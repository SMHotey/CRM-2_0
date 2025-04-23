from django import forms
from django.contrib.auth.models import User


from erp_main.models import Organization, Invoice, Order, LegalEntity, OrderItem, Shipment


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
    TYPE_CHOICES = (
        ('organization', 'Юридическое лицо'),
        ('individual', 'Физическое лицо'),
    )
    type = forms.ChoiceField(choices=TYPE_CHOICES, widget=forms.RadioSelect, label='Тип организации', required=False)

    class Meta:
        model = Organization
        fields = ['type', 'name', 'inn', 'phone_number', 'name_fl', 'ceo_footing', 'ogrn', 'kpp',
                  'r_s', 'bank', 'bik', 'k_s', 'address', 'email', 'ceo_title', 'ceo_name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Наименование'}),
            'inn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ИНН'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Номер телефона'}),
            'name_fl': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя, фамилия'}),
            'ceo_footing': forms.Select(attrs={'class': 'form-select'}),
            'ogrn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ОГРН'}),
            'kpp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'КПП'}),
            'r_s': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Р/с'}),
            'bank': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Банк'}),
            'bik': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'БИК'}),
            'k_s': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'К/с'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Адрес'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'ceo_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Должность'}),
            'ceo_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ФИО'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Скрываем поле type при редактировании
            self.fields['type'].widget = forms.HiddenInput()
            self.fields['type'].required = False
        else:
            # При создании новой организации делаем поле обязательным
            self.fields['type'].required = True
        self.fields['name_fl'].label = ''
        self.fields['phone_number'].label = ''
        self.fields['inn'].label = ''
        self.fields['name'].label = ''

    def clean(self):
        cleaned_data = super().clean()
        # Для новой организации проверяем тип
        if not self.instance.pk:
            type_ = cleaned_data.get('type')
            if not type_:
                raise forms.ValidationError("Необходимо выбрать тип организации")

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



