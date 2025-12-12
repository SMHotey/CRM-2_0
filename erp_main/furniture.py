from django.db import models


class BaseFurnitureItem(models.Model):
    """Абстрактная базовая модель для всех элементов фурнитуры"""
    name = models.CharField(max_length=50, verbose_name='Наименование')
    code = models.CharField(max_length=30, unique=True, blank=True, null=True, verbose_name='Код для счета и заявки')
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
    image = models.ImageField(
        upload_to='furniture/%Y/%m/%d/',  # Организация по папкам
        blank=True,  # Сделать необязательным?
        null=True,
        verbose_name='изображение'
    )
    fireproof = models.BooleanField(default=False, blank=True, null=True)  # Противопожарность элемента фурнитуры

    # Для отдела закупки
    vendor_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='Артикул')
    supplier = models.CharField(max_length=50, blank=True, null=True, verbose_name='Поставщик')
    purchase_price = models.IntegerField(blank=True, null=True, verbose_name='Закупочная цена')

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

    def can_consume(self, quantity):
        """Можно ли списать указанное количество?"""
        return self.available_quantity >= quantity

    def get_code(self):
        if self.code:
            return self.code
        return self.name

    def _get_base_str(self):
        """Базовое строковое представление"""
        if self.code:
            return f"{self.name} [{self.code}]"
        return self.name

    def _get_additional_str_info(self):
        """Метод для переопределения в наследниках"""
        return ""

    def __str__(self):
        base = self._get_base_str()
        additional = self._get_additional_str_info()
        if additional:
            return f"{base} - {additional}"
        return base

    class Meta:
        abstract = True


class DoorLock(BaseFurnitureItem):
    security_class = models.CharField( max_length=50, default='None', blank=True, null=True)

    class Meta:
        verbose_name = 'Дверной замок'
        verbose_name_plural = 'Дверные замки'


class DoorHandle(BaseFurnitureItem):
    color = models.CharField(max_length=30, default='стандарт', blank=True, null=True, verbose_name='Цвет')
    anti_fire = models.BooleanField(default='False')
    class Meta:
        verbose_name = 'Дверная ручка'
        verbose_name_plural = 'Дверные ручки'


class LockCylinder(BaseFurnitureItem):
    class Meta:
        verbose_name = 'Цилиндровый механизм'
        verbose_name_plural = 'Цилиндровые механизмы'


class FurnitureKit(models.Model):
    """Комплект фурнитуры - связан с OrderItem через OneToOne"""
    name = models.CharField(max_length=100, verbose_name='Наименование комплекта', blank=True)
    description = models.TextField(blank=True, null=True, verbose_name='Описание')

    # Связь с замками и ручками через ManyToMany
    locks = models.ManyToManyField(
        DoorLock,
        through='FurnitureKitLock',
        related_name='furniture_kits',
        verbose_name='Замки',
        blank=True
    )
    handles = models.ManyToManyField(
        DoorHandle,
        through='FurnitureKitHandle',
        related_name='furniture_kits',
        verbose_name='Ручки',
        blank=True
    )
    cylinders = models.ManyToManyField(
        LockCylinder,
        through='FurnitureKitCylinder',
        related_name='furniture_kits',
        verbose_name='ц/м',
        blank=True
    )

    # Связь с позицией - один комплект на одну позицию
    order_item = models.OneToOneField(
        'OrderItem',
        on_delete=models.CASCADE,
        related_name='furniture_kit',
        verbose_name='Позиция'
    )

    class Meta:
        verbose_name = 'Комплект фурнитуры'
        verbose_name_plural = 'Комплекты фурнитуры'

    def __str__(self):
        if self.name:
            return self.name
        return f'Комплект фурнитуры для {self.order_item.id}'

    def save(self, *args, **kwargs):
        # Автоматически генерируем имя, если оно не указано
        if not self.name and self.order_item:
            self.name = f'Комплект для {self.order_item}'
        super().save(*args, **kwargs)


class FurnitureKitLock(models.Model):
    """Связь комплекта фурнитуры с замком"""
    furniture_kit = models.ForeignKey(FurnitureKit, on_delete=models.CASCADE)
    door_lock = models.ForeignKey(DoorLock, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')

    class Meta:
        unique_together = ('furniture_kit', 'door_lock')
        verbose_name = 'Замок в комплекте'
        verbose_name_plural = 'Замки в комплекте'

    def __str__(self):
        return f"{self.door_lock.name} × {self.quantity}"


class FurnitureKitHandle(models.Model):
    """Связь комплекта фурнитуры с ручкой"""
    furniture_kit = models.ForeignKey(FurnitureKit, on_delete=models.CASCADE)
    door_handle = models.ForeignKey(DoorHandle, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')

    class Meta:
        unique_together = ('furniture_kit', 'door_handle')
        verbose_name = 'Ручка в комплекте'
        verbose_name_plural = 'Ручки в комплекте'

    def __str__(self):
        return f"{self.door_handle.name} × {self.quantity}"


class FurnitureKitCylinder(models.Model):
    """Связь комплекта фурнитуры с ц/м"""
    furniture_kit = models.ForeignKey(FurnitureKit, on_delete=models.CASCADE)
    lock_cylinder = models.ForeignKey(LockCylinder, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')

    class Meta:
        unique_together = ('furniture_kit', 'lock_cylinder')
        verbose_name = 'Ц/м в комплекте'
        verbose_name_plural = 'Ц/м в комплекте'

    def __str__(self):
        return f"{self.lock_cylinder.name} × {self.quantity}"