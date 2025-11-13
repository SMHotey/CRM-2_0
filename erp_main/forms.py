from django import forms
from django.contrib.auth.models import User
from .models import Organization, Invoice, Order, LegalEntity, OrderItem, Shipment, Certificate , BankAccount, OrganizationEmail, LegalEntity, ContractTemplate
import json


# class UserCreationForm(forms.ModelForm):
#     class Meta:
#         model = User
#         fields = ('username', 'email', 'password', 'password')


class OrderForm(forms.ModelForm):
    due_date = forms.DateField(required=False, widget=forms.HiddenInput())  # Поле для даты готовности

    class Meta:
        model = Order
        fields = ['order_file', 'invoice', 'due_date', 'comment']  # Убедитесь, что у вас в полях есть 'due_date'

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['order_file'].label = 'Файл заказа'
        self.fields['invoice'].label = 'Счет'
        self.fields['comment'].label = 'Комментарий'
        self.user = user

        if not user.is_superuser:
            self.fields['invoice'].queryset = Invoice.objects.filter(organization__user=user)
        else:
            self.fields['invoice'].queryset = Invoice.objects.all()


class LegalEntityForm(forms.ModelForm):
    class Meta:
        model = LegalEntity
        fields = ['name', 'inn', 'ogrn', 'kpp', 'r_s', 'bank', 'bik', 'k_s', 'address', 'email', 'ceo_title', 'ceo_name']

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = 'Название'
        self.fields['inn'].label = 'ИНН'
        self.fields['ogrn'].label = 'ОГРН'
        self.fields['kpp'].label = 'КПП'
        self.fields['r_s'].label = 'р/с'
        self.fields['bank'].label = 'Банк'
        self.fields['bik'].label = 'БИК'
        self.fields['k_s'].label = 'к/с'
        self.fields['address'].label = 'юр.адрес'
        self.fields['email'].label = 'email'
        self.fields['ceo_title'].label = 'должность подписанта'
        self.fields['ceo_name'].label = 'ФИО полностью'


