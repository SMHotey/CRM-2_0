from django.db import models

# Create your models here.
# class StandardPrice(models.Model):
#     door_1 = models.JSONField()         # {tech: price, ei60: price, eis60: price} стандартная одностворка
#     door_2 = models.JSONField()         # {tech: price, ei60: price, eis60: price} стандартная двухстворка
#     wide_door_1 = models.JSONField()    # {tech: price, ei60: price, eis60: price} широкая одностворка
#     hatch_1 = models.JSONField()        # {tech: price, ei60: price} стандартный люк
#     wide_hatch_1 = models.JSONField()   # {tech: price, ei60: price} стандартный широкий люк
#     not_standard = models.JSONField()   # {tech: price, ei60: price, eis60: price} нестандартные двери
#     gate = models.JSONField()           # {tech: price, ei60: price, ei60_78mm: price} ворота до 3*3
#     wide_gate = models.JSONField()      # {tech: price, ei60: price, ei60_78mm: price} ворота более 3*3
#     transom = models.JSONField()        # фрамуги
#     dobor = models.JSONField()          # добор
#     door_panel = models.JSONField()     # вид панели для изделий с МДФ
#
#     lock = models.JSONField()           # замки
#     handle = models.JSONField()         # ручки
#     c_m = models.JSONField()            # цилиндровый механизм
#     door_closer = models.JSONField()    # доводчики; возможность внесения характеристик и добавление новых видов
#
#     metal = models.JSONField()          # компановки металла
#     ral = models.JSONField()            # цвет и опции
#
#     vent_grate = models.JSONField()     # вент.решетки
#     plate = models.JSONField()          # отбойная пластина
#
#     glass = models.JSONField()          # стекла плюс опции
