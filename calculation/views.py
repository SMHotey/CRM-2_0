from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404, render
from django.views.generic import CreateView
from .models import Calculation, CalculationItem
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


def calculation(request):
    context = {'name': 'Sergey'}
    dropdown_data = {
        'door_types': {'door': 'Дверь', 'door_2': 'Дверь 2-ств.'},
        'door_kinds': {'tech': 'тех.', 'ei-60': 'EI-60'},
        'glazing_types': {'none': 'нет', 'single': 'однокамерное'},
        'glazing_options': {'none': 'нет', 'A1_1': 'А1-1', 'A1_2': 'A1-2', 'A2_1': 'A2-2'},
        'metal_types': {'1.2-1.4': '1.2-1.4', '1.4-1.4': '1.4-1.4'},
        'vent_types': {'none': 'нет', 'tech': 'тех.'},
        'ral_colors': {'9001': 'RAL 9001', '9010': 'RAL 9010'},
        'hardware_handles': {'handle_type1': 'Ручка тип 1'},
        'hardware_locks': {'lock_type1': 'Замок тип 1'},
        'closers': {'closer_type1': 'Доводчик тип 1'},
        'cylinders': {'cylinder_type1': 'Цилиндр тип 1'}
    }
    context['dropdown_data'] = dropdown_data
    return render(request, 'calculation_table.html', context)


@require_POST
@csrf_exempt
def save_calculation_data(request):
    try:
        # Распарсим JSON данные
        data = json.loads(request.body)
        calculation_data = data.get('calculation_data', [])
        project_id = data.get('project_id')

        # Проверка данных
        if not calculation_data:
            return JsonResponse({
                'success': False,
                'error': 'Пустые данные'
            }, status=400)

        # Создаем новый расчет
        calculation = Calculation.objects.create(
            user=request.user,
            project_id=project_id,
            total_items=len(calculation_data)
        )

        # Сохраняем элементы расчета
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

        return JsonResponse({
            'success': True,
            'calculation_id': calculation.id,
            'items_saved': len(items_to_create),
            'created_at': calculation.created_at.strftime("%Y-%m-%d %H:%M")
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Невалидный JSON'
        }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Ошибка сервера: {str(e)}'
        }, status=500)
