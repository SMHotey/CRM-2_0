from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views
from django.contrib.auth import views as auth_views

from .views import OrderUploadView, edit_organization, create_legal_entity, create_contract, glass_info

urlpatterns = [
    path('update-order-item-status/', views.update_order_item_status, name='update_order_item_status'),
    path('order/upload/', OrderUploadView.as_view(), name='order_upload'),
    path('orders_list/', views.orders_list, name='orders_list'),
    path('organization/add/', views.organization_add, name='organization_add'),
    path('invoice/add/', views.invoice_add, name='invoice_add'),
    path('login/', auth_views.LoginView.as_view(next_page='index'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('organization/<int:pk>/', views.organization_detail, name='organization_detail'),
    path('invoice/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices_list/', views.invoices_list, name='invoices_list'),
    path('organization_list/', views.organization_list, name='organization_list'),
    path('index/', views.index, name='index'),
    path('password_reset/',
         auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'),
         name='password_reset'),
    path('register/', views.register, name='register'),
    path('organization/edit/<int:pk>/', edit_organization, name='edit_organization'),
    path('legal-entity/create/', create_legal_entity, name='create_legal_entity'),
    path('organization/contract/<int:pk>', create_contract, name='create_contract'),
    path('glass_info/', glass_info, name='glass_info'),
]

