from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, ListView, DetailView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from ..models import Organization, LegalEntity, ContractTemplate
from ..forms import OrganizationForm, LegalEntityForm
from .mixins import UserAccessMixin


class OrganizationCreateView(UserAccessMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'organization_add.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Проверяем ИНН на существование
        inn = form.cleaned_data.get('inn')
        org_type = form.cleaned_data.get('organization_type')

        if inn and org_type in ['legal_entity', 'individual_entrepreneur']:
            existing_org = Organization.objects.filter(inn=inn).first()
            if existing_org:
                # Сохраняем данные формы в сессии для повторного использования
                self.request.session['organization_form_data'] = {
                    'organization_type': org_type,
                    'kind': form.cleaned_data.get('kind'),
                    'name': form.cleaned_data.get('name'),
                    'name_fl': form.cleaned_data.get('name_fl'),
                    'legal_entity_id': form.cleaned_data.get('legal_entity').id if form.cleaned_data.get(
                        'legal_entity') else None,
                    'emails': form.cleaned_data.get('emails', ''),
                    'bank_accounts': form.cleaned_data.get('bank_accounts', '[]'),
                }
                return redirect('organization_duplicate_handler', inn=inn)

        organization = form.save(commit=False)
        organization.user = self.request.user
        organization.save()

        # Сохраняем связанные данные
        form.save_m2m()
        return redirect('organization_list')

    def form_invalid(self, form):
        return super().form_invalid(form)


@require_http_methods(["GET", "POST"])
def organization_duplicate_handler(request, inn):
    existing_org = get_object_or_404(Organization, inn=inn)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'take_over':
            # Забираем организацию
            old_user = existing_org.user
            existing_org.user = request.user
            existing_org.add_history_record('user', str(old_user), str(request.user))
            existing_org.save()
            messages.success(request, f'Организация "{existing_org}" теперь прикреплена к вам')

        elif action == 'create_duplicate':
            # Создаем дубликат с другим ИНН
            form_data = request.session.get('organization_form_data', {})
            organization = Organization.objects.create(
                organization_type=form_data.get('organization_type'),
                user=request.user,
                kind=form_data.get('kind'),
                name=form_data.get('name'),
                name_fl=form_data.get('name_fl'),
                legal_entity_id=form_data.get('legal_entity_id'),
                inn=f"{inn}_dup_{Organization.objects.count() + 1}"  # Уникальный ИНН для дубликата
            )
            messages.success(request, f'Создана новая организация с ИНН {organization.inn}')

        elif action == 'cancel':
            messages.info(request, 'Создание организации отменено')

        # Очищаем данные формы из сессии
        if 'organization_form_data' in request.session:
            del request.session['organization_form_data']

        return redirect('organization_list')

    return render(request, 'organization_duplicate_handler.html', {
        'existing_org': existing_org,
        'inn': inn
    })


@require_http_methods(["GET"])
def get_contract_template(request):
    """API для получения подходящего шаблона договора"""
    org_type = request.GET.get('organization_type')
    legal_entity_id = request.GET.get('legal_entity')
    kind = request.GET.get('kind')
    footing = request.GET.get('ceo_footing')

    templates = ContractTemplate.objects.all()

    if org_type:
        templates = templates.filter(contract_type=org_type)

    if legal_entity_id:
        templates = templates.filter(legal_entity_id=legal_entity_id)

    if kind:
        templates = templates.filter(organization_type=kind)

    if footing:
        templates = templates.filter(footing_type=footing)

    # Ищем наиболее подходящий шаблон
    template = templates.first()

    if template:
        return JsonResponse({
            'template_id': template.id,
            'template_name': template.name
        })

    return JsonResponse({'template_id': None, 'template_name': ''})


class OrganizationUpdateView(UserAccessMixin, UpdateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'organization_edit.html'
    context_object_name = 'organization'

    def get_success_url(self):
        return reverse('organization_detail', kwargs={'pk': self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Логируем изменения
        old_instance = Organization.objects.get(pk=self.object.pk)
        for field in form.changed_data:
            if field not in ['emails', 'bank_accounts']:  # Исключаем скрытые поля
                old_value = getattr(old_instance, field)
                new_value = form.cleaned_data[field]
                self.object.add_history_record(field, str(old_value), str(new_value))

        return super().form_valid(form)


class OrganizationListView(UserAccessMixin, ListView):
    model = Organization
    template_name = 'organization_list.html'
    context_object_name = 'organizations'

    def get_queryset(self):
        return self.get_user_organizations()


class OrganizationDetailView(UserAccessMixin, DetailView):
    model = Organization
    template_name = 'organization_detail.html'
    context_object_name = 'organization'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['legal_entities'] = LegalEntity.objects.all()
        return context

def create_legal_entity(request):
    if request.method == 'POST':
        form = LegalEntityForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            return redirect('organization_list')
    else:
        form = LegalEntityForm(request.user)

    return render(request, 'legal_entity_form.html', {'form': form})