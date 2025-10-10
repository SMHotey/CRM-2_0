from rest_framework import serializers
from .models import *

class StandardPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StandardPrice
        fields = '__all__'

class PersonalPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalPrice
        fields = '__all__'

class CalculationItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalculationItem
        fields = '__all__'

class CalculationSerializer(serializers.ModelSerializer):
    items = CalculationItemSerializer(many=True, read_only=True)

    class Meta:
        model = Calculation
        fields = '__all__'

class CPSerializer(serializers.ModelSerializer):
    class Meta:
        model = CP
        fields = '__all__'

class CPitemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CPitem
        fields = '__all__'