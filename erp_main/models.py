import os
from django.db import models
from datetime import datetime
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.timezone import now


class Organization(models.Model):
    name = models.CharField(max_length=100)
    inn = models.CharField(max_length=15)
    last_order_date = models.DateField()
    # здесь данные для формирования договора

    user = models.ManyToManyField(User, related_name='organizations')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Организации'




class Invoice(models.Model):
    ENTITY_CHOICE = (
        ('P', 'Палани'),
        ('PI', 'Палани Инжиниринг'),
        ('PD', 'Палани Дистрибуция'),
        ('GP', 'Глобал Палани'),
        ('DMM', 'Двери металл-М')
    )
    number = models.CharField(max_length=5)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    montage_amount = models.DecimalField(max_digits=10, decimal_places=2)
    legal_entity = models.CharField(max_length=50, choices=ENTITY_CHOICE)



def order_file_upload_to(instance, filename):
        # Создает уникальный путь для каждого загружаемого файла
    return os.path.join('uploads', f"{now().strftime('%Y%m%d_%H%M%S')}_{filename}")


class Order(models.Model):
    order_id = models.BigAutoField(primary_key=True)  # Внешний номер заказа
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    internal_order_number = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order_file = models.FileField(upload_to=order_file_upload_to, blank=True, null=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)



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
        ('door', 'дверь'),
        ('gate', 'ворота'),
        ('hatch', 'люк'),
        ('transom', 'фрамуга'),
        ('dobor', 'добор'),
        ('others', 'прочее')
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
    p_active_trim = models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True) # активная створка
    p_furniture = models.JSONField(blank=True, null=True) # словарь: код - количество по замку, ручке и ц/м
    p_ral = models.JSONField(blank=True, null=True) # расписать по элементам (возможные вариации, опции цвета)
    p_platband = models.JSONField(blank=True, null=True) # наличники: размер с каждой стороны
    p_door_closer = models.JSONField(blank=True, null=True) # доводчик
    p_step = models.CharField(max_length=100, blank=True, null=True) # порог
    p_metal =models.CharField(max_length=100, blank=True, null=True) # возможные компановки толщины металла изделия
    p_vent_grate = models.JSONField(blank=True, null=True) # вент. решетки (тип, размер, толщина, кол-во)
    p_plate = models.JSONField(blank=True, null=True) # отбойная пластина (высота, отступ от низа, сторонность)
    p_glass = models.CharField(max_length=255, blank=True, null=True) # тип, размер, толщина, кол-во
    p_others = models.CharField(max_length=200, blank=True, null=True) # прочее
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    status = models.CharField(max_length=15)
    position_num = models.CharField(max_length=5)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE)
    nameplate_range = models.CharField(max_length=100, blank=True, null=True)  # номерной диапзон шильдов для позиции
    p_quantity = models.IntegerField(default=1)
    p_comment = models.CharField(max_length=255, blank=True, null=True)
    firm_plate = models.BooleanField(default=True)  # фирменный шильд
    mounting_plates = models.JSONField(blank=True, null=True)  # монтажные уши: размер, кол-во







