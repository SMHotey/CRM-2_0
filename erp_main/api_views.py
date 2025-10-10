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
from .models import ChatRoom, ChatMessage, UserStatus

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


class LegalEntityViewSet(viewsets.ModelViewSet):
    queryset = LegalEntity.objects.all()
    serializer_class = LegalEntitySerializer
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


class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ChatRoom.objects.filter(participants=self.request.user, is_active=True)

    @action(detail=False, methods=['post'])
    def create_private_chat(self, request):
        user_id = request.data.get('user_id')
        try:
            target_user = User.objects.get(id=user_id)
            # Проверяем, существует ли уже приватный чат
            existing_room = ChatRoom.objects.filter(
                room_type='private',
                participants=request.user
            ).filter(participants=target_user).distinct()

            if existing_room.exists():
                room = existing_room.first()
            else:
                room = ChatRoom.objects.create(
                    name=f"Чат с {target_user.get_full_name() or target_user.username}",
                    room_type='private',
                    created_by=request.user
                )
                room.participants.add(request.user, target_user)

            serializer = self.get_serializer(room)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)


class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        room_id = self.request.query_params.get('room_id')
        if room_id:
            return ChatMessage.objects.filter(room_id=room_id).select_related('user', 'reply_to')
        return ChatMessage.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        room = serializer.validated_data['room']

        # Проверяем, что пользователь является участником комнаты
        if not room.participants.filter(id=self.request.user.id).exists():
            raise PermissionDenied("Вы не участник этого чата")

        message = serializer.save(user=self.request.user)

        # Обновляем последнее сообщение в комнате
        room.last_message = message
        room.save()

        # Отправка через WebSocket
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'chat_{room.id}',
                {
                    'type': 'chat_message',
                    'message': ChatMessageSerializer(message, context={'request': self.request}).data
                }
            )
        except Exception as e:
            print(f"WebSocket error: {e}")