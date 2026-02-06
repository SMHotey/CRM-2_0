import ast
from datetime import datetime

from django.utils import timezone
from django.core.exceptions import ValidationError, FieldError
from django.db import models, transaction
from django.db.models import Max
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.templatetags.static import static
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.utils.functional import cached_property

import threading


DEFAULT_NUMBER=100



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
    correspondent_account = models.CharField(max_length=20, blank=True, null=True,
                                             verbose_name="Корреспондентский счет")

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
    phone = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Номер телефона")
    bank_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название банка")
    account_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Расчетный счет")
    bik = models.CharField(max_length=9, blank=True, null=True, verbose_name="БИК")
    correspondent_account = models.CharField(max_length=20, blank=True, null=True,
                                             verbose_name="Корреспондентский счет")

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
    contract_type = models.CharField(max_length=30, choices=CONTRACT_TYPE_CHOICES, default='legal_entity', null=True,
                                     blank=True)
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

    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(fields=['number', 'internal_legal_entity', 'year'], name='unique_field_combination')
    #     ]

    @property
    def percent(self):
        return int(self.payed_amount * 100 / self.amount)


_order_lock = threading.Lock()


class Order(models.Model):

    number = models.IntegerField(default=DEFAULT_NUMBER, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order_file = models.FileField(upload_to='uploads/orders/%Y/%m/%d/')
    invoice = models.ForeignKey('Invoice', related_name='orders', blank=True, null=True, on_delete=models.CASCADE)
    due_date = models.DateField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            # Составной индекс для самого частого запроса (поиск по номеру в году)
            models.Index(
                fields=['created_at', 'number'],
                name='idx_order_year_number_compound'
            ),
            # Индекс для фильтрации по дате создания
            models.Index(fields=['created_at'], name='idx_order_created_at'),
            # Индекс для поиска по номеру
            models.Index(fields=['number'], name='idx_order_number'),
            # Индекс для поиска по дате планируемой готовности
            models.Index(fields=['due_date'], name='idx_order_due_date'),
        ]
        # Ограничение уникальности номера в пределах года
        constraints = [
            models.UniqueConstraint(
                fields=['created_at__year', 'number'],
                name='unique_order_number_per_year',
                violation_error_message="Заказ с таким номером уже существует в этом году"
            ),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ №{self.number or 'N/A'}/{self.created_at.year}"

    @property
    def year(self):
        return self.created_at.year

    def clean(self):
        """Валидация перед сохранением"""
        super().clean()

        pass

    def save(self, *args, **kwargs):
        """
        Автоматическая генерация номера при создании.
        Номер увеличивается на 1 от предыдущего в текущем году.
        Если это первый заказ в году - используется DEFAULT_NUMBER.
        """
        # Определяем, нужно ли генерировать номер
        is_new = self.pk is None
        needs_number_generation = is_new and self.number is None

        if needs_number_generation:
            # Используем блокировку для предотвращения гонок
            with _order_lock:
                with transaction.atomic():
                    # Определяем текущий год
                    current_year = datetime.now().year

                    # Получаем максимальный номер за текущий год с блокировкой
                    max_number = Order.objects.select_for_update().filter(
                        created_at__year=current_year
                    ).aggregate(Max('number'))['number__max']

                    # Определяем следующий номер
                    if max_number is not None:
                        self.number = max_number + 1
                    else:
                        self.number = DEFAULT_NUMBER

        elif is_new and self.number:
            # Проверяем уникальность явно заданного номера
            exists = Order.objects.filter(
                created_at__year=self.year,
                number=self.number
            ).exists()

            if exists:
                raise ValidationError(
                    f'Заказ с номером {self.number} уже существует в {self.year} году'
                )

        # Выполняем валидацию
        self.full_clean()

        # Сохраняем объект
        super().save(*args, **kwargs)

    @property
    def full_number(self):
        """Полный номер в формате ГГГГ/НОМЕР"""
        if self.number:
            return f"{self.year}/{self.number:04d}"
        return "N/A"

    @property
    def is_overdue(self):
        """Просрочен ли заказ (на основе due_date)"""
        if self.due_date:
            return datetime.now().date() > self.due_date
        return False

    # Оптимизированные методы для работы с items

    def _get_filtered_items(self):
        """Базовый запрос отфильтрованных items"""
        return self.items.exclude(p_status__in=['changed'])

    @cached_property
    def filtered_items_cache(self):
        """Кешированный queryset отфильтрованных items"""
        return self._get_filtered_items()

    def _get_items_aggregate(self, filters):
        """Общий метод для агрегации items с использованием cached_property"""
        return self.filtered_items_cache.filter(**filters).aggregate(
            total=Sum('p_quantity')
        )['total'] or 0

    # Оптимизированные свойства с использованием кеша

    @property
    def doors_1_nk(self):
        return self._get_items_aggregate({
            'p_kind': 'door',
            'p_construction': 'NK',
            'p_active_trim': None,
        })

    @property
    def doors_2_nk(self):
        return self._get_items_aggregate({
            'p_kind': 'door',
            'p_construction': 'NK',
            'p_active_trim__isnull': False,
        })

    @property
    def hatch_nk(self):
        return self._get_items_aggregate({
            'p_kind': 'hatch',
            'p_construction': 'NK',
        })

    @property
    def doors_1_sk(self):
        return self._get_items_aggregate({
            'p_kind': 'door',
            'p_construction': 'SK',
            'p_active_trim': None,
        })

    @property
    def doors_2_sk(self):
        return self._get_items_aggregate({
            'p_kind': 'door',
            'p_construction': 'SK',
            'p_active_trim__isnull': False,
        })

    @property
    def hatch_sk(self):
        return self._get_items_aggregate({
            'p_kind': 'hatch',
            'p_construction': 'SK',
        })

    @property
    def transom(self):
        return self._get_items_aggregate({
            'p_kind': 'transom',
        })

    @property
    def gate(self):
        return self._get_items_aggregate({
            'p_kind': 'gate',
            'p_width__lt': 3000,
            'p_height__lt': 3000,
        })

    @property
    def gate_3000(self):
        return self._get_items_aggregate(
            Q(p_kind='gate') & (Q(p_width__gte=3000) | Q(p_height__gte=3000))
        )

    @property
    def glass(self):
        return self._get_items_aggregate(
            Q(p_glass__isnull=False) & ~Q(p_glass={})
        )

    @property
    def quantity(self):
        return self._get_items_aggregate({'p_quantity__gt': 0})

    @cached_property
    def status_calculations(self):
        """Кешированный расчет всех статусов для одного запроса"""
        items = self.filtered_items_cache
        return {
            'in_query': items.filter(p_status='in_query').aggregate(total=Sum('p_quantity'))['total'] or 0,
            'product': items.filter(p_status='product').aggregate(total=Sum('p_quantity'))['total'] or 0,
            'ready': items.filter(p_status='ready').aggregate(total=Sum('p_quantity'))['total'] or 0,
            'shipped': items.filter(p_status='shipped').aggregate(total=Sum('p_quantity'))['total'] or 0,
            'stopped': items.filter(p_status='stopped').aggregate(total=Sum('p_quantity'))['total'] or 0,
            'canceled': items.filter(p_status='canceled').aggregate(total=Sum('p_quantity'))['total'] or 0,
        }

    @property
    def status(self):
        """Оптимизированное вычисление статуса"""
        s = self.status_calculations

        if s['in_query'] > 0 and all(v == 0 for k, v in s.items() if k != 'in_query'):
            return 'в очереди'
        elif s['product'] > 0 and all(v == 0 for k, v in s.items() if k != 'product'):
            return 'запущен'
        elif s['ready'] > 0 and all(v == 0 for k, v in s.items() if k != 'ready'):
            return 'готов'
        elif s['shipped'] > 0 and all(v == 0 for k, v in s.items() if k != 'shipped'):
            return 'отгружен'
        elif s['stopped'] > 0 and all(v == 0 for k, v in s.items() if k != 'stopped'):
            return 'остановлен'
        elif s['canceled'] > 0 and all(v == 0 for k, v in s.items() if k != 'canceled'):
            return 'отменен'
        else:
            return 'частично не готов'

    @cached_property
    def workshop_calculations(self):
        """Кешированный расчет цехов"""
        items = self.filtered_items_cache
        return {
            'ws_1': items.filter(workshop='1').aggregate(total=Sum('p_quantity'))['total'] or 0,
            'ws_3': items.filter(workshop='3').aggregate(total=Sum('p_quantity'))['total'] or 0,
            'stopped': items.filter(workshop='2').aggregate(total=Sum('p_quantity'))['total'] or 0,
        }

    @property
    def workshop_icon_path(self):
        """Оптимизированное вычисление иконки цеха"""
        from django.contrib.staticfiles.storage import staticfiles_storage

        ws = self.workshop_calculations

        if ws['stopped']:
            return staticfiles_storage.url('erp_main/images/pause.png')
        elif ws['ws_1'] and ws['ws_3']:
            return staticfiles_storage.url('erp_main/images/icon_play13.png')
        elif ws['ws_1']:
            return staticfiles_storage.url('erp_main/images/icon_play1.png')
        elif ws['ws_3']:
            return staticfiles_storage.url('erp_main/images/icon_play3.png')
        else:
            return staticfiles_storage.url('erp_main/images/icon_play.png')

    @classmethod
    def get_next_number(cls, year=None):
        """
        Получение следующего номера заказа без создания объекта.
        Полезно для форм и API.
        """
        if year is None:
            year = datetime.now().year

        with _order_lock:
            with transaction.atomic():
                max_number = cls.objects.select_for_update().filter(
                    created_at__year=year
                ).aggregate(Max('number'))['number__max']

                if max_number is not None:
                    return max_number + 1
                return DEFAULT_NUMBER

    @classmethod
    def get_by_full_number(cls, full_number):
        """
        Поиск заказа по полному номеру (ГГГГ/НОМЕР)
        """
        try:
            year_str, number_str = full_number.split('/')
            return cls.objects.get(
                created_at__year=int(year_str),
                number=int(number_str)
            )
        except (ValueError, cls.DoesNotExist, cls.MultipleObjectsReturned):
            return None

    def get_items_summary(self):
        """
        Получение всех агрегированных данных о товарах заказа одним запросом.
        Оптимизация для снижения количества запросов к БД.

        Returns:
            dict: Словарь с агрегированными данными
        """
        from django.db.models import Count, Case, When, Value, IntegerField, Q

        items = self.filtered_items_cache

        # Один сложный запрос вместо множества простых
        summary = items.aggregate(
            # Общее количество товаров
            total_quantity=Sum('p_quantity'),

            # Двери NK без активной отделки
            doors_1_nk=Sum(
                Case(
                    When(
                        p_kind='door',
                        p_construction='NK',
                        p_active_trim=None,
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Двери NK с активной отделкой
            doors_2_nk=Sum(
                Case(
                    When(
                        p_kind='door',
                        p_construction='NK',
                        p_active_trim__isnull=False,
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Люки NK
            hatch_nk=Sum(
                Case(
                    When(
                        p_kind='hatch',
                        p_construction='NK',
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Двери SK без активной отделки
            doors_1_sk=Sum(
                Case(
                    When(
                        p_kind='door',
                        p_construction='SK',
                        p_active_trim=None,
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Двери SK с активной отделкой
            doors_2_sk=Sum(
                Case(
                    When(
                        p_kind='door',
                        p_construction='SK',
                        p_active_trim__isnull=False,
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Люки SK
            hatch_sk=Sum(
                Case(
                    When(
                        p_kind='hatch',
                        p_construction='SK',
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Фрамуги
            transom=Sum(
                Case(
                    When(
                        p_kind='transom',
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Ворота обычные (< 3000)
            gate=Sum(
                Case(
                    When(
                        p_kind='gate',
                        p_width__lt=3000,
                        p_height__lt=3000,
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Ворота большие (≥ 3000)
            gate_3000=Sum(
                Case(
                    When(
                        Q(p_kind='gate') & (Q(p_width__gte=3000) | Q(p_height__gte=3000)),
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Стеклянные элементы
            glass=Sum(
                Case(
                    When(
                        Q(p_glass__isnull=False) & ~Q(p_glass={}),
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Статусы товаров
            in_query_qty=Sum(
                Case(
                    When(
                        p_status='in_query',
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            product_qty=Sum(
                Case(
                    When(
                        p_status='product',
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            ready_qty=Sum(
                Case(
                    When(
                        p_status='ready',
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            shipped_qty=Sum(
                Case(
                    When(
                        p_status='shipped',
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            stopped_qty=Sum(
                Case(
                    When(
                        p_status='stopped',
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            canceled_qty=Sum(
                Case(
                    When(
                        p_status='canceled',
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Распределение по цехам
            ws_1_qty=Sum(
                Case(
                    When(
                        workshop='1',
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            ws_3_qty=Sum(
                Case(
                    When(
                        workshop='3',
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            stopped_ws_qty=Sum(
                Case(
                    When(
                        workshop='2',
                        then='p_quantity'
                    ),
                    default=Value(0),
                    output_field=IntegerField()
                )
            ),

            # Общая статистика
            items_count=Count('id'),
            unique_kinds=Count('p_kind', distinct=True),
            unique_constructions=Count('p_construction', distinct=True),

            # Максимальные размеры
            max_width=Case(
                When(p_width__isnull=False, then=Max('p_width')),
                default=Value(None)
            ),

            max_height=Case(
                When(p_height__isnull=False, then=Max('p_height')),
                default=Value(None)
            ),
        )

        # Вычисляем общую сумму всех дверей NK
        summary['doors_nk_total'] = summary.get('doors_1_nk', 0) + summary.get('doors_2_nk', 0)

        # Вычисляем общую сумму всех дверей SK
        summary['doors_sk_total'] = summary.get('doors_1_sk', 0) + summary.get('doors_2_sk', 0)

        # Вычисляем общую сумму всех дверей (NK + SK)
        summary['doors_total'] = summary['doors_nk_total'] + summary['doors_sk_total']

        # Вычисляем общую сумму всех люков
        summary['hatches_total'] = summary.get('hatch_nk', 0) + summary.get('hatch_sk', 0)

        # Вычисляем общую сумму всех ворот
        summary['gates_total'] = summary.get('gate', 0) + summary.get('gate_3000', 0)

        # Вычисляем процент стеклянных элементов
        if summary['total_quantity'] and summary['total_quantity'] > 0:
            summary['glass_percentage'] = round(
                (summary.get('glass', 0) / summary['total_quantity']) * 100,
                1
            )
        else:
            summary['glass_percentage'] = 0.0

        # Определяем общий статус заказа
        status_qty = {
            'in_query': summary.get('in_query_qty', 0),
            'product': summary.get('product_qty', 0),
            'ready': summary.get('ready_qty', 0),
            'shipped': summary.get('shipped_qty', 0),
            'stopped': summary.get('stopped_qty', 0),
            'canceled': summary.get('canceled_qty', 0),
        }

        if status_qty['in_query'] > 0 and all(v == 0 for k, v in status_qty.items() if k != 'in_query'):
            summary['status'] = 'в очереди'
        elif status_qty['product'] > 0 and all(v == 0 for k, v in status_qty.items() if k != 'product'):
            summary['status'] = 'запущен'
        elif status_qty['ready'] > 0 and all(v == 0 for k, v in status_qty.items() if k != 'ready'):
            summary['status'] = 'готов'
        elif status_qty['shipped'] > 0 and all(v == 0 for k, v in status_qty.items() if k != 'shipped'):
            summary['status'] = 'отгружен'
        elif status_qty['stopped'] > 0 and all(v == 0 for k, v in status_qty.items() if k != 'stopped'):
            summary['status'] = 'остановлен'
        elif status_qty['canceled'] > 0 and all(v == 0 for k, v in status_qty.items() if k != 'canceled'):
            summary['status'] = 'отменен'
        else:
            summary['status'] = 'частично не готов'

        # Определяем иконку цеха
        from django.contrib.staticfiles.storage import staticfiles_storage

        ws_1 = summary.get('ws_1_qty', 0)
        ws_3 = summary.get('ws_3_qty', 0)
        stopped_ws = summary.get('stopped_ws_qty', 0)

        if stopped_ws:
            summary['workshop_icon'] = staticfiles_storage.url('erp_main/images/pause.png')
            summary['workshop_name'] = 'остановлен'
        elif ws_1 and ws_3:
            summary['workshop_icon'] = staticfiles_storage.url('erp_main/images/icon_play13.png')
            summary['workshop_name'] = 'цех 1 и 3'
        elif ws_1:
            summary['workshop_icon'] = staticfiles_storage.url('erp_main/images/icon_play1.png')
            summary['workshop_name'] = 'цех 1'
        elif ws_3:
            summary['workshop_icon'] = staticfiles_storage.url('erp_main/images/icon_play3.png')
            summary['workshop_name'] = 'цех 3'
        else:
            summary['workshop_icon'] = staticfiles_storage.url('erp_main/images/icon_play.png')
            summary['workshop_name'] = 'не назначен'

        # Определяем основной цех
        if ws_1 > ws_3:
            summary['main_workshop'] = '1'
        elif ws_3 > ws_1:
            summary['main_workshop'] = '3'
        else:
            summary['main_workshop'] = None

        # Проверка на просроченные товары (если есть поле due_date в Item)
        try:
            from datetime import date
            overdue_items = items.filter(
                p_due_date__isnull=False,
                p_due_date__lt=date.today(),
                p_status__in=['in_query', 'product']
            ).aggregate(
                overdue_qty=Sum('p_quantity'),
                overdue_count=Count('id')
            )
            summary['overdue_items'] = overdue_items.get('overdue_qty', 0)
            summary['overdue_count'] = overdue_items.get('overdue_count', 0)
        except (AttributeError, FieldError):
            # Поле p_due_date может отсутствовать
            summary['overdue_items'] = 0
            summary['overdue_count'] = 0

        # Добавляем флаг наличия товаров с нестандартными размерами
        summary['has_oversized'] = summary.get('gate_3000', 0) > 0

        # Добавляем флаг наличия товаров со стеклом
        summary['has_glass'] = summary.get('glass', 0) > 0

        # Форматируем числовые значения (заменяем None на 0)
        for key, value in summary.items():
            if isinstance(value, (int, float)) and key not in ['max_width', 'max_height']:
                summary[key] = value or 0

        return summary
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
    internal_legal_entity = models.ForeignKey(InternalLegalEntity, related_name='certificates',
                                              on_delete=models.CASCADE)
    scan_copy = models.FileField(upload_to='uploads/certificates/', blank=True, null=True)
    passport_templates = models.FileField(upload_to='uploads/certificates/passport_templates/',
                                          verbose_name='Шаблон паспорта', blank=True, null=True)


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
    #    item_info = models.OneToOneField(ItemInfo, related_name='order_item', on_delete=models.PROTECT, null=True)
    position_num = models.CharField(max_length=5, verbose_name='номер позиции')
    nameplate_range = models.CharField(max_length=20, blank=True, null=True, verbose_name='номера шильдов')
    p_quantity = models.IntegerField(default=1, verbose_name='количество изделий')
    p_comment = models.TextField(max_length=255, blank=True, null=True, default='', verbose_name='комментарий')
    firm_plate = models.BooleanField(default=False, verbose_name='фирменный шильд')
    mounting_plates = models.CharField(max_length=50, default=False, blank=True, null=True,
                                       verbose_name='монтажные уши')
    workshop = models.IntegerField(default=0, verbose_name='цех')

    def __str__(self):
        return f"{self.order.id} - {self.position_num} - {self.get_p_kind_display()} {self.p_width}x{self.p_height}"

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

    kind = models.CharField(max_length=20, blank=True, null=True, choices=KIND_CHOICE)
    option = models.CharField(max_length=20, blank=True, null=True, choices=OPTIONS_CHOICE)
    order_items = models.ForeignKey(OrderItem, related_name='glasses', blank=True, null=True, on_delete=models.SET_NULL)
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
