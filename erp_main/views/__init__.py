# Auth views
from .auth import custom_login

# Base views
from .base import index, glass_info, update_glass_status, debug_users

from .orders import update_workshop

# Order views
from .orders import OrderUploadView, orders_list, order_detail, update_order_item_status

# Invoice views
from .invoices import invoice_add, invoice_detail, invoices_list

# Organization views
from .organizations import (
    OrganizationCreateView, OrganizationUpdateView,
    OrganizationListView, create_internal_legal_entity
)

# Contract views
from .contracts import create_contract

# Shipment views
from .shipments import save_shipment, shipment_detail, delete_shipment, calendar_view

__all__ = [
    'custom_login',
    'index',
    'glass_info',
    'update_glass_status',
    'update_workshop',
    'OrderUploadView',
    'orders_list',
    'order_detail',
    'update_order_item_status',
    'invoice_add',
    'invoice_detail',
    'invoices_list',
    'OrganizationCreateView',
    'OrganizationUpdateView',
    'OrganizationListView',
    'create_legal_entity',
    'create_contract',
    'save_shipment',
    'shipment_detail',
    'delete_shipment',
    'calendar_view',
    'debug_users',
]