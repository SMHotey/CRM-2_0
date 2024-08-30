from django.urls import path

from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('upload/', views.order_upload, name='order_upload'),
    path('organization/add/', views.organization_add, name='organization_add'),
    path('invoice/add/', views.invoice_add, name='invoice_add'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('index/', views.index, name='index'),

]