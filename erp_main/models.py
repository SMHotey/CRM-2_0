from django.contrib.auth.decorators import login_required
from django.db import models
from datetime import datetime
from django.contrib.auth.models import User
from django.shortcuts import redirect, render


class Organisation(models.Model):
    name = models.CharField(max_length=100)
    inn = models.CharField(max_length=15)
    # все данные для формирования договора
    city = models.CharField(max_length=25)
    employee = models.ManyToManyField('Employee', related_name='organisations', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Организации'


class Department(models.Model):
    name = models.CharField(max_length=100)
    director = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'Отделы'

    def __str__(self):
        return self.name


class Employee(models.Model):
    login = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    date_of_birth = models.DateField(null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    supervisor = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='subordinates')  # начальник сотрудника
    permissions = models.JSONField(default=list, null=True, blank=True)  # Хранение прав как список

    def has_permission(self, permission):
        return permission in self.permissions

    def __str__(self):
        return self.name


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    external_order_number = models.CharField(max_length=255, unique=True)  # Внешний номер заказа
    internal_order_number = models.CharField(max_length=255, unique=True,
                                             primary_key=True)  # Уникальный внутренний номер
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):  # Переопределение метода save класса models.Model
        if not self.internal_order_number:  # Проверка, если внутренний номер не установлен
            self.internal_order_number = self.generate_internal_order_number()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_internal_order_number():
        return datetime.now().strftime('%Y%m%d%H%M%S')


@login_required
def add_order(request):
    if request.method == 'POST':
        external_order_number = request.POST.get('external_order_number')

        if external_order_number:
            new_order = Order(
                external_order_number=external_order_number,
                user=request.user  # Присваиваем текущего пользователя
            )
            new_order.save()
            return redirect('success_url')  # Замените на URL успешного завершения

    return render(request, 'add_order.html')  # Замените на ваш шаблон


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
