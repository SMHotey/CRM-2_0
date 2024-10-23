import os
import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from datetime import datetime
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.timezone import now


def validate_numeric_only(value):
    if not re.match(r'^\d{6,}$', value) and value is not None:
        raise ValidationError('Поле должно содержать только цифры и минимум 6 символов.')


class Organization(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True)
    inn = models.CharField(max_length=15, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    name_fl = models.CharField(max_length=15, blank=True, null=True)
    user = models.ForeignKey(User, related_name='organizations', on_delete=models.CASCADE)

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



class Invoice(models.Model):
    ENTITY_CHOICE = (
        ('P', 'Палани'),
        ('PI', 'Палани Инжиниринг'),
        ('PD', 'Палани Дистрибуция'),
        ('GP', 'Глобал Палани'),
        ('DMM', 'Двери металл-М'),
        ('FL', 'Прочее')
    )
    number = models.CharField(max_length=5, blank=True, null=True)
    organization = models.ForeignKey(Organization, related_name='organization', on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    amount = models.IntegerField(default=0)
    payed_amount = models.IntegerField(default=0)
    shipping_amount = models.IntegerField(default=0)
    montage_amount = models.IntegerField(default=0)
    legal_entity = models.CharField(max_length=50, choices=ENTITY_CHOICE)

    def __str__(self):
        return f'Счет № {self.number}'


#def order_file_upload_to(instance, filename):
#        # Создает уникальный путь для каждого загружаемого файла
#    return os.path.join('uploads', f"{now().strftime('%Y%m%d_%H%M%S')}_{filename}")


class Order(models.Model):
    internal_order_number = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order_file = models.FileField(upload_to='uploads/')
    invoice = models.ForeignKey(Invoice, blank=True, null=True, on_delete=models.CASCADE)
    due_date = models.DateField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)

    def get_items_filtered(self):
        return self.items.exclude(status__in=['changed', 'canceled'])

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
        return self.get_items_filtered().filter(Q(p_glass__isnull=False) & ~Q(p_glass={})).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def quantity(self):
        return self.get_items_filtered().filter(p_quantity__gt=0).aggregate(total=Sum('p_quantity'))['total'] or 0

    @property
    def status(self): # раскидываем позиции по статусам
        in_query = self.get_items_filtered().filter(status='in_query').aggregate(total=Sum('p_quantity'))['total'] or 0
        product = self.get_items_filtered().filter(status='product').aggregate(total=Sum('p_quantity'))['total'] or 0
        if in_query > product:
            return in_query


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
    p_glass = models.CharField(max_length=255, blank=True, null=True) # тип, размер, толщина, кол-во
    p_others = models.CharField(max_length=200, blank=True, null=True) # прочее
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    status = models.CharField(max_length=15, default='in_query')
    position_num = models.CharField(max_length=5)
    nameplate_range = models.CharField(max_length=100, blank=True, null=True)  # номерной диапзон шильдов для позиции
    p_quantity = models.IntegerField(default=1)
    p_comment = models.CharField(max_length=255, blank=True, null=True)
    firm_plate = models.BooleanField(default=True)  # фирменный шильд
    mounting_plates = models.CharField(max_length=100, default=False, blank=True, null=True)  # монтажные уши: размер, кол-во

    @property
    def glass(self):
        if self.p_glass != '{}':
            return self.p_glass.translate(str.maketrans("", "", "{}()")).replace(",", "х") + "<br>"
        else:
            return f'глухая'