class OrganizationForm(forms.ModelForm):
    ORGANIZATION_TYPE_CHOICES = (
        ('legal_entity', 'Юридическое лицо'),
        ('individual_entrepreneur', 'Индивидуальный предприниматель'),
        ('physical_person', 'Физическое лицо'),
    )

    organization_type = forms.ChoiceField(
        choices=ORGANIZATION_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'type-radio'}),
        label='Тип контрагента'
    )

    # Поля для множественных email
    emails = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Список email адресов через запятую"
    )

    # Поля для банковских счетов
    bank_accounts = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="JSON с банковскими счетами"
    )

    class Meta:
        model = Organization
        fields = [
            'organization_type', 'kind', 'name', 'inn', 'legal_entity',
            'name_fl', 'ogrnip', 'phone_number', 'passport_scan',
            'ceo_footing', 'attorney_number', 'attorney_date', 'attorney_file',
            'ogrn', 'kpp', 'address', 'postal_address', 'ceo_title', 'ceo_name',
            'contract_template', 'custom_contract_template'
        ]
        widgets = {
            'kind': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Название организации'}),
            'inn': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '10 или 12 цифр'}),
            'legal_entity': forms.Select(attrs={'class': 'form-select'}),
            'name_fl': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'ФИО'}),
            'ogrnip': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '15 цифр'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+7 XXX XXX-XX-XX'}),
            'ceo_footing': forms.Select(attrs={'class': 'form-select'}),
            'attorney_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Номер доверенности'}),
            'attorney_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
            'ogrn': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '13 или 15 цифр'}),
            'kpp': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '9 цифр'}),
            'address': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Юридический адрес'}),
            'postal_address': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Почтовый адрес'}),
            'ceo_title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Генеральный директор'}),
            'ceo_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'ФИО руководителя'}),
            'contract_template': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['legal_entity'].queryset = LegalEntity.objects.all()
        self.fields['contract_template'].queryset = ContractTemplate.objects.all()

        if self.instance.pk:
            # Предзаполняем emails для существующей организации
            emails = list(self.instance.emails.values_list('email', flat=True))
            self.initial['emails'] = ','.join(emails)

            # Предзаполняем банковские счета
            bank_accounts = list(self.instance.bank_accounts.values('r_s', 'bank', 'bik', 'k_s'))
            self.initial['bank_accounts'] = json.dumps(bank_accounts)

    def clean(self):
        cleaned_data = super().clean()
        org_type = cleaned_data.get('organization_type')

        if org_type == 'legal_entity':
            if not cleaned_data.get('kind'):
                self.add_error('kind', "Для юридического лица тип организации обязателен")
            if not cleaned_data.get('name'):
                self.add_error('name', "Для юридического лица название организации обязательно")
            if not cleaned_data.get('inn'):
                self.add_error('inn', "Для юридического лица ИНН обязателен")
            if not cleaned_data.get('legal_entity'):
                self.add_error('legal_entity', "Для юридического лица выбор юридического лица обязателен")

        elif org_type == 'individual_entrepreneur':
            if not cleaned_data.get('name_fl'):
                self.add_error('name_fl', "Для ИП ФИО обязательно")
            if not cleaned_data.get('inn'):
                self.add_error('inn', "Для ИП ИНН обязателен")
            if not cleaned_data.get('legal_entity'):
                self.add_error('legal_entity', "Для ИП выбор юридического лица обязателен")

        elif org_type == 'physical_person':
            if not cleaned_data.get('name_fl'):
                self.add_error('name_fl', "Для физического лица ФИО обязательно")
            if not cleaned_data.get('phone_number'):
                self.add_error('phone_number', "Для физического лица номер телефона обязателен")

        # Валидация emails
        emails_str = cleaned_data.get('emails', '')
        if emails_str:
            emails_list = [email.strip() for email in emails_str.split(',') if email.strip()]
            for email in emails_list:
                try:
                    forms.EmailField().clean(email)
                except forms.ValidationError:
                    self.add_error(None, f"Некорректный email адрес: {email}")

        # Проверка ИНН на уникальность
        inn = cleaned_data.get('inn')
        if inn and org_type in ['legal_entity', 'individual_entrepreneur']:
            existing_org = Organization.objects.filter(inn=inn).first()
            if existing_org and (not self.instance.pk or self.instance.pk != existing_org.pk):
                self.add_error('inn', f"Организация с ИНН {inn} уже существует")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.user:
            instance.user = self.user

        if commit:
            instance.save()

            # Сохраняем emails
            emails_str = self.cleaned_data.get('emails', '')
            emails_list = [email.strip() for email in emails_str.split(',') if email.strip()]

            # Удаляем старые emails
            instance.emails.all().delete()

            # Создаем новые
            for email in emails_list:
                OrganizationEmail.objects.create(organization=instance, email=email)

            # Сохраняем банковские счета
            bank_accounts_str = self.cleaned_data.get('bank_accounts', '[]')
            try:
                bank_accounts_data = json.loads(bank_accounts_str)

                # Удаляем старые счета
                instance.bank_accounts.all().delete()

                # Создаем новые
                for account_data in bank_accounts_data:
                    if account_data.get('r_s') or account_data.get('bank'):
                        BankAccount.objects.create(
                            organization=instance,
                            r_s=account_data.get('r_s', ''),
                            bank=account_data.get('bank', ''),
                            bik=account_data.get('bik', ''),
                            k_s=account_data.get('k_s', '')
                        )
            except json.JSONDecodeError:
                pass

        return instance


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['number', 'date', 'amount', 'payed_amount', 'shipping_amount', 'montage_amount', 'legal_entity',
                  'organization', 'invoice_file']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['number'].label = 'Номер'
        self.fields['date'].label = 'Дата выставления'
        self.fields['amount'].label = 'Сумма'
        self.fields['payed_amount'].label = 'Оплачено'
        self.fields['shipping_amount'].label = 'Стоимость доставки'
        self.fields['montage_amount'].label = 'Стоимость монтажа'
        self.fields['legal_entity'].label = 'Юридическое лицо'
        self.fields['legal_entity'].queryset = LegalEntity.objects.all()
        self.fields['organization'].label = 'Организация'
        if not user.is_superuser:
            self.fields['organization'].queryset = Organization.objects.filter(user=user)

        else:
            self.fields['organization'].queryset = Organization.objects.all()

    def __str__(self):
        return self.number if self.number else "Без номера"


