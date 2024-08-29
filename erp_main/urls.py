from django.urls import path

from . import views
from django.contrib.auth import views as auth_views
from .views import order_upload

urlpatterns = [
    path('upload/', order_upload, name='order_upload'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('index/', views.index, name='index'),

]