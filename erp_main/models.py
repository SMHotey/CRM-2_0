import ast
import re
from django.core.exceptions import ValidationError
from django.db import models
from datetime import datetime
from django.contrib.auth.models import User
from django.db.models import Q, Sum


def validate_numeric_only(value):
    if not re.match(r'^\d{6,}$', value) and value is not None:
        raise ValidationError('Поле должно содержать только цифры и минимум 6 символов.')


class Organization(models.Model):
    FOOTING_CHOICES = (
        ('ustav', 'устава'),
        ('attorney', 'доверенности')
    )
    KIND_CHOICES = (
        ('ooo', 'ООО'),
        ('ao', 'АО'),
        ('zao', 'ЗАО'),
        ('ip', 'ИП'),
    )

    kind = models.CharField(max_length=100, blank=True, null=True, choices=KIND_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    name_fl = models.CharField(max_length=15, blank=True, null=True)
    user = models.ForeignKey(User, related_name='organizations', on_delete=models.CASCADE)
    ceo_footing = models.CharField(max_length=30, choices=FOOTING_CHOICES)
    name = models.CharField(max_length=100, blank=True, null=True)
    inn = models.CharField(max_length=15, blank=True, null=True)
    ogrn = models.CharField(max_length=15, blank=True, null=True)
    kpp = models.CharField(max_length=15, blank=True, null=True)
    r_s = models.CharField(max_length=25, blank=True, null=True)
    bank = models.CharField(max_length=300, blank=True, null=True)
    bik = models.CharField(max_length=10, blank=True, null=True)
    k_s = models.CharField(max_length=25, blank=True, null=True)
    address = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    ceo_title = models.CharField(max_length=30, blank=True, null=True)
    ceo_name = models.CharField(max_length=150, blank=True, null=True)
    contracts = models.FileField(upload_to='contracts/', blank=True, null=True)

    def __str__(self):
        if self.name_fl:
            return f'{self.name_fl} ({self.phone_number})'
        return self.name

    class Meta:
        verbose_name_plural = 'Организации'

    @property
    def last_order(self):
        return (
            Order.objects.filter(invoice__organization=self.id)
            .order_by('-created_at')
            .first().created_at if Order.objects.filter(invoice__organization=self.id).exists() else None
        )


class LegalEntity(models.Model):
    name = models.CharField(max_length=255)
    inn = models.CharField(max_length=12, unique=True)
    ogrn = models.CharField(max_length=15, unique=True)
    kpp = models.CharField(max_length=9)
    r_s = models.CharField(max_length=20)
    bank = models.CharField(max_length=255)
    bik = models.CharField(max_length=9)
    k_s = models.CharField(max_length=20)
    address = models.CharField(max_length=255)
    email = models.EmailField()
    ceo_title = models.CharField(max_length=100)
    ceo_name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Юридические лица'


class Invoice(models.Model):
    number = models.CharField(max_length=5, blank=True, null=True)
    organization = models.ForeignKey(Organization, related_name='organization', on_delete=models.CASCADE)
    date = models.DateField()
    amount = models.IntegerField(default=0)
    payed_amount = models.IntegerField(default=0)
    shipping_amount = models.IntegerField(default=0)
    montage_amount = models.IntegerField(default=0)
    legal_entity = models.ForeignKey(LegalEntity, related_name='legal_entity', on_delete=models.CASCADE)
    invoice_file = models.FileField(upload_to='invoices/', blank=True, null=True)
    year = models.PositiveIntegerField(editable=False)
    is_paid = models.BooleanField(default=False, blank=True, null=True)
    change_date = models.DateField(blank=True, null=True)

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
            models.UniqueConstraint(fields=['number', 'legal_entity', 'year'], name='unique_field_combination')
        ]


#def order_file_upload_to(instance, filename):
#        # Создает уникальный путь для каждого загружаемого файла
#    return os.path.join('uploads', f"{now().strftime('%Y%m%d_%H%M%S')}_{filename}")


