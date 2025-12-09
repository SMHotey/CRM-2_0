from django.db import models

from erp_main.furniture import BaseFurnitureItem


class RAL(BaseFurnitureItem):
    ral_exterior = models.CharField(max_length=10, blank=True, null=True)
    ral_interior = models.CharField(max_length=10, blank=True, null=True)
    moire = models.BooleanField(default=False)  # муар
    priming = models.BooleanField(default=False)  # грунт
    varnish = models.BooleanField(default=False)  # лак

    def get_ral_name(self):
        # логика по преобразованию кода RAL в название цвета
        pass


class DoorCloser(BaseFurnitureItem):  # Закладные, доводчики и координаторы
    name = models.CharField(max_length=10,
                              choices=(
                                  ('plate', 'закладная'),
                                  ('kg_60', '60 кг'),
                                  ('kg_80', '80 кг'),
                                  ('kg_100', '100 кг')
                              ),
                              blank=True, null=True)
