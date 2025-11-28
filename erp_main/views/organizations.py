from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, UpdateView, View, ListView, DeleteView, DetailView
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.forms import formset_factory, modelformset_factory
from ..models import Organization, LegalEntity, IndividualEntrepreneur, PhysicalPerson, InternalLegalEntity
from ..forms import LegalEntityForm, IndividualEntrepreneurForm, PhysicalPersonForm, InternalLegalEntityForm


class OrganizationCreateView(LoginRequiredMixin, CreateView):
    template_name = 'organizations/organization_form.html'
    success_url = reverse_lazy('organization_list')

    def get_form_class(self):
        org_type = self.request.GET.get('type', 'LEGAL')
        if org_type == 'LEGAL':
            return LegalEntityForm
        elif org_type == 'INDIVIDUAL':
            return IndividualEntrepreneurForm
        elif org_type == 'PERSON':
            return PhysicalPersonForm
        else:
            raise Http404("Неверный тип организации")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org_type = self.request.GET.get('type', 'LEGAL')

        context.update({
            'org_type': org_type,
            'organization_types': Organization.TYPES,
        })
        return context

    def form_valid(self, form):
        org_type = self.request.GET.get('type', 'LEGAL')

        try:
            with transaction.atomic():
                # Сохраняем основную организацию
                organization = form.save(commit=False)
                organization.type = org_type
                organization.user = self.request.user

                # Для физлиц устанавливаем internal_legal_entity в None
                if org_type == 'PERSON':
                    organization.internal_legal_entity = None

                organization.save()

                # Добавляем запись в историю
                organization.add_history_entry(
                    self.request.user,
                    'Создание контрагента'
                )

                messages.success(self.request, 'Контрагент успешно создан')
                return redirect(self.success_url)

        except Exception as e:
            messages.error(self.request, f'Ошибка при создании контрагента: {str(e)}')
            return self.render_to_response(self.get_context_data(form=form))


class OrganizationUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'organizations/organization_edit.html'  # Изменено на единый шаблон
    success_url = reverse_lazy('organization_list')

    def get_queryset(self):
        return Organization.objects.all()

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')
        org = get_object_or_404(Organization, pk=pk)

        if org.type == 'LEGAL':
            return get_object_or_404(LegalEntity, pk=pk)
        elif org.type == 'INDIVIDUAL':
            return get_object_or_404(IndividualEntrepreneur, pk=pk)
        elif org.type == 'PERSON':
            return get_object_or_404(PhysicalPerson, pk=pk)
        return org

    def get_form_class(self):
        organization = self.get_object()
        if organization.type == 'LEGAL':
            return LegalEntityForm
        elif organization.type == 'INDIVIDUAL':
            return IndividualEntrepreneurForm
        elif organization.type == 'PERSON':
            return PhysicalPersonForm
        else:
            raise Http404("Неизвестный тип организации")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_object()

        context.update({
            'organization': organization,
            'org_type': organization.type,
            'organization_types': Organization.TYPES,
        })

        return context

    def form_valid(self, form):
        organization = self.get_object()

        try:
            with transaction.atomic():
                # Сохраняем основную организацию
                organization = form.save()

                # Добавляем запись в историю
                organization.add_history_entry(
                    self.request.user,
                    'Редактирование контрагента'
                )

                messages.success(self.request, 'Контрагент успешно обновлен')
                return redirect(self.success_url)

        except Exception as e:
            messages.error(self.request, f'Ошибка при обновлении контрагента: {str(e)}')
            return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        messages.error(self.request, 'Ошибка при обновлении контрагента')
        return super().form_invalid(form)


