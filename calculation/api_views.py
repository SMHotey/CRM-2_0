from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import *
from .serializers import *


class StandardPriceViewSet(viewsets.ModelViewSet):
    queryset = StandardPrice.objects.all()
    serializer_class = StandardPriceSerializer


class PersonalPriceViewSet(viewsets.ModelViewSet):
    queryset = PersonalPrice.objects.all()
    serializer_class = PersonalPriceSerializer


class CalculationViewSet(viewsets.ModelViewSet):
    queryset = Calculation.objects.all()
    serializer_class = CalculationSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def save_calculation(self, request):
        calculation_data = request.data.get('calculation_data', [])
        project_id = request.data.get('project_id')

        with transaction.atomic():
            calculation = Calculation.objects.create(
                user=request.user,
                project_id=project_id,
                total_items=len(calculation_data)
            )

            items_to_create = []
            for item in calculation_data:
                items_to_create.append(
                    CalculationItem(
                        calculation=calculation,
                        product_name=item.get('product_name', ''),
                        door_type=item.get('door_type', ''),
                        status=item.get('status', 0),
                        price=item.get('price', 0),
                        quantity=item.get('quantity', 0),
                        total=item.get('total', 0)
                    )
                )

            CalculationItem.objects.bulk_create(items_to_create)

        return Response({
            'success': True,
            'calculation_id': calculation.id,
            'items_saved': len(items_to_create)
        })


class CalculationItemViewSet(viewsets.ModelViewSet):
    queryset = CalculationItem.objects.all()
    serializer_class = CalculationItemSerializer


class CPViewSet(viewsets.ModelViewSet):
    queryset = CP.objects.all()
    serializer_class = CPSerializer


class CPitemViewSet(viewsets.ModelViewSet):
    queryset = CPitem.objects.all()
    serializer_class = CPitemSerializer