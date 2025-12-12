from django.db import models

from erp_main.furniture import BaseFurnitureItem


class RAL(models.Model):
    ral_exterior = models.CharField(max_length=10, blank=True, null=True)
    ral_interior = models.CharField(max_length=10, blank=True, null=True)
    moire = models.BooleanField(default=False)  # муар
    priming = models.BooleanField(default=False)  # грунт
    varnish = models.BooleanField(default=False)  # лак

    def get_name(self):
        # логика по преобразованию кода RAL в название цвета
        pass


class Metal(models.Model):
    pass


class VentGrate(BaseFurnitureItem):
    height = models.IntegerField(blank=True, null=True)
    width = models.IntegerField(blank=True, null=True)
    comment = models.TextField(blank=True)


class MountingPlates(models.Model):
    height = models.IntegerField(default=50)
    width = models.IntegerField(default=200)
    comment = models.TextField(blank=True)


class DoorCloser(BaseFurnitureItem):  # Закладные, доводчики и координаторы
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



