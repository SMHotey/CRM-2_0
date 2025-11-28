from django import forms
from django.contrib.auth.models import User
from .models import (Organization, Invoice, Order, InternalLegalEntity, OrderItem, Shipment, Certificate,
                     ContractTemplate, LegalEntity, IndividualEntrepreneur, PhysicalPerson)
from django.core.exceptions import ValidationError


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


class InternalLegalEntityForm(forms.ModelForm):
    class Meta:
        model = InternalLegalEntity
        fields = '__all__'
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 40%', 'placeholder': 'Название'}),
            'inn': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 20%', 'placeholder': 'ИНН'}),
            'ogrn': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 20%', 'placeholder': 'ОГРН'}),
            'kpp': forms.TextInput(attrs={'class': 'form-control', 'style': 'width: 20%', 'placeholder': 'КПП'}),
            'legal_address': forms.Textarea(attrs={
                'class': 'form-control',
                'style': 'width: 40%; height: 60px;',
                'placeholder': 'Юридический адрес',
                'rows': 3
            }),
            'postal_address': forms.Textarea(attrs={
                'class': 'form-control',
                'style': 'width: 40%; height: 60px;',
                'placeholder': 'Почтовый адрес',
                'rows': 3
            }),
            'ceo_title': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 20%',
                'placeholder': 'Должность руководителя'
            }),
            'ceo_name': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 40%',
                'placeholder': 'ФИО руководителя'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 40%',
                'placeholder': 'Название банка'
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 20%',
                'placeholder': 'Расчетный счет'
            }),
            'bik': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 20%',
                'placeholder': 'БИК'
            }),
            'correspondent_account': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 20%',
                'placeholder': 'Корреспондентский счет'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'style': 'width: 20%',
                'placeholder': 'Введите email'
            })
        }


class LegalEntityForm(forms.ModelForm):
    show_advanced = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput(),
        label="Показать расширенную информацию"
    )

    class Meta:
        model = LegalEntity
        fields = [
            'legal_form', 'name', 'inn', 'internal_legal_entity', 'ogrn', 'kpp',
            'legal_address', 'postal_address', 'leader_position', 'leader_name',
            'bank_name', 'account_number', 'bik', 'correspondent_account', 'email'
        ]
        widgets = {
            'legal_form': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название организации'}),
            'inn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ИНН'}),
            'internal_legal_entity': forms.Select(attrs={'class': 'form-select'}),
            'ogrn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ОГРН'}),
            'kpp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'КПП'}),
            'legal_address': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Юридический адрес'}),
            'postal_address': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Почтовый адрес'}),
            'leader_position': forms.Select(attrs={'class': 'form-select'}),
            'leader_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО руководителя'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название банка'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Расчетный счет'}),
            'bik': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'БИК'}),
            'correspondent_account': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Корреспондентский счет'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Введите email'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['internal_legal_entity'].queryset = InternalLegalEntity.objects.all()
        self.fields['internal_legal_entity'].label = "Юридическое лицо"
        # Делаем поле обязательным для ЮЛ
        self.fields['internal_legal_entity'].required = True


class IndividualEntrepreneurForm(forms.ModelForm):
    show_advanced = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput(),
        label="Показать расширенную информацию"
    )

    class Meta:
        model = IndividualEntrepreneur
        fields = [
            'full_name', 'inn', 'internal_legal_entity', 'ogrn', 'legal_address',
            'bank_name', 'account_number', 'bik', 'correspondent_account', 'email'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО индивидуального предпринимателя'}),
            'inn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ИНН'}),
            'internal_legal_entity': forms.Select(attrs={'class': 'form-select'}),
            'ogrn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ОГРНИП'}),
            'legal_address': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Юридический адрес / Почтовый адрес'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название банка'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Расчетный счет'}),
            'bik': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'БИК'}),
            'correspondent_account': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Корреспондентский счет'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Введите email'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['internal_legal_entity'].queryset = InternalLegalEntity.objects.all()
        self.fields['internal_legal_entity'].label = "Юридическое лицо (наша компания)"
        self.fields['internal_legal_entity'].required = True


class PhysicalPersonForm(forms.ModelForm):
    show_advanced = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput(),
        label="Показать расширенную информацию"
    )

    class Meta:
        model = PhysicalPerson
        fields = ['full_name', 'phone', 'passport_scan', 'email']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Номер телефона'}),
            'passport_scan': forms.FileInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Введите email'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Для физлица internal_legal_entity не требуется
        pass

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['number', 'date', 'amount', 'payed_amount', 'shipping_amount', 'montage_amount',
                  'internal_legal_entity',
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
        self.fields['internal_legal_entity'].label = 'Юридическое лицо'
        self.fields['internal_legal_entity'].queryset = InternalLegalEntity.objects.all()
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
        fields = ['numbers', 'p_kind', 'p_type', 'internal_legal_entity', 'scan_copy', 'passport_templates']
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
            'internal_legal_entity': forms.Select(attrs={
                'class': 'form-select'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields required
        self.fields['p_kind'].required = True
        self.fields['p_type'].required = True
        self.fields['internal_legal_entity'].required = True

        # Limit legal_entity choices to active entities
        self.fields['internal_legal_entity'].queryset = InternalLegalEntity.objects.all()

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
