from django import forms

from erp_main.models import Organization, Invoice, Order


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['organization', 'order_file']  # Укажите, какие поля вы хотите отобразить

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Получаем пользователя из kwargs
        super().__init__(*args, **kwargs)
        if user:
            self.fields['organization'].queryset = Organization.objects.filter(user=user)  # Фильтруем организации
        else:
            self.fields['organization'].queryset = Organization.objects.none()  # Если пользователя нет, устанавливаем пустой queryset


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'inn', 'last_order_date']


class InvoiceForm(forms.ModelForm):

    class Meta:
        model = Invoice
        fields = ['number', 'amount', 'payed_amount', 'shipping_amount', 'montage_amount', 'legal_entity']