class Order(models.Model):
    internal_order_number = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order_file = models.FileField(upload_to='uploads/')
    invoice = models.ForeignKey(Invoice, related_name='invoice',blank=True, null=True, on_delete=models.CASCADE)
    due_date = models.DateField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)

    def get_items_filtered(self):
        return self.items.exclude(p_status__in=['changed', 'canceled'])

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
    def status(self): # раскидываем позиции по статусам
        in_query = self.get_items_filtered().filter(p_status='in_query').aggregate(total=Sum('p_quantity'))['total'] or 0
        product = self.get_items_filtered().filter(p_status='product').aggregate(total=Sum('p_quantity'))['total'] or 0
        ready = self.get_items_filtered().filter(p_status='ready').aggregate(total=Sum('p_quantity'))['total'] or 0
        shipped = self.get_items_filtered().filter(p_status='shipped').aggregate(total=Sum('p_quantity'))['total'] or 0
        if in_query > 0 and product == 0 and ready == 0 and shipped == 0:
            return f'в очереди'
        elif in_query == 0 and product > 0 and ready == 0 and shipped == 0:
            return f'запущен'
        elif in_query == 0 and product == 0 and ready > 0 and shipped == 0:
            return f'готов'
        elif in_query == 0 and product == 0 and ready == 0 and shipped > 0:
            return f'отгружен'
        else:
            return f'всё сложно'

    def save(self, *args, **kwargs):  # Переопределение метода save класса models.Model
        if not self.internal_order_number:  # Проверка, если внутренний номер не установлен
            self.internal_order_number = self.generate_internal_order_number()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_internal_order_number():
        return datetime.now().strftime('%Y%m%d%H%M%S')


class OrderChangeHistory(models.Model):
    order = models.ForeignKey(Order, related_name='changes', on_delete=models.CASCADE)
    previous_internal_order_number = models.CharField(max_length=255)  # Старый внутренний номер
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE)


class OrderItem(models.Model):
    KIND_CHOICE = (
        ('door', 'Дверь'),
        ('gate', 'Ворота'),
        ('hatch', 'Люк'),
        ('transom', 'Фрамуга'),
        ('dobor', 'Добор'),
        ('others', 'Прочее')
    )
    TYPE_CHOICE = (
        ('tech', 'тех.'),
        ('ei-60', 'EI-60'),
        ('eis-60', 'EIS-60'),
        ('eiws-60', 'EIWS-60'),
        ('flat', 'квартир.'),
        ('one_layer', 'однолист.'),
        ('revision', 'ревиз.')
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

    p_kind = models.CharField(max_length=100, null=True, choices=KIND_CHOICE)
    p_type = models.CharField(max_length=100, choices=TYPE_CHOICE)
    p_construction = models.CharField(max_length=100, choices=CONSTRUCTION_CHOICE, blank=True, null=True)
    p_width = models.DecimalField(max_digits=10, decimal_places=0)
    p_height = models.DecimalField(max_digits=10, decimal_places=0)
    p_open = models.CharField(max_length=2, blank=True, null=True) # открывание
    p_active_trim = models.CharField(max_length=5, blank=True, null=True) # активная створка
    p_furniture = models.CharField(max_length=100, blank=True, null=True) # словарь: код - количество по замку, ручке и ц/м
    p_ral = models.CharField(max_length=100, blank=True, null=True) # расписать по элементам (возможные вариации, опции цвета)
    p_platband = models.CharField(max_length=100, blank=True, null=True) # наличники: размер с каждой стороны
    p_door_closer = models.CharField(max_length=100, blank=True, null=True) # доводчик
    p_step = models.CharField(max_length=100, blank=True, null=True) # порог
    p_metal = models.CharField(max_length=100, blank=True, null=True) # возможные компановки толщины металла изделия
    p_vent_grate = models.CharField(max_length=100, blank=True, null=True) # вент. решетки (тип, размер, толщина, кол-во)
    p_plate = models.CharField(max_length=100, blank=True, null=True) # отбойная пластина (высота, отступ от низа, сторонность)
    p_glass = models.CharField(max_length=100, blank=True, null=True)
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    p_status = models.CharField(max_length=15, default='in_query', choices=STATUS_CHOICE)
    position_num = models.CharField(max_length=5)
    nameplate_range = models.CharField(max_length=100, blank=True, null=True)  # номерной диапзон шильдов для позиции
    p_quantity = models.IntegerField(default=1)
    p_comment = models.TextField(max_length=255, blank=True, null=True, default='')
    firm_plate = models.BooleanField(default=True)  # фирменный шильд
    mounting_plates = models.CharField(max_length=100, default=False, blank=True, null=True)  # монтажные уши: размер, кол-во

    @property
    def d_glass(self):
        if self.p_glass != '{}':
            data = ast.literal_eval(self.p_glass)
            result = '<br>'.join(f"({key[0]}x{key[1]}): {value}" for key, value in data.items())
            return result  # Убираем фигурные скобки
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
    order_items = models.ForeignKey(OrderItem, related_name='glasses', on_delete=models.CASCADE)
    height = models.IntegerField(blank=True, null=True)
    width = models.IntegerField(blank=True, null=True)
    depth = models.IntegerField(blank=True, null=True)
    quantity = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=100, blank=True, null=True, choices=GLASS_STATUS_CHOICE)
    comment = models.TextField(max_length=255, blank=True, null=True, default='')





