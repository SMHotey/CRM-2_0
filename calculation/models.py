from django.contrib.auth.models import User
from django.db import models
from erp_main.models import Organization, OrderItem


class StandardPrice(models.Model):
    door_1 = models.JSONField()         # {tech: price, ei60: price, eis60: price} стандартная одностворка
    door_2 = models.JSONField()         # {tech: price, ei60: price, eis60: price} стандартная двухстворка
    wide_door_1 = models.JSONField()    # {tech: price, ei60: price, eis60: price} широкая одностворка
    hatch_1 = models.JSONField()        # {tech: price, ei60: price} стандартный люк
    wide_hatch_1 = models.JSONField()   # {tech: price, ei60: price} стандартный широкий люк
    not_standard = models.JSONField()   # {tech: price, ei60: price, eis60: price} нестандартные двери
    gate = models.JSONField()           # {tech: price, ei60: price, ei60_78mm: price} ворота до 3*3
    wide_gate = models.JSONField()      # {tech: price, ei60: price, ei60_78mm: price} ворота более 3*3
    transom = models.JSONField()        # фрамуги
    dobor = models.JSONField()          # добор
    door_panel = models.JSONField()     # вид панели для изделий с МДФ

    lock = models.JSONField()           # замки
    handle = models.JSONField()         # ручки
    c_m = models.JSONField()            # цилиндровый механизм
    door_closer = models.JSONField()    # доводчики; возможность внесения характеристик и добавление новых видов

    metal = models.JSONField()          # компановки металла
    ral = models.JSONField()            # цвет и опции

    vent_grate = models.JSONField()     # вент.решетки
    plate = models.JSONField()          # отбойная пластина

    glass = models.JSONField()          # стекла плюс опции


class PersonalPrice(StandardPrice):
    client = models.ForeignKey(Organization, related_name='price', on_delete=models.CASCADE)
    default_margin = models.IntegerField(default=0)


class CPitem(OrderItem):
    personal_price = models.ForeignKey(PersonalPrice,related_name='cp', on_delete=models.CASCADE)


class CP(OrderItem):
    date = models.DateField()


class Calculation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    total_items = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Расчет #{self.id} от {self.created_at.strftime('%d.%m.%Y')}"


class CalculationItem(models.Model):
    calculation = models.ForeignKey(
        Calculation,
        related_name='items',
        on_delete=models.CASCADE
    )
    product_name = models.CharField(max_length=255)

    DOOR_TYPES = (
        ('internal', 'Межкомнатная'),
        ('external', 'Входная'),
        ('fire', 'Противопожарная'),
        ('armored', 'Бронированная'),
    )
    door_type = models.CharField(
        max_length=20,
        choices=DOOR_TYPES,
        default='internal'
    )

    STATUS_CHOICES = (
        (0, 'Черновик'),
        (1, 'На производстве'),
        (2, 'Готов к отгрузке'),
        (3, 'Отгружен'),
        (4, 'Отменен'),
    )
    status = models.IntegerField(choices=STATUS_CHOICES, default=0)

    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.IntegerField()
    total = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product_name} - {self.quantity} шт."