class OrderFileForm(forms.Form):
    order_file = forms.FileField()


class ShipmentForm(forms.ModelForm):
    order = forms.ModelChoiceField(
        queryset=Order.objects.none(),  # Будет установлен в __init__
        required=False,
        label='Номер заявки'
    )
    order_type = forms.ChoiceField(
        choices=[('', '-- Выберите тип --'), ('самовывоз', 'самовывоз'), ('наша', 'наша'), ('ТК', 'ТК')],
        required=False,
        label='Тип отгрузки'
    )
    car_brand = forms.CharField(required=False, label='Марка автомобиля')
    car_number = forms.CharField(required=False, label='Гос. номер')
    address = forms.CharField(required=False, label='Адрес доставки')
    comments = forms.CharField(required=False, label='Комментарии')
    shipment_mark = forms.CharField(required=False, label='Отметка об отгрузке')

    class Meta:
        model = Shipment
        fields = ['order', 'date', 'time', 'workshop']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'workshop': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Устанавливаем queryset для поля order
        if user:
            filtered_items = OrderItem.objects.filter(p_status__in=['product', 'ready'])
            self.fields['order'].queryset = Order.objects.filter(items__in=filtered_items).distinct()

        # Инициализация полей из JSON-данных
        if self.instance.pk:
            self.fields['order_type'].initial = self.instance.order_items.get('type', '')
            self.fields['car_brand'].initial = self.instance.car_info.get('brand', '')
            self.fields['car_number'].initial = self.instance.car_info.get('number', '')
            self.fields['comments'].initial = self.instance.driver_info.get('comments', '')
            self.fields['shipment_mark'].initial = self.instance.driver_info.get('shipment_mark', '')

    def save(self, commit=True):
        shipment = super().save(commit=False)

        # Сохраняем данные в JSON-поля
        order_items = shipment.order_items or {}
        order_items['type'] = self.cleaned_data.get('order_type', '')
        shipment.order_items = order_items

        car_info = shipment.car_info or {}
        car_info.update({
            'brand': self.cleaned_data.get('car_brand', ''),
            'number': self.cleaned_data.get('car_number', '')
        })
        shipment.car_info = car_info

        driver_info = shipment.driver_info or {}
        driver_info.update({
            'comments': self.cleaned_data.get('comments', ''),
            'shipment_mark': self.cleaned_data.get('shipment_mark', '')
        })
        shipment.driver_info = driver_info

        if commit:
            shipment.save()
        return shipment


class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ['numbers', 'p_kind', 'p_type', 'legal_entity', 'scan_copy', 'passport_templates']
        widgets = {
            'numbers': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите номер сертификата'
            }),
            'p_kind': forms.Select(attrs={
                'class': 'form-select'
            }),
            'p_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'legal_entity': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields required
        self.fields['p_kind'].required = True
        self.fields['p_type'].required = True
        self.fields['legal_entity'].required = True

        # Limit legal_entity choices to active entities
        self.fields['legal_entity'].queryset = LegalEntity.objects.all()

        # File fields with custom attributes
        self.fields['scan_copy'].widget.attrs.update({
            'class': 'form-control',
            'accept': '.pdf,.jpg,.jpeg,.png'
        })
        self.fields['passport_templates'].widget.attrs.update({
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx'
        })

    def clean_scan_copy(self):
        scan_copy = self.cleaned_data.get('scan_copy')
        if scan_copy:
            # Validate file size (5MB limit)
            if scan_copy.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Размер файла не должен превышать 5MB")
        return scan_copy

    def clean_passport_templates(self):
        passport_templates = self.cleaned_data.get('passport_templates')
        if passport_templates:
            if passport_templates.size > 10 * 1024 * 1024:
                raise forms.ValidationError("Размер файла не должен превышать 10MB")
        return passport_templates