class OrganizationListView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = 'organizations/organization_list.html'
    context_object_name = 'organizations'
    paginate_by = 20

    def get_queryset(self):
        # Базовый запрос с предзагрузкой всех связанных данных
        queryset = Organization.objects.all()

        # Предзагрузка всех связанных данных
        queryset = queryset.select_related('user', 'internal_legal_entity')

        # Предзагрузка дочерних моделей для корректной работы свойств
        queryset = queryset.prefetch_related(
            'legalentity',
            'individualentrepreneur',
            'physicalperson'
        )

        # Фильтрация по типу
        org_type = self.request.GET.get('type')
        if org_type:
            queryset = queryset.filter(type=org_type)

        # Поиск
        search_query = self.request.GET.get('search')
        if search_query:
            # Используем Q-объекты для более эффективного поиска
            from django.db.models import Q

            # Создаем подзапросы для каждого типа организации
            legal_entity_ids = LegalEntity.objects.filter(
                Q(name__icontains=search_query) |
                Q(inn__icontains=search_query) |
                Q(leader_name__icontains=search_query) |
                Q(email__icontains=search_query)
            ).values_list('organization_ptr_id', flat=True)

            individual_entrepreneur_ids = IndividualEntrepreneur.objects.filter(
                Q(full_name__icontains=search_query) |
                Q(inn__icontains=search_query) |
                Q(email__icontains=search_query)
            ).values_list('organization_ptr_id', flat=True)

            physical_person_ids = PhysicalPerson.objects.filter(
                Q(full_name__icontains=search_query) |
                Q(phone__icontains=search_query) |
                Q(email__icontains=search_query)
            ).values_list('organization_ptr_id', flat=True)

            # Объединяем все ID
            all_ids = list(legal_entity_ids) + list(individual_entrepreneur_ids) + list(physical_person_ids)

            if all_ids:
                queryset = queryset.filter(id__in=all_ids)
            else:
                # Если ничего не найдено, возвращаем пустой queryset
                queryset = queryset.none()

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization_types'] = Organization.TYPES
        context['current_type'] = self.request.GET.get('type', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context


class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = 'organizations/organization_detail.html'
    context_object_name = 'organization'

    def get_object(self, queryset=None):
        """Возвращает конкретную организацию с правильным типом"""
        pk = self.kwargs.get('pk')
        org = get_object_or_404(Organization, pk=pk)

        # Возвращаем конкретный экземпляр нужного типа
        if org.type == 'LEGAL':
            return get_object_or_404(LegalEntity, pk=pk)
        elif org.type == 'INDIVIDUAL':
            return get_object_or_404(IndividualEntrepreneur, pk=pk)
        elif org.type == 'PERSON':
            return get_object_or_404(PhysicalPerson, pk=pk)
        return org

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_object()

        # Получаем банковские реквизиты для отображения
        bank_details = None
        if hasattr(organization, 'bank_name') and organization.bank_name:
            bank_details = {
                'bank_name': organization.bank_name,
                'account_number': organization.account_number,
                'bik': organization.bik,
                'correspondent_account': organization.correspondent_account
            }

        context.update({
            'documents': organization.documents.all(),
            'bank_details': bank_details,
            'history_entries': organization.history[-10:][::-1] if organization.history else []  # Последние 10 записей
        })
        return context


class OrganizationDeleteView(LoginRequiredMixin, DeleteView):
    model = Organization
    template_name = 'organizations/organization_confirm_delete.html'
    success_url = reverse_lazy('organization_list')
    context_object_name = 'organization'

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Организация успешно удалена')
        return super().delete(request, *args, **kwargs)


class TakeOverOrganizationView(LoginRequiredMixin, View):
    def post(self, request, pk):
        organization = get_object_or_404(Organization, pk=pk)
        old_user = organization.user

        organization.user = request.user
        organization.save()

        # Добавление записи в историю
        organization.add_history_entry(
            request.user,
            "Смена менеджера",
            old_value=str(old_user),
            new_value=str(request.user)
        )

        messages.success(request, f'Организация "{organization}" теперь прикреплена к вам')
        return redirect('organization_list')


class OrganizationTypeSelectView(LoginRequiredMixin, View):
    """Представление для выбора типа организации перед созданием"""

    def get(self, request):
        return render(request, 'organizations/organization_type_select.html', {
            'organization_types': Organization.TYPES
        })


# def create_internal_legal_entity(request):
#     if request.method == 'POST':
#         form = InternalLegalEntityForm(request.POST)
#         if form.is_valid():
#             form.save()
#             return redirect('organization_list')
#     else:
#         form = InternalLegalEntityForm()
#
#     return render(request, 'legal_entity_form.html', {'form': form})
#
#
# # AJAX представления для работы с внутренними юрлицами
# class GetInternalLegalEntitiesView(LoginRequiredMixin, View):
#     """Возвращает JSON список внутренних юрлиц для AJAX-запросов"""
#
#     def get(self, request):
#         legal_entities = InternalLegalEntity.objects.all().values('id', 'name', 'inn')
#         return JsonResponse(list(legal_entities), safe=False)
#
#
# class GetInternalLegalEntityDetailsView(LoginRequiredMixin, View):
#     """Возвращает детали внутреннего юрлица по ID"""
#
#     def get(self, request, pk):
#         try:
#             legal_entity = InternalLegalEntity.objects.get(pk=pk)
#             data = {
#                 'id': legal_entity.id,
#                 'name': legal_entity.name,
#                 'inn': legal_entity.inn,
#                 'ogrn': legal_entity.ogrn,
#                 'kpp': legal_entity.kpp,
#                 'address': legal_entity.address,
#                 'ceo_title': legal_entity.ceo_title,
#                 'ceo_name': legal_entity.ceo_name,
#                 'bank_name': legal_entity.bank_name,
#                 'account_number': legal_entity.account_number,
#                 'bik': legal_entity.bik,
#                 'correspondent_account': legal_entity.correspondent_account,
#             }
#             return JsonResponse(data)
#         except InternalLegalEntity.DoesNotExist:
#             return JsonResponse({'error': 'Юридическое лицо не найдено'}, status=404)