from django.urls import path
from . import views


urlpatterns = [
    path('calculation_table', views.calculation, name='calculation_table'),
    path('save_calculation_data', views.save_calculation_data, name='save_calculation_data'),
]
