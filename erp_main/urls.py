from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import (
    custom_login, glass_info, update_glass_status,
    OrderUploadView, orders_list, order_detail, update_order_item_status,
    invoice_add, invoice_detail, invoices_list,
    OrganizationCreateView, OrganizationUpdateView, OrganizationListView, OrganizationDetailView,
    create_legal_entity, create_contract,
    save_shipment, shipment_detail, delete_shipment, calendar_view, debug_users, passport
)
from .views import certificates
from .views.orders import update_workshop
from .views.base import index
urlpatterns = [
    # Auth
    path('login/', custom_login, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    # Main
    path('', index, name='index'),

    # Orders
    path('orders/upload/', OrderUploadView.as_view(), name='order_upload'),
    path('orders/upload/<int:order_id>/', OrderUploadView.as_view(), name='order_upload'),
    path('orders/', orders_list, name='orders_list'),
    path('orders/<int:order_id>/', order_detail, name='order_detail'),
    path('orders/update_status/', update_order_item_status, name='update_order_item_status'),

    # Invoices
    path('invoices/add/', invoice_add, name='invoice_add'),
    path('invoices/<int:pk>/', invoice_detail, name='invoice_detail'),
    path('invoices/', invoices_list, name='invoices_list'),

    # Organizations
    path('organizations/add/', OrganizationCreateView.as_view(), name='organization_add'),
    path('organizations/<int:pk>/edit/', OrganizationUpdateView.as_view(), name='organization_edit'),
    path('organizations/<int:pk>/', OrganizationDetailView.as_view(), name='organization_detail'),
    path('organizations/', OrganizationListView.as_view(), name='organization_list'),
    path('legal_entity/create/', create_legal_entity, name='create_legal_entity'),
    path('organizations/<int:pk>/create_contract/', create_contract, name='create_contract'),

    # Glass

    path('glass/<int:pk>/', glass_info, name='glass_info'),
    path('glass/', glass_info, name='glass_info'),
    path('glass/update/<int:glass_id>/', update_glass_status, name='update_glass_status'),

    # Workshop
    path('workshop/update/<int:order_id>/', update_workshop, name='update_workshop'),

    # Shipments
    path('shipments/save/', save_shipment, name='save_shipment'),
    path('shipments/<str:workshop>/<str:date>/', shipment_detail, name='shipment_detail'),
    path('shipments/delete/<int:shipment_id>/', delete_shipment, name='delete_shipment'),
    path('calendar/', calendar_view, name='calendar'),

# Certificate URLs
    path('certificates/', certificates.CertificateListView.as_view(), name='certificate_list'),
    path('certificates/create/', certificates.CertificateCreateView.as_view(), name='certificate_create'),
    path('certificates/<int:pk>/', certificates.CertificateDetailView.as_view(), name='certificate_detail'),
    path('certificates/<int:pk>/edit/', certificates.CertificateUpdateView.as_view(), name='certificate_edit'),
    path('certificates/<int:pk>/delete/', certificates.CertificateDeleteView.as_view(), name='certificate_delete'),

# Nameplate URLs
    path('get-certificates/', certificates.get_certificates, name='get_certificates'),
    path('get-nameplates/', certificates.get_nameplates, name='get_nameplates'),
    path('create-nameplate/', certificates.create_nameplate, name='create_nameplate'),
    path('get-nameplate-data/', certificates.get_nameplate_data, name='get_nameplate_data'),
    path('update-nameplate/', certificates.update_nameplate, name='update_nameplate'),
    path('delete-nameplate/', certificates.delete_nameplate, name='delete_nameplate'),

#Passport
    path('check-nameplates/', passport.check_nameplates, name='check_nameplates'),
    path('generate-passports/', passport.generate_passports, name='generate_passports'),
    # Chat
    # path('chat/', chat_view, name='chat'),
    # path('chat/users/', get_available_users, name='get_available_users'),

    # Debug
    path('debug/users/', debug_users, name='debug_users'),
]