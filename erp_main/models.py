import ast
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.templatetags.static import static
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

from erp_main.furniture import FurnitureKit, FurnitureKitLock, FurnitureKitHandle, FurnitureKitCylinder


# def validate_numeric_only(value):
#     if not re.match(r'^\d{6,}$', value) and value is not None:
#         raise ValidationError('Поле должно содержать только цифры и минимум 6 символов.')


class DocumentType(models.Model):
    """Типы документов для разных моделей"""
    name = models.CharField(max_length=100, verbose_name="Название типа")
    code = models.CharField(max_length=50, unique=True, verbose_name="Код типа")
    description = models.TextField(blank=True, verbose_name="Описание")

    # Для каких моделей доступен этот тип документа
    available_for_models = models.ManyToManyField(
        ContentType,
        verbose_name="Доступно для моделей",
        blank=True
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тип документа"
        verbose_name_plural = "Типы документов"


class BaseDocumentModel(models.Model):
    """Абстрактная базовая модель для всех сущностей с документами"""

    class DocumentTypes:
        # Общие типы документов
        OTHER = 'other'
        ORDER_BLANK = 'order_blank'

        # Для юридических лиц
        LEGAL_ENTITY_CONTRACT = 'legal_entity_contract'
        LEGAL_ENTITY_ARTICLES = 'legal_entity_articles'
        LEGAL_ENTITY_EGRUL = 'legal_entity_egrul'
        LEGAL_ENTITY_REQUISITES = 'legal_entity_requisites'

        # Для ИП
        INDIVIDUAL_ENTREPRENEUR_CONTRACT = 'individual_entrepreneur_contract'
        INDIVIDUAL_ENTREPRENEUR_EGRIP = 'individual_entrepreneur_egrip'
        INDIVIDUAL_ENTREPRENEUR_REQUISITES = 'individual_entrepreneur_requisites'

        # Для физлиц
        PHYSICAL_PERSON_PASSPORT = 'physical_person_passport'

    def get_available_document_types(self):
        """Возвращает доступные типы документов для этой модели"""
        raise NotImplementedError("Должен быть реализован в дочерних классах")

    class Meta:
        abstract = True


class Documents(models.Model):
    """Сканы документов всех видов"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    number = models.CharField(max_length=50, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    file = models.FileField(upload_to='documents/')

    # Связь с типом документа
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Тип документа"
    )

    # Generic Foreign Key
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)  # Добавлено null=True, blank=True
    content_object = GenericForeignKey('content_type', 'object_id')

    def clean(self):
        """Проверяет, что тип документа доступен для связанной модели"""
        if self.content_object and self.document_type:
            # Проверяем, реализует ли модель метод get_available_document_types
            if hasattr(self.content_object, 'get_available_document_types'):
                available_types = self.content_object.get_available_document_types()
                if self.document_type not in available_types:
                    raise ValidationError(
                        f"Тип документа '{self.document_type}' недоступен для этой модели"
                    )
            else:
                # Если метод не реализован, разрешаем все типы документов
                pass

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.document_type})" if self.document_type else self.name

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"


class InternalLegalEntity(models.Model):
    TYPES = [
        ('LEGAL', 'ООО'),
        ('INDIVIDUAL', 'ИП'),
        ('WITHOUT_INVOICE', 'Без выставления счета'),
    ]

    CEO_TITLES = [
        ('director', 'Директор'),
        ('general_director', 'Генеральный директор'),
    ]

    type = models.CharField(max_length=20, choices=TYPES, verbose_name="Тип")
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название")
    inn = models.CharField(max_length=12, blank=True, null=True, verbose_name="ИНН")
    ogrn = models.CharField(max_length=15, blank=True, null=True, verbose_name="ОГРН")
    kpp = models.CharField(max_length=9, blank=True, null=True, verbose_name="КПП")
    legal_address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Юридический адрес")
    postal_address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Почтовый адрес")
    ceo_title = models.CharField(
        max_length=20,
        choices=CEO_TITLES,
        blank=True,
        null=True,
        verbose_name="Должность руководителя"
    )
    ceo_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="ФИО руководителя")
    email = models.EmailField(blank=True, null=True, verbose_name="Электронная почта")
    bank_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название банка")
    account_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Расчетный счет")
    bik = models.CharField(max_length=9, blank=True, null=True, verbose_name="БИК")
    correspondent_account = models.CharField(max_length=20, blank=True, null=True,
                                             verbose_name="Корреспондентский счет")

    documents = GenericRelation(Documents, verbose_name="Документы")

    def __str__(self):
        if self.name:
            return self.name
        elif self.ceo_name:
            return f"{self.get_type_display()} {self.ceo_name}"
        else:
            return f"{self.get_type_display()} - {self.id if self.id else 'Новый'}"

    class Meta:
        verbose_name = 'Внутреннее юридическое лицо'
        verbose_name_plural = 'Внутренние юридические лица'


class Organization(models.Model):
    """Базовая модель контрагента - теперь НЕ абстрактная"""
    TYPES = [
        ('LEGAL', 'Юридическое лицо'),
        ('INDIVIDUAL', 'Индивидуальный предприниматель'),
        ('PERSON', 'Физическое лицо'),
    ]

    type = models.CharField(max_length=20, choices=TYPES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Менеджер")

    # Делаем поле необязательным в базовой модели
    internal_legal_entity = models.ForeignKey(
        InternalLegalEntity,
        on_delete=models.CASCADE,
        verbose_name="Внутреннее юридическое лицо",
        null=True,  # Разрешаем NULL для физлиц
        blank=True  # Разрешаем пустое значение в формах
    )

    history = models.JSONField(default=list, verbose_name="История изменений")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

   # Связь с документами
    documents = GenericRelation(Documents, verbose_name="Документы по контрагенту")

    @property
    def last_order(self):
        return (
            Order.objects.filter(invoice__organization=self.id)
            .order_by('-created_at')
            .first().created_at if Order.objects.filter(invoice__organization=self.id).exists() else None
        )

    @property
    def bank_name(self):
        if self.type == 'LEGAL' and hasattr(self, 'legalentity'):
            return self.legalentity.bank_name
        elif self.type == 'INDIVIDUAL' and hasattr(self, 'individualentrepreneur'):
            return self.individualentrepreneur.bank_name
        return None
    @property
    def account_number(self):
        if self.type == 'LEGAL' and hasattr(self, 'legalentity'):
            return self.legalentity.account_number
        elif self.type == 'INDIVIDUAL' and hasattr(self, 'individualentrepreneur'):
            return self.individualentrepreneur.account_number
        return None

    @property
    def correspondent_account(self):
        if self.type == 'LEGAL' and hasattr(self, 'legalentity'):
            return self.legalentity.correspondent_account
        elif self.type == 'INDIVIDUAL' and hasattr(self, 'individualentrepreneur'):
            return self.individualentrepreneur.correspondent_account
        return None

    def bik(self):
        if self.type == 'LEGAL' and hasattr(self, 'legalentity'):
            return self.legalentity.bik
        elif self.type == 'INDIVIDUAL' and hasattr(self, 'individualentrepreneur'):
            return self.individualentrepreneur.bik
        return None

    @property
    def display_name(self):
        """Возвращает отображаемое имя в зависимости от типа"""
        if self.type == 'LEGAL' and hasattr(self, 'legalentity'):
            return self.legalentity.name
        elif self.type == 'INDIVIDUAL' and hasattr(self, 'individualentrepreneur'):
            return self.individualentrepreneur.full_name
        elif self.type == 'PERSON' and hasattr(self, 'physicalperson'):
            return self.physicalperson.full_name
        return f"Контрагент {self.id}"

    @property
    def legal_form(self):
        """Возвращает ОГРН/ОГРНИП"""
        if self.type == 'LEGAL' and hasattr(self, 'legalentity'):
            return self.legalentity.legal_form_display
        elif self.type == 'INDIVIDUAL' and hasattr(self, 'individualentrepreneur'):
            return 'ИП'
        return None

    @property
    def inn(self):
        """Возвращает ИНН для юрлиц и ИП"""
        if self.type == 'LEGAL' and hasattr(self, 'legalentity'):
            return self.legalentity.inn
        elif self.type == 'INDIVIDUAL' and hasattr(self, 'individualentrepreneur'):
            return self.individualentrepreneur.inn
        return None

    @property
    def kpp(self):
        """Возвращает КПП для юрлиц"""
        if self.type == 'LEGAL' and hasattr(self, 'legalentity'):
            return self.legalentity.kpp
        return None

    @property
    def ogrn(self):
        """Возвращает ОГРН/ОГРНИП"""
        if self.type == 'LEGAL' and hasattr(self, 'legalentity'):
            return self.legalentity.ogrn
        elif self.type == 'INDIVIDUAL' and hasattr(self, 'individualentrepreneur'):
            return self.individualentrepreneur.ogrn
        return None

    @property
    def email(self):
        """Возвращает ОГРН/ОГРНИП"""
        if self.type == 'LEGAL' and hasattr(self, 'legalentity'):
            return self.legalentity.email
        elif self.type == 'INDIVIDUAL' and hasattr(self, 'individualentrepreneur'):
            return self.individualentrepreneur.email
        elif self.type == 'PERSON' and hasattr(self, 'physicalperson'):
            return self.physicalperson.email
        return None

    @property
    def phone(self):
        """Возвращает телефон для физлиц"""
        if self.type == 'PERSON' and hasattr(self, 'physicalperson'):
            return self.physicalperson.phone
        return None

    @property
    def legal_form_display(self):
        """Возвращает отображаемое название организационно-правовой формы"""
        if self.type == 'LEGAL' and hasattr(self, 'legalentity'):
            return self.legalentity.get_legal_form_display()
        elif self.type == 'INDIVIDUAL':
            return "Индивидуальный предприниматель"
        elif self.type == 'PERSON':
            return "Физическое лицо"
        return ""

    @property
    def leader_name(self):
        """Возвращает ФИО руководителя для юрлиц"""
        if self.type == 'LEGAL' and hasattr(self, 'legalentity'):
            return self.legalentity.leader_name
        return None


    class Meta:
        verbose_name = "Контрагент"
        verbose_name_plural = "Контрагенты"

    def clean(self):
        """Валидация для обязательных полей в зависимости от типа"""
        if self.type in ['LEGAL', 'INDIVIDUAL'] and not self.internal_legal_entity:
            raise ValidationError({
                'internal_legal_entity': 'Для данного типа контрагента обязательно нужно выбрать внутреннее юридическое лицо'
            })

    def get_available_document_types(self):
        """Возвращает доступные типы документов для внутреннего юрлица"""
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(self)
        return DocumentType.objects.filter(available_for_models=content_type)

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def add_history_entry(self, user, action, old_value=None, new_value=None):
        """Добавление записи в историю изменений"""
        entry = {
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user': user.username,
            'action': action,
            'old_value': str(old_value) if old_value else None,
            'new_value': str(new_value) if new_value else None
        }
        self.history.append(entry)
        self.save()

    def __str__(self):
        return self.display_name


class LegalEntity(Organization):
    """Юридическое лицо - контрагент"""
    LEGAL_FORMS = [
        ('OOO', 'ООО'),
        ('ZAO', 'ЗАО'),
        ('AO', 'АО'),
    ]

    LEADER_POSITIONS = [
        ('director', 'Директор'),
        ('general_director', 'Генеральный директор'),
    ]

    legal_form = models.CharField(
        max_length=10,
        choices=LEGAL_FORMS,
        verbose_name="Организационно-правовая форма"
    )
    name = models.CharField(max_length=255, verbose_name="Название организации")
    inn = models.CharField(max_length=12, unique=True, verbose_name="ИНН")

    # Дополнительные поля
    ogrn = models.CharField(max_length=15, blank=True, null=True, verbose_name="ОГРН")
    kpp = models.CharField(max_length=9, blank=True, null=True, verbose_name="КПП")
    legal_address = models.TextField(blank=True, null=True, verbose_name="Юридический адрес")
    postal_address = models.TextField(blank=True, null=True, verbose_name="Почтовый адрес")
    leader_position = models.CharField(
        max_length=20,
        choices=LEADER_POSITIONS,
        blank=True,
        null=True,
        verbose_name="Должность руководителя"
    )
    leader_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ФИО руководителя"
    )
    email = models.EmailField(blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название банка")
    account_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Расчетный счет")
    bik = models.CharField(max_length=9, blank=True, null=True, verbose_name="БИК")
    correspondent_account = models.CharField(max_length=20, blank=True, null=True, verbose_name="Корреспондентский счет")


    def __str__(self):
        return f"{self.get_legal_form_display()} {self.name}"

    def clean(self):
        """Дополнительная валидация для ЮЛ"""
        errors = {}

        if not all([self.legal_form, self.name, self.inn]):
            errors['__all__'] = "Все обязательные поля должны быть заполнены"

        if not self.internal_legal_entity:
            errors[
                'internal_legal_entity'] = "Для юридического лица обязательно нужно выбрать внутреннее юридическое лицо"

        if errors:
            raise ValidationError(errors)

    class Meta:
        verbose_name = "Юридическое лицо"
        verbose_name_plural = "Юридические лица"


class IndividualEntrepreneur(Organization):
    """Индивидуальный предприниматель"""
    full_name = models.CharField(max_length=255, verbose_name="ФИО ИП")
    inn = models.CharField(max_length=12, unique=True, verbose_name="ИНН")

    # Дополнительные поля
    ogrn = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name="ОГРНИП"
    )
    legal_address = models.TextField(
        blank=True,
        null=True,
        verbose_name="Юридический адрес"
    )
    email = models.EmailField(blank=True, null=True, )
    bank_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название банка")
    account_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Расчетный счет")
    bik = models.CharField(max_length=9, blank=True, null=True, verbose_name="БИК")
    correspondent_account = models.CharField(max_length=20, blank=True, null=True, verbose_name="Корреспондентский счет")

    def __str__(self):
        return f"ИП {self.full_name}"

    def clean(self):
        """Дополнительная валидация для ИП"""
        errors = {}

        if not all([self.full_name, self.inn]):
            errors['__all__'] = "Все обязательные поля должны быть заполнены"

        if not self.internal_legal_entity:
            errors['internal_legal_entity'] = "Для ИП обязательно нужно выбрать внутреннее юридическое лицо"

        if errors:
            raise ValidationError(errors)

    class Meta:
        verbose_name = "Индивидуальный предприниматель"
        verbose_name_plural = "Индивидуальные предприниматели"


class PhysicalPerson(Organization):
    """Физическое лицо"""
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    phone = models.CharField(max_length=20, unique=True, verbose_name="Номер телефона")

    # Дополнительные поля
    email = models.EmailField(blank=True, null=True)
    passport_scan = models.FileField(
        upload_to='passport_scans/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="Скан паспорта"
    )

    def __str__(self):
        return self.full_name

    def clean(self):
        """Валидация для физлица"""
        if not all([self.full_name, self.phone]):
            raise ValidationError("Все обязательные поля должны быть заполнены")

    class Meta:
        verbose_name = "Физическое лицо"
        verbose_name_plural = "Физические лица"

class ContractTemplate(models.Model):
    CONTRACT_TYPE_CHOICES = (
        ('legal_entity', 'Юридическое лицо'),
        ('individual_entrepreneur', 'Индивидуальный предприниматель'),
        ('physical_person', 'Физическое лицо'),
    )

    name = models.CharField(max_length=100)
    contract_type = models.CharField(max_length=30, choices=CONTRACT_TYPE_CHOICES,default='legal_entity', null=True, blank=True)
    internal_legal_entity = models.ForeignKey(InternalLegalEntity, on_delete=models.CASCADE, null=True, blank=True)
    organization_type = models.CharField(max_length=100, choices=(
        ('ooo', 'ООО'),
        ('ao', 'АО'),
        ('zao', 'ЗАО'),
    ), null=True, blank=True)
    footing_type = models.CharField(max_length=10, choices=(
        ('ustav', 'устава'),
        ('attorney', 'доверенности')
    ), null=True, blank=True)
    attorney_number = models.CharField(max_length=50, blank=True, null=True)
    attorney_date = models.DateField(blank=True, null=True)
    attorney_file = models.FileField(upload_to='attorney_files/', null=True, blank=True)
    file = models.FileField(upload_to='contract_templates/')
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class Invoice(models.Model):
    number = models.CharField(max_length=5, blank=True, null=True)
    organization = models.ForeignKey(Organization, related_name='organization', on_delete=models.CASCADE)
    date = models.DateField()
    amount = models.IntegerField(default=0)
    payed_amount = models.IntegerField(default=0)
    shipping_amount = models.IntegerField(default=0)
    montage_amount = models.IntegerField(default=0)
    internal_legal_entity = models.ForeignKey(InternalLegalEntity, related_name='invoices', on_delete=models.CASCADE)
    invoice_file = models.FileField(upload_to='invoices/', blank=True, null=True)
    year = models.PositiveIntegerField(editable=False)
    is_paid = models.BooleanField(default=False, blank=True, null=True)
    change_date = models.DateField(blank=True, null=True)
    closing_document = models.FileField(upload_to='closing_documents/', blank=True, null=True)

    def save(self, *args, **kwargs):
        self.is_paid = self.payed_amount >= self.amount
        if not self.pk:
            self.year = self.date.year
        self.change_date = self.date
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Счет № {self.number}'

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['number', 'internal_legal_entity', 'year'], name='unique_field_combination')
        ]

    @property
    def percent(self):
        return int(self.payed_amount * 100 / self.amount)

class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    order_file = models.FileField(upload_to='uploads/')
    invoice = models.ForeignKey(Invoice, related_name='invoice', blank=True, null=True, on_delete=models.CASCADE)
    due_date = models.DateField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)

    def get_items_filtered(self):
        return self.items.exclude(p_status__in=['changed',])

    @property
    def doors_1_nk(self):
        return self.get_items_filtered().filter(
            p_kind='door',
            p_construction='NK',
            p_active_trim=None,
        ).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def doors_2_nk(self):
        return self.get_items_filtered().filter(
            p_kind='door',
            p_construction='NK',
            p_active_trim__isnull=False,
        ).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def hatch_nk(self):
        return self.get_items_filtered().filter(
            p_kind='hatch',
            p_construction='NK',
        ).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def doors_1_sk(self):
        return self.get_items_filtered().filter(
            p_kind='door',
            p_construction='SK',
            p_active_trim=None,
        ).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def doors_2_sk(self):
        return self.get_items_filtered().filter(
            p_kind='door',
            p_construction='SK',
            p_active_trim__isnull=False,
        ).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def hatch_sk(self):
        return self.get_items_filtered().filter(
            p_kind='hatch',
            p_construction='SK',
        ).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def transom(self):
        return self.get_items_filtered().filter(
            p_kind='transom',
        ).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def gate(self):
        return self.get_items_filtered().filter(
            p_kind='gate',
            p_width__lt=3000,
            p_height__lt=3000,
        ).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def gate_3000(self):
        return self.get_items_filtered().filter(
            Q(p_kind='gate') & (Q(p_width__gte=3000) | Q(p_height__gte=3000)),
        ).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def glass(self):
        return self.get_items_filtered().filter(Q(p_glass__isnull=False) &
                                                ~Q(p_glass={})).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def quantity(self):
        return self.get_items_filtered().filter(p_quantity__gt=0).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def status(self):
        in_query = self.get_items_filtered().filter(p_status='in_query').aggregate(total=Sum('p_quantity'))['total'] or 0
        product = self.get_items_filtered().filter(p_status='product').aggregate(total=Sum('p_quantity'))['total'] or 0
        ready = self.get_items_filtered().filter(p_status='ready').aggregate(total=Sum('p_quantity'))['total'] or 0
        shipped = self.get_items_filtered().filter(p_status='shipped').aggregate(total=Sum('p_quantity'))['total'] or 0
        stopped = self.get_items_filtered().filter(p_status='stopped').aggregate(total=Sum('p_quantity'))['total'] or 0
        canceled = self.get_items_filtered().filter(p_status='canceled').aggregate(total=Sum('p_quantity'))['total'] or 0

        if in_query > 0 and product == 0 and ready == 0 and shipped == 0:
            return f'в очереди'
        elif in_query == 0 and product > 0 and ready == 0 and shipped == 0:
            return f'запущен'
        elif in_query == 0 and product == 0 and ready > 0 and shipped == 0:
            return f'готов'
        elif in_query == 0 and product == 0 and ready == 0 and shipped > 0:
            return f'отгружен'
        elif stopped > 0 and product == 0 and ready == 0 and shipped == 0:
            return f'остановлен'
        elif canceled > 0 and product == 0 and ready == 0 and shipped == 0:
            return f'отменен'
        else:
            return f'частично не готов'

    @property
    def workshop(self):
        ws_1 = self.get_items_filtered().filter(workshop='1').aggregate(total=Sum('p_quantity'))['total'] or 0
        ws_3 = self.get_items_filtered().filter(workshop='3').aggregate(total=Sum('p_quantity'))['total'] or 0
        stopped = self.get_items_filtered().filter(workshop='2').aggregate(total=Sum('p_quantity'))['total'] or 0
        icon_path = static('erp_main/images/icon_play.png')
        if ws_1:
            icon_path = static('erp_main/images/icon_play1.png')
        if ws_3:
            icon_path = static('erp_main/images/icon_play3.png')
        if ws_1 and ws_3:
            icon_path = static('erp_main/images/icon_play13.png')
        if stopped:
            icon_path = static('erp_main/images/pause.png')

        return icon_path


class OrderChangeHistory(models.Model):
    order = models.ForeignKey(Order, related_name='changes', on_delete=models.CASCADE)
    order_file = models.FileField(upload_to='uploads/', blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField(blank=True, null=True)

class Certificate(models.Model):
    KIND_CHOICE = (
        ('door', 'Дверь'),
        ('gate', 'Ворота'),
        ('hatch', 'Люк'),
        ('transom', 'Фрамуга')
    )
    TYPE_CHOICE = (
        ('tech', 'тех.'),
        ('ei-60', 'EI-60'),
        ('eis-60', 'EIS-60'),
        ('eiws-60', 'EIWS-60')
    )
    numbers = models.CharField(max_length=20, blank=True, null=True)
    p_kind = models.CharField(max_length=15, choices=KIND_CHOICE, verbose_name='вид изделия')
    p_type = models.CharField(max_length=10, choices=TYPE_CHOICE, verbose_name='тип изделия')
    internal_legal_entity = models.ForeignKey(InternalLegalEntity, related_name='certificates', on_delete=models.CASCADE)
    scan_copy = models.FileField(upload_to='uploads/certificates/', blank=True, null=True)
    passport_templates = models.FileField(upload_to='uploads/certificates/passport_templates/',verbose_name='Шаблон паспорта', blank=True, null=True)


class OrderItem(models.Model):
    KIND_CHOICE = (
        ('door', 'Дверь'),
        ('gate', 'Ворота'),
        ('hatch', 'Люк'),
        ('transom', 'Фрамуга'),
        ('dobor', 'Добор'),
        ('others', 'Прочее'),
        ('wickit', 'Калитка')
    )
    TYPE_CHOICE = (
        ('tech', 'тех.'),
        ('ei-60', 'EI-60'),
        ('eis-60', 'EIS-60'),
        ('eiws-60', 'EIWS-60'),
        ('flat', 'квартир.'),
        ('one_layer', 'однолист.'),
        ('revision', 'ревиз.'),
        ('None', '')
    )
    CONSTRUCTION_CHOICE = (
        ('SK', 'старый конструктив'),
        ('NK', 'новый конструктив')
    )
    STATUS_CHOICE = (
        ('in_query', 'в очереди'),
        ('product', 'запущен'),
        ('ready', 'готов'),
        ('shipped', 'отгружен'),
        ('canceled', 'отменен'),
        ('stopped', 'остановлен'),
        ('changed', 'изменен'),
    )

    p_kind = models.CharField(max_length=15, null=True, choices=KIND_CHOICE, verbose_name='вид изделия')
    p_type = models.CharField(max_length=10, choices=TYPE_CHOICE, verbose_name='тип изделия')
    p_construction = models.CharField(max_length=10, choices=CONSTRUCTION_CHOICE, blank=True, null=True,
                                      verbose_name='конструктив изделия')
    p_status = models.CharField(max_length=15, default='in_query', choices=STATUS_CHOICE, verbose_name='статус')

    p_width = models.IntegerField(default=0, verbose_name='ширина изделия')
    p_height = models.IntegerField(default=0, verbose_name='высота изделия')

    p_open = models.CharField(max_length=100, blank=True, null=True,
                              choices=(('right', 'R'), ('left', 'L')),
                              verbose_name='открывание')
    p_active_trim = models.IntegerField(default=0, blank=True, null=True, verbose_name='ширина активной створки')

    # Поле для хранения кодовой строки фурнитуры
    p_furniture = models.CharField(max_length=100, blank=True, null=True, verbose_name='фурнитура')

    p_ral = models.CharField(max_length=50, blank=True, null=True, verbose_name='RAL')

    p_platband = models.CharField(max_length=50, blank=True, null=True, verbose_name='наличник')
    p_door_closer = models.CharField(max_length=50, blank=True, null=True, verbose_name='доводчик')

    p_step = models.CharField(max_length=20, blank=True, null=True, verbose_name='порог')

    p_metal = models.CharField(max_length=50, blank=True, null=True, verbose_name='толщина металла')

    p_vent_grate = models.CharField(max_length=50, blank=True, null=True, verbose_name='вент.решетка')

    p_plate = models.CharField(max_length=100, blank=True, null=True, verbose_name='отбойная пластина')

    p_glass = models.CharField(max_length=100, blank=True, null=True, verbose_name='остекление')

    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name='заказ')
    position_num = models.CharField(max_length=5, verbose_name='номер позиции')
    nameplate_range = models.CharField(max_length=20, blank=True, null=True, verbose_name='номера шильдов')
    p_quantity = models.IntegerField(default=1, verbose_name='количество изделий')
    p_comment = models.TextField(max_length=255, blank=True, null=True, default='', verbose_name='комментарий')
    firm_plate = models.BooleanField(default=True, verbose_name='фирменный шильд')
    mounting_plates = models.CharField(max_length=50, default=False, blank=True, null=True,
                                       verbose_name='монтажные уши')
    workshop = models.IntegerField(default=0, verbose_name='цех')

    def __str__(self):
        return f"{self.order.id} - {self.position_num} - {self.get_p_kind_display()} {self.p_width}x{self.p_height}"

    def generate_furniture_codes_string(self):
        def format_furniture_items(items, item_attr_name):
            """Форматирует элементы фурнитуры одного типа"""
            if not items.exists():
                return "00"

            codes = []
            for item in items.order_by('id'):
                # Получаем объект фурнитуры через указанный атрибут
                furniture_item = getattr(item, item_attr_name, None)
                if not furniture_item:
                    codes.append("00")
                    continue

                # Пытаемся получить код через метод get_code() если он есть
                if hasattr(furniture_item, 'get_code'):
                    code = furniture_item.get_code()
                # Иначе берем поле code или name
                elif hasattr(furniture_item, 'code') and furniture_item.code:
                    code = furniture_item.code
                elif hasattr(furniture_item, 'name') and furniture_item.name:
                    code = furniture_item.name
                else:
                    code = "00"

                codes.append(str(code))

            return ".".join(codes)

        try:
            # Получаем связанный комплект фурнитуры
            furniture_kit = self.furniture_kit

            # Форматируем каждый тип фурнитуры
            lock_str = format_furniture_items(
                furniture_kit.furniturekitlock_set.all(),
                'door_lock'
            )
            handle_str = format_furniture_items(
                furniture_kit.furniturekithandle_set.all(),
                'door_handle'
            )
            # Исправляем имя атрибута для цилиндров (согласно исправленной модели)
            cylinder_str = format_furniture_items(
                furniture_kit.furniturekitcylinder_set.all(),
                'lock_cylinder'
            )

            result = f"{lock_str}-{handle_str}-{cylinder_str}"

            # Сохраняем сгенерированную строку в поле p_furniture
            self.p_furniture = result
            # Сохраняем только поле p_furniture, чтобы не трогать другие поля
            self.save(update_fields=['p_furniture'])

            return result

        except (FurnitureKit.DoesNotExist, AttributeError):
            # Если комплекта нет, возвращаем текущее значение из p_furniture или дефолтную строку
            if self.p_furniture:
                return self.p_furniture
            return "00-00-00"

    def update_furniture_codes(self):
        """Обновляет поле p_furniture на основе данных из комплекта фурнитуры"""
        return self.generate_furniture_codes_string()

    @property
    def furniture_codes(self):
        """Свойство для удобного доступа к кодам фурнитуры"""
        # Если есть данные в p_furniture, возвращаем их
        if self.p_furniture:
            return self.p_furniture

        # Иначе пытаемся сгенерировать и сохранить
        try:
            return self.generate_furniture_codes_string()
        except:
            return "00-00-00"

    def get_furniture_items(self):
        """
        Возвращает все элементы фурнитуры для этой позиции в структурированном виде
        """
        try:
            furniture_kit = self.furniture_kit
            return {
                'locks': [item.door_lock for item in furniture_kit.furniturekitlock_set.all()],
                'handles': [item.door_handle for item in furniture_kit.furniturekithandle_set.all()],
                'cylinders': [item.lock_cylinder for item in furniture_kit.furniturekitcylinder_set.all()],
            }
        except (FurnitureKit.DoesNotExist, AttributeError):
            return {'locks': [], 'handles': [], 'cylinders': []}

    def has_furniture_kit(self):
        """Проверяет, есть ли у позиции комплект фурнитуры"""
        return hasattr(self, 'furniture_kit') and self.furniture_kit is not None

    def create_furniture_kit_if_needed(self):
        """Создает пустой комплект фурнитуры, если его нет"""
        if not self.has_furniture_kit():
            kit = FurnitureKit.objects.create(order_item=self)
            return kit
        return self.furniture_kit

    def add_furniture_item(self, item_type, item_object, quantity=1):
        """
        Добавляет элемент фурнитуры в комплект и обновляет p_furniture

        Args:
            item_type: 'lock', 'handle' или 'cylinder'
            item_object: объект DoorLock, DoorHandle или LockCylinder
            quantity: количество
        """
        # Создаем комплект, если его нет
        self.create_furniture_kit_if_needed()

        furniture_kit = self.furniture_kit

        if item_type == 'lock':
            FurnitureKitLock.objects.get_or_create(
                furniture_kit=furniture_kit,
                door_lock=item_object,
                defaults={'quantity': quantity}
            )
        elif item_type == 'handle':
            FurnitureKitHandle.objects.get_or_create(
                furniture_kit=furniture_kit,
                door_handle=item_object,
                defaults={'quantity': quantity}
            )
        elif item_type == 'cylinder':
            FurnitureKitCylinder.objects.get_or_create(
                furniture_kit=furniture_kit,
                lock_cylinder=item_object,
                defaults={'quantity': quantity}
            )

        # Автоматически обновляем поле p_furniture после добавления
        self.update_furniture_codes()

    def remove_furniture_item(self, item_type, item_object):
        """
        Удаляет элемент фурнитуры из комплекта и обновляет p_furniture
        """
        if not self.has_furniture_kit():
            return

        furniture_kit = self.furniture_kit

        if item_type == 'lock':
            FurnitureKitLock.objects.filter(
                furniture_kit=furniture_kit,
                door_lock=item_object
            ).delete()
        elif item_type == 'handle':
            FurnitureKitHandle.objects.filter(
                furniture_kit=furniture_kit,
                door_handle=item_object
            ).delete()
        elif item_type == 'cylinder':
            FurnitureKitCylinder.objects.filter(
                furniture_kit=furniture_kit,
                lock_cylinder=item_object
            ).delete()

        # Автоматически обновляем поле p_furniture после удаления
        self.update_furniture_codes()

    def clear_furniture_kit(self):
        """Очищает весь комплект фурнитуры"""
        if self.has_furniture_kit():
            self.furniture_kit.furniturekitlock_set.all().delete()
            self.furniture_kit.furniturekithandle_set.all().delete()
            self.furniture_kit.furniturekitcylinder_set.all().delete()
            self.update_furniture_codes()

    def save(self, *args, **kwargs):
        """Переопределяем save для автоматического обновления p_furniture при изменении комплекта"""
        # Сначала сохраняем объект
        super().save(*args, **kwargs)

        # Если есть комплект фурнитуры, обновляем p_furniture
        if self.has_furniture_kit():
            # Обновляем только если еще не обновляли в этом же save
            if 'update_fields' not in kwargs or 'p_furniture' not in kwargs.get('update_fields', []):
                self.update_furniture_codes()

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        ordering = ['order', 'position_num']

    @property
    def d_glass(self):
        if self.p_glass != '{}':
            data = ast.literal_eval(self.p_glass)
            result = '<br>'.join(f"({key[0]}x{key[1]}): {value}" for key, value in data.items())
            return result
        else:
            return 'нет'

class GlassInfo(models.Model):
    KIND_CHOICE = (
        ('pp', 'п/п'),
        ('spo', 'СПО'),
        ('zkl', 'закаленное'),
        ('sp_2', '2-кам. стеклопакет'),
        ('triplex', 'триплекс')
    )
    OPTIONS_CHOICE = (
        ('a1_1', 'пленка A1 с одной стороны'),
        ('a1_2', 'пленка A1 с двух сторон'),
        ('a2_1', 'пленка A2 с одной стороны'),
        ('a2_2', 'пленка A2 с двух сторон'),
        ('a3_1', 'пленка A3 с одной стороны'),
        ('a3_2', 'пленка A3 с двух сторон'),
    )
    GLASS_STATUS_CHOICE = (
        ('not_ordered', 'не заказано'),
        ('ordered', 'заказано'),
        ('ready', 'изготовлено'),
        ('received', 'получено'),
    )

    kind = models.CharField(max_length=20, blank=True, null=True,choices=KIND_CHOICE)
    option = models.CharField(max_length=20, blank=True, null=True, choices=OPTIONS_CHOICE)
    order_items = models.ForeignKey(OrderItem, related_name='glasses',blank=True, null=True, on_delete=models.SET_NULL)
    height = models.IntegerField(blank=True, null=True)
    width = models.IntegerField(blank=True, null=True)
    depth = models.IntegerField(blank=True, null=True)
    quantity = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=100, blank=True, null=True, choices=GLASS_STATUS_CHOICE)
    comment = models.TextField(max_length=255, blank=True, null=True, default='')

    def __hash__(self):
        if self.pk:
            return hash(self.pk)
        return hash(id(self))

    def __eq__(self, other):
        if not isinstance(other, GlassInfo):
            return NotImplemented
        return (
                self.kind == other.kind and
                self.option == other.option and
                self.height == other.height and
                self.width == other.width and
                self.depth == other.depth and
                self.quantity == other.quantity and
                self.comment == other.comment
        )

class Nameplate(models.Model):
    order_item = models.ForeignKey(
        OrderItem,
        related_name='nameplates',
        on_delete=models.CASCADE,
        db_column='order_item_id'
    )
    certificate = models.ForeignKey(
        Certificate,
        related_name='nameplates',
        on_delete=models.CASCADE,
        db_column='certificate_id'
    )
    first_value = models.IntegerField(blank=True, null=True)
    end_value = models.IntegerField(blank=True, null=True)
    issue_date = models.DateField(blank=True, null=True, verbose_name='Дата выдачи')

    class Meta:
        verbose_name = 'Шильд'
        verbose_name_plural = 'Шильды'
        db_table = 'erp_main_nameplate'

    def __str__(self):
        if self.end_value:
            return f"Шильды {self.first_value}-{self.end_value}"
        else:
            return f"Шильд {self.first_value}"

class Contract(models.Model):
    number = models.CharField(unique=True, max_length=100, blank=True, null=True)
    organization = models.ForeignKey(Organization, related_name='contracts', on_delete=models.CASCADE)
    internal_legal_entity = models.ForeignKey(InternalLegalEntity, related_name='contracts', on_delete=models.CASCADE)
    file = models.FileField(upload_to='contracts/')
    days = models.IntegerField(blank=True, null=True)


class Shipment(models.Model):
    SHIPMENT_TYPES = [
        ('pickup', 'самовывоз'),
        ('our', 'наша'),
        ('tk', 'ТК'),
    ]
    user = models.ForeignKey(User, related_name='shipments', on_delete=models.CASCADE)
    order = models.ForeignKey(Order, related_name='shipments', on_delete=models.CASCADE)
    workshop = models.IntegerField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    time = models.TimeField(blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    comments = models.CharField(max_length=100, blank=True, null=True)
    price = models.IntegerField(blank=True, null=True)
    order_items = models.JSONField(blank=True, null=True)
    car_info = models.JSONField(blank=True, null=True)
    driver_info = models.JSONField(blank=True, null=True)
    shipment_type = models.CharField(max_length=20, choices=SHIPMENT_TYPES, default='pickup')

    def can_edit(self, user):
        return user.is_superuser or self.user == user


# class StockOperation(models.Model):
#     """Операция со складом (приход/резерв/списание)"""
#     OPERATION_TYPES = [
#         ('receipt', 'Приход'),
#         ('reservation', 'Резервирование'),
#         ('consumption', 'Списание'),
#         ('cancel_reservation', 'Отмена резерва'),
#     ]
#
#     operation_type = models.CharField(
#         max_length=20,
#         choices=OPERATION_TYPES,
#         verbose_name='Тип операции'
#     )
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата операции')
#     created_by = models.ForeignKey(
#         User,
#         on_delete=models.PROTECT,
#         verbose_name='Создал'
#     )
#     comment = models.TextField(blank=True, null=True, verbose_name='Комментарий')
#
#     # Для приходов
#     invoice_number = models.CharField(
#         max_length=50,
#         blank=True,
#         null=True,
#         verbose_name='Номер накладной'
#     )
#     supplier = models.CharField(
#         max_length=100,
#         blank=True,
#         null=True,
#         verbose_name='Поставщик'
#     )
#
#     class Meta:
#         verbose_name = 'Операция со складом'
#         verbose_name_plural = 'Операции со складом'
#         ordering = ['-created_at']
#
#     def __str__(self):
#         return f"{self.get_operation_type_display()} от {self.created_at.date()}"


# class StockOperationItem(models.Model):
#     """Позиция в операции со складом"""
#     operation = models.ForeignKey(
#         StockOperation,
#         on_delete=models.CASCADE,
#         related_name='items',
#         verbose_name='Операция'
#     )
#
#     # Универсальная связь с любой моделью фурнитуры
#     content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
#     object_id = models.PositiveIntegerField()
#     item = models.GenericForeignKey('content_type', 'object_id')
#
#     quantity = models.PositiveIntegerField(
#         verbose_name='Количество'
#     )
    #
    # # Для приходов - цена закупки
    # purchase_price = models.DecimalField(
    #     max_digits=10,
    #     decimal_places=2,
    #     blank=True,
    #     null=True,
    #     verbose_name='Цена закупки'
    # )
    #
    # class Meta:
    #     verbose_name = 'Позиция операции'
    #     verbose_name_plural = 'Позиции операций'
    #
    # def __str__(self):
    #     return f"{self.item}: {self.quantity} шт."