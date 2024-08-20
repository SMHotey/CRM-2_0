from django import forms

from erp_main.models import Employee, Organization, Invoice


class UploadFileForm(forms.Form):
    file = forms.FileField()


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['name', 'email', 'phone']


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ['name', 'inn', 'last_order_date']


class InvoiceForm(forms.ModelForm):

    class Meta:
        model = Invoice
        fields = ['number', 'amount', 'payed_amount', 'shipping_amount', 'montage_amount', 'legal_entity']