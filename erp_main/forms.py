from django import forms

from erp_main.models import Organization, Invoice, Order


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['organization', 'order_file', 'invoice']  # Укажите, какие поля вы хотите отобразить

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Получаем пользователя из kwargs
        super().__init__(*args, **kwargs)
        self.fields['organization'].label = 'Организация'
        self.fields['order_file'].label = 'Файл заказа'
        self.fields['invoice'].label = 'Счет'

        if user:
            self.fields['organization'].queryset = Organization.objects.filter(user=user)  # Фильтруем организации
        else:
            self.fields['organization'].queryset = Organization.objects.none()  # Если пользователя нет, устанавливаем пустой queryset


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'inn']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].label = 'Название'
        self.fields['inn'].label = 'ИНН'

    def __str__(self):
        return self.name


class InvoiceForm(forms.ModelForm):

    class Meta:
        model = Invoice
        fields = ['number', 'amount', 'payed_amount', 'shipping_amount', 'montage_amount', 'legal_entity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['number'].label = 'Номер'
        self.fields['amount'].label = 'Сумма'
        self.fields['payed_amount'].label = 'Оплачено'
        self.fields['shipping_amount'].label = 'Стоимость доставки'
        self.fields['montage_amount'].label = 'Стоимость монтажа'
        self.fields['legal_entity'].label = 'Юридическое лицо'

    def __str__(self):
        return self.number