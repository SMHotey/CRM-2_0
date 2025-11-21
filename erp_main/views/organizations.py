from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, UpdateView, View
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.forms import formset_factory
from ..models import Organization, LegalEntity, IndividualEntrepreneur, PhysicalPerson, Email, BankDetails, \
    InternalLegalEntity
from ..forms import LegalEntityForm, IndividualEntrepreneurForm, PhysicalPersonForm, EmailForm, BankDetailsForm

class OrganizationCreateView(CreateView):
    template_name = 'organization_add.html'
    success_url = reverse_lazy('organization_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org_type = self.request.GET.get('type', 'LEGAL')

        # Формы для email и банковских реквизитов
        EmailFormSet = formset_factory(EmailForm, extra=1)
        BankDetailsFormSet = formset_factory(BankDetailsForm, extra=1)

        # Получаем доступные InternalLegalEntity для выбора
        available_legal_entities = InternalLegalEntity.objects.all()

        context.update({
            'org_type': org_type,
            'email_formset': EmailFormSet(),
            'bank_details_formset': BankDetailsFormSet(),
            'Organization': Organization,
            'available_legal_entities': available_legal_entities,
        })

        # Добавляем соответствующую основную форму в зависимости от типа
        if org_type == 'LEGAL':
            context['main_form'] = LegalEntityForm()
        elif org_type == 'INDIVIDUAL':
            context['main_form'] = IndividualEntrepreneurForm()
        else:
            context['main_form'] = PhysicalPersonForm()

        return context

    def post(self, request, *args, **kwargs):
        org_type = request.POST.get('org_type', 'LEGAL')

        # Инициализация форм и формсетов
        EmailFormSet = formset_factory(EmailForm)
        BankDetailsFormSet = formset_factory(BankDetailsForm)

        email_formset = EmailFormSet(request.POST, prefix='email')
        bank_details_formset = BankDetailsFormSet(request.POST, prefix='bank')

        # Выбор основной формы
        if org_type == 'LEGAL':
            main_form = LegalEntityForm(request.POST, request.FILES)
        elif org_type == 'INDIVIDUAL':
            main_form = IndividualEntrepreneurForm(request.POST, request.FILES)
        else:
            main_form = PhysicalPersonForm(request.POST, request.FILES)

        # Для физлиц устанавливаем internal_legal_entity в None
        if org_type == 'PERSON':
            main_form.data = main_form.data.copy()
            main_form.data['internal_legal_entity'] = ''

        if main_form.is_valid() and email_formset.is_valid():
            # Для ЮЛ и ИП проверяем банковские реквизиты
            if org_type in ['LEGAL', 'INDIVIDUAL']:
                if not bank_details_formset.is_valid():
                    return self.form_invalid(
                        main_form, email_formset, bank_details_formset, org_type
                    )

            try:
                with transaction.atomic():
                    # Сохраняем основную форму
                    organization = main_form.save(commit=False)
                    organization.type = org_type
                    organization.user = request.user

                    # Для физлиц устанавливаем internal_legal_entity в None
                    if org_type == 'PERSON':
                        organization.internal_legal_entity = None

                    organization.save()

                    # Сохраняем email адреса
                    self.save_emails(email_formset, organization)

                    # Сохраняем банковские реквизиты для ЮЛ и ИП
                    if org_type in ['LEGAL', 'INDIVIDUAL']:
                        self.save_bank_details(bank_details_formset, organization)

                    # Добавляем запись в историю
                    organization.add_history_entry(
                        request.user,
                        'Создание контрагента'
                    )

                    messages.success(request, 'Контрагент успешно создан')
                    return redirect(self.success_url)

            except Exception as e:
                messages.error(request, f'Ошибка при создании контрагента: {str(e)}')
                return self.form_invalid(
                    main_form, email_formset, bank_details_formset, org_type
                )

        return self.form_invalid(
            main_form, email_formset, bank_details_formset, org_type
        )

    def save_emails(self, email_formset, organization):
        """Сохранение email адресов"""
        for i, form in enumerate(email_formset):
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                email = form.save(commit=False)
                email.content_object = organization
                # Первый email делаем основным
                if i == 0:
                    email.is_primary = True
                email.save()

    def save_bank_details(self, bank_details_formset, organization):
        """Сохранение банковских реквизитов"""
        for i, form in enumerate(bank_details_formset):
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                bank_detail = form.save(commit=False)
                bank_detail.content_object = organization
                # Первые реквизиты делаем основными
                if i == 0:
                    bank_detail.is_primary = True
                bank_detail.save()


class OrganizationUpdateView(UpdateView):
    template_name = 'organization_edit.html'
    success_url = reverse_lazy('organization_list')  # Замените на ваш URL

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(Organization, pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_object()

        # Формы для email и банковских реквизитов
        EmailFormSet = formset_factory(EmailForm, extra=1)
        BankDetailsFormSet = formset_factory(BankDetailsForm, extra=1)

        # Получаем существующие email и банковские реквизиты
        existing_emails = organization.emails.all()
        existing_bank_details = organization.bank_details.all() if hasattr(organization, 'bank_details') else []

        context.update({
            'org_type': organization.type,
            'email_formset': EmailFormSet(
                initial=[{'email': email.email, 'is_primary': email.is_primary} for email in existing_emails],
                prefix='email'
            ),
            'bank_details_formset': BankDetailsFormSet(
                initial=[{
                    'bank_name': bank.bank_name,
                    'account_number': bank.account_number,
                    'bik': bank.bik,
                    'correspondent_account': bank.correspondent_account,
                    'is_primary': bank.is_primary
                } for bank in existing_bank_details],
                prefix='bank'
            ) if organization.type in ['LEGAL', 'INDIVIDUAL'] else None,
        })

        return context

    def get_form_class(self):
        organization = self.get_object()
        if organization.type == 'LEGAL':
            return LegalEntityForm
        elif organization.type == 'INDIVIDUAL':
            return IndividualEntrepreneurForm
        else:
            return PhysicalPersonForm

    def form_valid(self, form):
        organization = self.get_object()

        try:
            with transaction.atomic():
                # Сохраняем основную форму
                organization = form.save()

                # Обновляем email и банковские реквизиты
                self.update_emails(organization)
                if organization.type in ['LEGAL', 'INDIVIDUAL']:
                    self.update_bank_details(organization)

                # Добавляем запись в историю
                organization.add_history_entry(
                    self.request.user,
                    'Редактирование контрагента'
                )

                messages.success(self.request, 'Контрагент успешно обновлен')
                return redirect(self.success_url)

        except Exception as e:
            messages.error(self.request, f'Ошибка при обновлении контрагента: {str(e)}')
            return self.form_invalid(form)

    def update_emails(self, organization):
        """Обновление email адресов"""
        EmailFormSet = formset_factory(EmailForm)
        email_formset = EmailFormSet(self.request.POST, prefix='email')

        if email_formset.is_valid():
            # Удаляем старые email
            organization.emails.all().delete()

            # Сохраняем новые
            for form in email_formset:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    email = form.save(commit=False)
                    email.content_object = organization
                    email.save()

    def update_bank_details(self, organization):
        """Обновление банковских реквизитов"""
        BankDetailsFormSet = formset_factory(BankDetailsForm)
        bank_details_formset = BankDetailsFormSet(self.request.POST, prefix='bank')

        if bank_details_formset.is_valid():
            # Удаляем старые реквизиты
            organization.bank_details.all().delete()

            # Сохраняем новые
            for i, form in enumerate(bank_details_formset):
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    bank_detail = form.save(commit=False)
                    bank_detail.content_object = organization
                    if i == 0:
                        bank_detail.is_primary = True
                    bank_detail.save()

    def _get_organization(self, org_type, pk):
        """Вспомогательный метод для получения организации по типу и ID"""
        if org_type == 'legal':
            return get_object_or_404(LegalEntity, pk=pk)
        elif org_type == 'individual_entrepreneur':
            return get_object_or_404(IndividualEntrepreneur, pk=pk)
        elif org_type == 'person':
            return get_object_or_404(PhysicalPerson, pk=pk)
        return None


class OrganizationListView(LoginRequiredMixin, View):
    def get(self, request):
        # Получаем все типы организаций для текущего пользователя
        legal_entities = LegalEntity.objects.filter(user=request.user)
        individual_entrepreneurs = IndividualEntrepreneur.objects.filter(user=request.user)
        physical_persons = PhysicalPerson.objects.filter(user=request.user)

        # Объединяем в один список для отображения
        all_organizations = list(legal_entities) + list(individual_entrepreneurs) + list(physical_persons)
        # Сортируем по дате создания (новые первыми)
        all_organizations.sort(key=lambda x: x.created_at, reverse=True)

        return render(request, 'organization_list.html', {
            'organizations': all_organizations
        })


class TakeOverOrganizationView(LoginRequiredMixin, View):
    def post(self, request):
        org_type = request.POST.get('org_type')
        organization_id = request.POST.get('organization_id')

        organization = self._get_organization(org_type, organization_id)
        if not organization:
            return JsonResponse({'success': False, 'error': 'Organization not found'})

        old_user = organization.user
        organization.user = request.user
        organization.save()

        # Добавление записи в историю
        organization.add_history_entry(
            request.user,
            "Смена менеджера",
            old_value={'user': old_user.username},
            new_value={'user': request.user.username}
        )

        return JsonResponse({'success': True})

    def _get_organization(self, org_type, organization_id):
        """Вспомогательный метод для получения организации по типу и ID"""
        if org_type == 'legal':
            return get_object_or_404(LegalEntity, pk=organization_id)
        elif org_type == 'individual_entrepreneur':
            return get_object_or_404(IndividualEntrepreneur, pk=organization_id)
        elif org_type == 'person':
            return get_object_or_404(PhysicalPerson, pk=organization_id)
        return None


@require_http_methods(["GET", "POST"])
def organization_duplicate_handler(request, org_type, identifier):
    """Обработчик дубликатов организаций"""

    # Получаем существующую организацию
    if org_type in ['legal', 'individual_entrepreneur']:
        existing_org = get_object_or_404(
            LegalEntity if org_type == 'legal' else IndividualEntrepreneur,
            inn=identifier
        )
    elif org_type == 'person':
        existing_org = get_object_or_404(PhysicalPerson, phone=identifier)
    else:
        messages.error(request, 'Неверный тип организации')
        return redirect('organization_create')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'take_over':
            # Забираем организацию
            old_user = existing_org.user
            existing_org.user = request.user
            existing_org.save()

            existing_org.add_history_entry(
                request.user,
                "Смена менеджера при взятии организации",
                old_value={'user': old_user.username},
                new_value={'user': request.user.username}
            )

            messages.success(request, f'Организация "{existing_org}" теперь прикреплена к вам')

        elif action == 'create_duplicate':
            # Создаем дубликат с другим идентификатором
            form_data = request.session.get('organization_form_data', {})

            if org_type == 'legal':
                duplicate_inn = f"{identifier}_dup_{int(timezone.now().timestamp())}"
                organization = LegalEntity.objects.create(
                    legal_form=form_data.get('legal_form'),
                    name=form_data.get('name'),
                    inn=duplicate_inn,
                    parent_company_id=form_data.get('parent_company'),
                    user=request.user,
                    # ... остальные поля
                )
            elif org_type == 'individual_entrepreneur':
                duplicate_inn = f"{identifier}_dup_{int(timezone.now().timestamp())}"
                organization = IndividualEntrepreneur.objects.create(
                    full_name=form_data.get('full_name'),
                    inn=duplicate_inn,
                    parent_company_id=form_data.get('parent_company'),
                    user=request.user,
                    # ... остальные поля
                )
            elif org_type == 'person':
                duplicate_phone = f"{identifier}_dup_{int(timezone.now().timestamp())}"
                organization = PhysicalPerson.objects.create(
                    full_name=form_data.get('full_name'),
                    phone=duplicate_phone,
                    user=request.user,
                    # ... остальные поля
                )

            organization.add_history_entry(
                request.user,
                "Создана как дубликат существующей организации"
            )

            messages.success(request, f'Создана новая организация')

        elif action == 'cancel':
            messages.info(request, 'Создание организации отменено')

        # Очищаем данные формы из сессии
        if 'organization_form_data' in request.session:
            del request.session['organization_form_data']

        return redirect('organization_list')

    return render(request, 'organizations/organization_duplicate_handler.html', {
        'existing_org': existing_org,
        'org_type': org_type,
        'identifier': identifier
    })

def create_internal_legal_entity(request):
    if request.method == 'POST':
        form = InternalLegalEntityForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            return redirect('organization_list')
    else:
        form = InternalLegalEntityForm(request.user)

    return render(request, 'legal_entity_form.html', {'form': form})