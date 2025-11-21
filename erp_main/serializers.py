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


class InternalLegalEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalLegalEntity
        fields = '__all__'


class InvoiceSerializer(serializers.ModelSerializer):
    organization_details = OrganizationSerializer(source='organization', read_only=True)
    internal_legal_entity_details = InternalLegalEntitySerializer(source='internal_legal_entity', read_only=True)
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
