from rest_framework import serializers
from .models import *
from django.contrib.auth.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class OrganizationSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = Organization
        fields = '__all__'


class LegalEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalEntity
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    organization_details = OrganizationSerializer(source='organization', read_only=True)
    legal_entity_details = LegalEntitySerializer(source='legal_entity', read_only=True)
    percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Invoice
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    invoice_details = InvoiceSerializer(source='invoice', read_only=True)

    # Добавляем вычисляемые поля как read-only
    doors_1_nk = serializers.IntegerField(read_only=True)
    doors_2_nk = serializers.IntegerField(read_only=True)
    hatch_nk = serializers.IntegerField(read_only=True)
    doors_1_sk = serializers.IntegerField(read_only=True)
    doors_2_sk = serializers.IntegerField(read_only=True)
    hatch_sk = serializers.IntegerField(read_only=True)
    transom = serializers.IntegerField(read_only=True)
    gate = serializers.IntegerField(read_only=True)
    gate_3000 = serializers.IntegerField(read_only=True)
    glass = serializers.IntegerField(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Order
        fields = '__all__'


class GlassInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlassInfo
        fields = '__all__'


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = '__all__'


class ShipmentSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    order_details = OrderSerializer(source='order', read_only=True)

    class Meta:
        model = Shipment
        fields = '__all__'


class ChatRoomSerializer(serializers.ModelSerializer):
    participants_details = UserSerializer(source='participants', many=True, read_only=True)
    created_by_details = UserSerializer(source='created_by', read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = '__all__'

    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'content': last_msg.content,
                'timestamp': last_msg.timestamp,
                'user': last_msg.user.username
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.messages.filter(is_read=False).exclude(user=request.user).count()
        return 0


class ChatMessageSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    reply_to_details = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['id', 'room', 'user', 'user_details', 'message_type', 'content',
                  'file', 'timestamp', 'is_read', 'reply_to', 'reply_to_details']
        read_only_fields = ['user', 'timestamp', 'is_read']

    def get_reply_to_details(self, obj):
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'content': obj.reply_to.content,
                'user': obj.reply_to.user.username
            }
        return None

    def create(self, validated_data):
        # Убедимся, что пользователь установлен
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class UserStatusSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = UserStatus
        fields = '__all__'