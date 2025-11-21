from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import *

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet)
router.register(r'legal-entities', InternalLegalEntityViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'order-items', OrderItemViewSet)
router.register(r'glass-info', GlassInfoViewSet)
router.register(r'contracts', ContractViewSet)
router.register(r'shipments', ShipmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]