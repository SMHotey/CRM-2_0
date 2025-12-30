from django.db import models

from erp_main.models import OrderItem


class ItemInfo(models.Model):
    """Позиция для коммерческого предложения"""
    KIND_CHOICE = (
        ('door', 'Дверь'),
        ('gate', 'Ворота'),
        ('hatch', 'Люк'),
        ('transom', 'Фрамуга'),
        ('dobor', 'Добор'),
        ('others', 'Прочее'),
        ('wickit', 'Калитка')
    )
    CONSTRUCTION_CHOICE = (
        ('SK', 'старый конструктив'),
        ('NK', 'новый конструктив')
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
    i_construction = models.CharField(max_length=10, choices=CONSTRUCTION_CHOICE, blank=True, null=True,
                                      verbose_name='конструктив изделия')


class BaseFurnitureItem(models.Model):
    """Абстрактная базовая модель для всех элементов фурнитуры"""
    STATUS_CHOICE = (
        ('in_stock', 'в наличии'),
        ('reserved', 'в резерве'),
        ('sold', 'продано'),
        ('defect', 'брак'),
    )

    name = models.CharField(max_length=50, verbose_name='Наименование')
    code = models.CharField(max_length=30, unique=True, blank=True, null=True, verbose_name='Код для счета и заявки')
    status = models.CharField(max_length=10, choices=STATUS_CHOICE, blank=True, null=True)
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    retail_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Розничная цена'
    )
    base_order_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Цена в заказе'
    )
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True, verbose_name='Закупочная цена')

    image = models.ImageField(
        upload_to='furniture/%Y/%m/%d/',  # Организация по папкам
        blank=True,
        null=True,
        verbose_name='изображение'
    )
    fireproof = models.BooleanField(default=False, blank=True, null=True)  # Противопожарность элемента фурнитуры

    # Для отдела закупки
    vendor_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='Артикул')
    supplier = models.CharField(max_length=50, blank=True, null=True, verbose_name='Поставщик')


    # Остатки
    quantity_in_stock = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество на складе'
    )
    reserved_quantity = models.PositiveIntegerField(
        default=0,
        verbose_name='Зарезервировано'
    )

    # Минимальные остатки для заказа
    min_stock = models.PositiveIntegerField(
        default=10,
        verbose_name='Минимальный запас'
    )

    def get_price(self, price_type='retail'):
        price_map = {
            'purchase': self.purchase_price,
            'retail': self.retail_price,
            'base_order': self.base_order_price,
        }
        return price_map.get(price_type, self.retail_price)

    @property
    def available_quantity(self):
        """Доступное количество (остаток - резерв)"""
        return max(0, self.quantity_in_stock - self.reserved_quantity)

    def needs_reorder(self):
        """Нужно ли заказывать?"""
        return self.available_quantity <= self.min_stock

    def can_reserve(self, quantity):
        """Можно ли зарезервировать указанное количество?"""
        return self.available_quantity >= quantity

    def get_code(self):
        if self.code:
            return self.code
        return self.name

    class Meta:
        abstract = True


class DoorLock(BaseFurnitureItem):
    security_class = models.CharField(max_length=50, default='None', blank=True, null=True)
    item_info = models.ForeignKey(
        ItemInfo,
        related_name='door_locks',
        blank=True, null=True,
        on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Дверной замок'
        verbose_name_plural = 'Дверные замки'


class DoorHandle(BaseFurnitureItem):
    color = models.CharField(max_length=30, default='стандарт', blank=True, null=True, verbose_name='Цвет')
    item_info = models.ForeignKey(
        ItemInfo,
        related_name='door_handles',
        blank=True, null=True,
        on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'Дверная ручка'
        verbose_name_plural = 'Дверные ручки'


class LockCylinder(BaseFurnitureItem):
    item_info = models.ForeignKey(
        ItemInfo,
        related_name='lock_cylinders',
        blank=True, null=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = 'Цилиндровый механизм'
        verbose_name_plural = 'Цилиндровые механизмы'


class RAL(models.Model):
    exterior = models.CharField(max_length=10, blank=True, null=True)
    interior = models.CharField(max_length=10, blank=True, null=True)
    moire = models.BooleanField(default=False)  # муар
    priming = models.BooleanField(default=False)  # грунт
    varnish = models.BooleanField(default=False)  # лак
    item_info = models.ForeignKey(
        ItemInfo,
        related_name='ral',
        blank=True, null=True,
        on_delete=models.SET_NULL)


    def get_name(self):
        # логика по преобразованию кода RAL в название цвета
        pass


class Metal(models.Model):
    TYPE_CHOICES = (
        ('m_10', '1.0'),
        ('m_12', '1.2'),
        ('m_14', '1.4'),
        ('m_15', '1.5'),
        ('m_20', '2.0'),

    )
    exterior = models.CharField(max_length=5, choices=TYPE_CHOICES, default='1.0')
    interior = models.CharField(max_length=5, choices=TYPE_CHOICES, default='1.0')
    item_info = models.ForeignKey(
        ItemInfo,
        related_name='metal',
        blank=True, null=True,
        on_delete=models.SET_NULL)
    def get_price(self):
        pass

    def __str__(self):
        return f'металл {self.exterior} - {self.interior} мм'


class VentGrate(BaseFurnitureItem):  # Вентиляционная решетка
    height = models.IntegerField(blank=True, null=True)
    width = models.IntegerField(blank=True, null=True)
    comment = models.TextField(blank=True)
    item_info = models.ForeignKey(
        ItemInfo,
        related_name='vent_grates',
        blank=True, null=True,
        on_delete=models.CASCADE
        )

    class Meta:
        verbose_name = 'вентиляционная решетка'
        verbose_name_plural = 'вентиляционные решетки'

    def __str__(self):
        kind = 'п/п' if self.fireproof else 'тех.'
        return f'{kind} вент.решетка {self.height}h x {self.width} ({self.comment})'


class MountingPlate(models.Model):  # Отбойная пластина
    height = models.IntegerField(default=50)
    width = models.IntegerField(default=200)
    comment = models.TextField(blank=True)
    item_info = models.ForeignKey(ItemInfo,
                                  related_name='mounting_plates',
                                  blank=True, null=True,
                                  on_delete=models.SET_NULL)

    class Meta:
        verbose_name = 'отбойная пластина'

    def __str__(self):
        return f'отбойная пластина {self.height}h x {self.width} ({self.comment})'


class DoorCloser(BaseFurnitureItem):
    door_weight = models.IntegerField(default=60, blank=True, null=True)
    delay_action = models.BooleanField(default=False, blank=True, null=True, verbose_name='задержка закрывания')
    hold_open = models.BooleanField(default=False, blank=True, null=True, verbose_name='фиксация открытого положения')
    frost_resistance = models.BooleanField(default=False, blank=True, null=True, verbose_name='морозоустойчивость')
    color = models.CharField(max_length=10, blank=True, null=True, verbose_name='цвет')
    dc_plate = models.BooleanField(default=True, verbose_name='закладная')

    class Meta:
        verbose_name = 'Доводчик'
        verbose_name_plural = 'Доводчики'


class ClosingCoordinator(BaseFurnitureItem):
    class Meta:
        verbose_name = 'Координатор закрывания'
        verbose_name_plural = 'Координаторы закрывания'


