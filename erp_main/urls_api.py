from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import *

router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet)
router.register(r'legal-entities', LegalEntityViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'order-items', OrderItemViewSet)
router.register(r'glass-info', GlassInfoViewSet)
router.register(r'contracts', ContractViewSet)
router.register(r'shipments', ShipmentViewSet)
router.register(r'chat/rooms', ChatRoomViewSet, basename='chatroom')
router.register(r'chat/messages', ChatMessageViewSet, basename='chatmessage')
#router.register(r'chat/status', UserStatusViewSet, basename='userstatus')

urlpatterns = [
    path('', include(router.urls)),
]