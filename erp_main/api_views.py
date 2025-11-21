from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.shortcuts import get_object_or_404
from .models import *
from .serializers import *
from .filters import *
# from .models import ChatRoom, ChatMessage, UserStatus

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = OrganizationFilter
    search_fields = ['name', 'name_fl', 'inn']

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Organization.objects.all()
        return Organization.objects.filter(user=self.request.user)


class InternalLegalEntityViewSet(viewsets.ModelViewSet):
    queryset = InternalLegalEntity.objects.all()
    serializer_class = InternalLegalEntitySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'inn']


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = InvoiceFilter
    search_fields = ['number', 'organization__name']

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Invoice.objects.all()
        return Invoice.objects.filter(organization__user=self.request.user)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Order.objects.all()
        return Order.objects.filter(invoice__organization__user=self.request.user)

    @action(detail=True, methods=['post'])
    def update_workshop(self, request, pk=None):
        order = self.get_object()
        workshop = request.data.get('workshop')

        if workshop in ['1', '3']:
            order.items.update(workshop=workshop, p_status='product')
        elif workshop == '2':
            order.items.update(workshop=workshop, p_status='stopped')
        elif workshop == '4':
            order.items.update(p_status='ready')

        return Response({'status': 'workshop updated'})


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['order', 'p_status', 'workshop']

    @action(detail=False, methods=['post'])
    def bulk_update_status(self, request):
        updates = request.data.get('updates', {})

        for item_id, data in updates.items():
            try:
                item = OrderItem.objects.get(id=item_id)
                item.p_status = data.get('status', item.p_status)
                item.workshop = data.get('workshop', item.workshop)
                item.save()
            except OrderItem.DoesNotExist:
                continue

        return Response({'status': 'items updated'})


class GlassInfoViewSet(viewsets.ModelViewSet):
    queryset = GlassInfo.objects.all()
    serializer_class = GlassInfoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['order_items', 'status']


class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer


class ShipmentViewSet(viewsets.ModelViewSet):
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['workshop', 'date', 'order']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

