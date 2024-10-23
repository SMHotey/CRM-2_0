from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from erp_main.models import Organization, Invoice, Order


class UserCreationForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password')


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
            self.fields['invoice'].queryset = Invoice.objects.filter(user=user)
        else:
            self.fields['invoice'].queryset = Invoice.objects.all()
# forms.py
class OrganizationForm(forms.ModelForm):

    class Meta:
        model = Organization
        fields = ['name', 'inn', 'phone_number', 'name_fl']

    # Изменение по умолчанию для полей
    name_fl = forms.CharField(max_length=15, required=False)
    phone_number = forms.CharField(max_length=15, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['inn'].label = 'ИНН'
        self.fields['name'].label = 'Наименование'
        self.fields['name_fl'].label = 'Имя, фамилия'
        self.fields['phone_number'].label = 'Номер телефона'

    def clean(self):
        cleaned_data = super().clean()
        # Условная логика для валидации
        type_ = self.data.get('type')  # Получаем тип из POST данных

        if type_ == 'organization':
            if not cleaned_data.get('inn'):
                self.add_error('inn', 'ИНН обязательно для юридического лица.')
            if not cleaned_data.get('name'):
                self.add_error('name', 'Наименование обязательно для юридического лица.')

        elif type_ == 'individual':
            if not cleaned_data.get('name_fl'):
                self.add_error('name_fl', 'Имя обязательно для физического лица.')
            if not cleaned_data.get('phone_number'):
                self.add_error('phone_number', 'Номер телефона обязателен для физического лица.')

        return cleaned_data


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['number', 'amount', 'payed_amount', 'shipping_amount', 'montage_amount', 'legal_entity',
                  'organization']

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['number'].label = 'Номер'
        self.fields['amount'].label = 'Сумма'
        self.fields['payed_amount'].label = 'Оплачено'
        self.fields['shipping_amount'].label = 'Стоимость доставки'
        self.fields['montage_amount'].label = 'Стоимость монтажа'
        self.fields['legal_entity'].label = 'Юридическое лицо'
        self.fields['organization'].label = 'Организация'
        if not user.is_superuser:
            self.fields['organization'].queryset = Organization.objects.filter(user=user)

        else:
            self.fields['organization'].queryset = Organization.objects.all()

    def __str__(self):
        return self.number if self.number else "Без номера"


class OrderFileForm(forms.Form):
    order_file = forms.FileField()
