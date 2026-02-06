from django.db import models


class BaseProduct(models.Model):
    # KIND_CHOICE = (
    #     ('door', 'Дверь'),
    #     ('gate', 'Ворота'),
    #     ('hatch', 'Люк'),
    #     ('transom', 'Фрамуга'),
    # )
    # c_type = models.CharField(max_length=10, blank=True, null=True, choices=TYPE_CHOICE, verbose_name='тип изделия')
    c_width = models.IntegerField(default=0, verbose_name='ширина изделия')
    c_height = models.IntegerField(default=0, verbose_name='высота изделия')

    def get_options(self):
        pass

    class Meta:
        abstract = True


class Color(models.Model):
    ral_exterior = models.CharField(max_length=10, default='7035')
    ral_interior = models.CharField(max_length=10, default='7035')
    moire = models.BooleanField(default=False)  # муар
    varnish = models.BooleanField(default=False)  # лак
    primer = models.BooleanField(default=False)  # грунтовка

class Door(BaseProduct):
    TYPE_CHOICE = (
        ('tech', 'тех.'),
        ('ei-60', 'EI-60'),
        ('eis-60', 'EIS-60'),
        ('eiws-60', 'EIWS-60'),
        ('flat', 'квартир.'),
        ('one_layer', 'однолист.'),
        ('None', '')
    )
