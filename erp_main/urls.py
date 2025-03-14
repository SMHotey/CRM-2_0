from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views
from django.contrib.auth import views as auth_views

from .views import OrderUploadView, create_legal_entity, create_contract, glass_info, \
    update_glass_status, OrganizationCreateView, OrganizationListView, OrganizationDetailView, OrganizationUpdateView, \
    update_workshop, index, custom_login

urlpatterns = [
    path('update-order-item-status/', views.update_order_item_status, name='update_order_item_status'),
    path('update_workshop/<int:order_id>/', update_workshop, name='update_workshop'),
    path('order/upload/<int:order_id>/', OrderUploadView.as_view(), name='order_upload'),
    path('order/upload/', OrderUploadView.as_view(), name='order_upload'),
    path('orders_list/', views.orders_list, name='orders_list'),
    path('organization/<int:pk>/edit/', OrganizationUpdateView.as_view(), name='organization_edit'),
    path('organization/add/', OrganizationCreateView.as_view(), name='organization_add'),
    path('invoice/add/', views.invoice_add, name='invoice_add'),
    path('login/', custom_login, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('organization/<int:pk>/', OrganizationDetailView.as_view(), name='organization_detail'),
    path('invoice/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices_list/', views.invoices_list, name='invoices_list'),
    path('organizations/', OrganizationListView.as_view(), name='organization_list'),
    path('index/', index, name='index'),
    path('legal-entity/create/', create_legal_entity, name='create_legal_entity'),
    path('organization/contract/<int:pk>', create_contract, name='create_contract'),
    path('glass_info/<int:pk>/', glass_info, name='glass_info'),
    path('glass_info/', glass_info, name='glass_info'),
    path('update_glass_status/<int:glass_id>/', update_glass_status, name='update_glass_status'),
    path('calendar/', views.calendar_view, name='calendar'),
    path('shipment/<int:workshop>/<str:date>/', views.shipment_detail, name='shipment_detail'),
    path('save_shipment/', views.save_shipment, name='save_shipment'),
]

