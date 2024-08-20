from django.db import models
from datetime import datetime
from django.contrib.auth.models import User


class Organization(models.Model):
    name = models.CharField(max_length=100)
    inn = models.CharField(max_length=15)
    last_order_date = models.DateField()
    # здесь данные для формирования договора

    employee = models.ManyToManyField('Employee', related_name='organisations')

    class Meta:
        verbose_name_plural = 'Организации'


class Employee(models.Model):
    login = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
#    date_of_birth = models.DateField(null=True, blank=True)
    permissions = models.JSONField(default=list, null=True, blank=True)  # Хранение прав как список

    def has_permission(self, permission):
        return permission in self.permissions

    def __str__(self):
        return f'{self.name}'


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


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_id = models.BigAutoField(primary_key=True)  # Внешний номер заказа
    internal_order_number = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
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
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    position_num = models.CharField(max_length=5)
    status = models.CharField(max_length=15)
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # ПОМЕНЯТЬ УСЛОВИЕ ПРИ УДАЛЕНИИ МЕНЕДЖЕРА ИЗ БАЗЫ!!!
##        unique_together = ('order', 'product_name')  # Уникальность на уровне заказа и товара
