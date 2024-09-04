from django.urls import path

from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('upload/', views.order_upload, name='order_upload'),
    path('orders_list/', views.orders_list, name='orders_list'),
    path('organization/add/', views.organization_add, name='organization_add'),
    path('invoice/add/', views.invoice_add, name='invoice_add'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('organization_list/', views.organization_list, name='organization_list'),
    path('index/', views.index, name='index'),
    path('password_reset/',
         auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'),
         name='password_reset'),
    path('register/', views.register, name='register'),

]