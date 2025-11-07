from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django.db.models import Count
from datetime import datetime, time, timedelta
import calendar

from ..models import Shipment, Order, OrderItem


@csrf_exempt
@require_http_methods(["POST"])
def save_shipment(request):
    """Сохранение отгрузки"""
    try:
        data = request.POST
        shipment_id = data.get('shipment_id')

        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Требуется авторизация'}, status=403)

        if shipment_id:
            shipment = get_object_or_404(Shipment, id=shipment_id)
            if shipment.user != request.user and not request.user.is_superuser:
                return JsonResponse({'status': 'error', 'message': 'Нет прав на редактирование'}, status=403)
        else:
            shipment = Shipment(
                user=request.user,
                date=data.get('date'),
                time=data.get('time'),
                workshop=data.get('workshop')
            )

        # Обновляем основную информацию
        if data.get('order'):
            try:
                shipment.order = Order.objects.get(pk=data.get('order'))
            except Order.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Указанный заказ не существует'}, status=400)

        # Обновляем JSON-поля
        order_items = shipment.order_items or {}
        order_items['type'] = data.get('order_type', '')
        shipment.order_items = order_items

        car_info = shipment.car_info or {}
        car_info.update({
            'brand': data.get('car_brand', ''),
            'number': data.get('car_number', '')
        })
        shipment.car_info = car_info

        driver_info = shipment.driver_info or {}
        driver_info.update({
            'comments': data.get('comments', ''),
            'shipment_mark': data.get('shipment_mark', '')
        })
        shipment.driver_info = driver_info

        shipment.address = data.get('address', '')
        shipment.save()

        return JsonResponse({
            'status': 'success',
            'shipment_id': shipment.id,
            'order': shipment.order.pk if shipment.order else '',
            'order_type': shipment.order_items.get('type', ''),
            'car_brand': shipment.car_info.get('brand', ''),
            'car_number': shipment.car_info.get('number', ''),
            'address': shipment.address,
            'comments': shipment.driver_info.get('comments', ''),
            'shipment_mark': shipment.driver_info.get('shipment_mark', '')
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_http_methods(["GET"])
def shipment_detail(request, workshop, date):
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return HttpResponseBadRequest("Неверный формат даты")

    shipments = Shipment.objects.filter(workshop=workshop, date=date_obj).order_by('time')

    shipments_dict = {shipment.time: shipment for shipment in shipments}

    times = [time(hour, minute) for hour in range(9, 18) for minute in [0, 30]]

    filtered_items = OrderItem.objects.filter(p_status__in=['product', 'ready'])
    orders = Order.objects.filter(items__in=filtered_items).distinct()
    orders_list = [{'pk': order.pk, 'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S')} for order in orders]

    context = {
        'workshop': workshop,
        'date': date_obj,
        'shipments': shipments_dict,
        'times': times,
        'orders': orders_list,
    }
    return render(request, 'shipment_detail.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def delete_shipment(request, shipment_id):
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Требуется авторизация'}, status=403)

        shipment = get_object_or_404(Shipment, id=shipment_id)

        if shipment.user != request.user and not request.user.is_superuser:
            return JsonResponse({'status': 'error', 'message': 'Нет прав на удаление'}, status=403)

        shipment.delete()

        return JsonResponse({
            'status': 'success',
            'message': 'Отгрузка успешно удалена'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def calendar_view(request):
    """Улучшенное представление календаря отгрузок"""
    today = timezone.now().date()

    # Получаем год и месяц из параметров или используем текущие
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
    except (ValueError, TypeError):
        year = today.year
        month = today.month

    # Ограничиваем диапазон месяцев для предотвращения ошибок
    if month < 1:
        month = 1
        year -= 1
    elif month > 12:
        month = 12
        year += 1

    current_date = datetime(year, month, 1).date()

    # Расчет предыдущего и следующего месяца
    if month == 1:
        prev_month = datetime(year - 1, 12, 1).date()
    else:
        prev_month = datetime(year, month - 1, 1).date()

    if month == 12:
        next_month = datetime(year + 1, 1, 1).date()
    else:
        next_month = datetime(year, month + 1, 1).date()

    # Генерация календаря
    cal = calendar.Calendar(firstweekday=0)  # Понедельник - первый день недели
    month_days = cal.monthdayscalendar(year, month)

    # Получаем статистику по отгрузкам
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)

    # Статистика по цехам
    shipments_workshop1 = Shipment.objects.filter(
        workshop=1,
        date__range=[start_date, end_date]
    ).count()

    shipments_workshop3 = Shipment.objects.filter(
        workshop=3,
        date__range=[start_date, end_date]
    ).count()

    total_shipments = shipments_workshop1 + shipments_workshop3

    # Получаем отгрузки по дням для календаря
    shipments_by_date_workshop1 = Shipment.objects.filter(
        workshop=1,
        date__range=[start_date, end_date]
    ).values('date').annotate(count=Count('id'))

    shipments_by_date_workshop3 = Shipment.objects.filter(
        workshop=3,
        date__range=[start_date, end_date]
    ).values('date').annotate(count=Count('id'))

    # Создаем словари для быстрого доступа к количеству отгрузок
    shipments_workshop1_dict = {s['date'].strftime('%Y-%m-%d'): s['count'] for s in shipments_by_date_workshop1}
    shipments_workshop3_dict = {s['date'].strftime('%Y-%m-%d'): s['count'] for s in shipments_by_date_workshop3}

    # Формируем данные для календаря
    calendar_weeks = []
    for week in month_days:
        calendar_week = []
        for day in week:
            if day == 0:  # Пустой день (из предыдущего/следующего месяца)
                calendar_week.append({
                    'day': None,
                    'date': None,
                    'shipments_count_workshop1': 0,
                    'shipments_count_workshop3': 0,
                    'is_weekend': False,
                    'has_shipments': False
                })
            else:
                date_obj = datetime(year, month, day).date()
                date_str = date_obj.strftime('%Y-%m-%d')
                is_weekend = date_obj.weekday() >= 5  # Суббота и воскресенье

                # Количество отгрузок по цехам
                count_workshop1 = shipments_workshop1_dict.get(date_str, 0)
                count_workshop3 = shipments_workshop3_dict.get(date_str, 0)
                has_shipments = count_workshop1 > 0 or count_workshop3 > 0

                day_data = {
                    'day': day,
                    'date': date_str,
                    'is_weekend': is_weekend,
                    'shipments_count_workshop1': count_workshop1,
                    'shipments_count_workshop3': count_workshop3,
                    'has_shipments': has_shipments,
                    'is_today': date_obj == today
                }

                calendar_week.append(day_data)
        calendar_weeks.append(calendar_week)

    # Подсчет рабочих дней (понедельник-пятница)
    work_days_count = sum(1 for week in month_days for day in week
                          if day != 0 and datetime(year, month, day).date().weekday() < 5)

    # Русские названия месяцев
    month_names = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
        5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
        9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }

    context = {
        'current_date': current_date,
        'prev_month': prev_month,
        'next_month': next_month,
        'prev_month_name': month_names[prev_month.month],
        'next_month_name': month_names[next_month.month],
        'calendar_weeks': calendar_weeks,
        'work_days_count': work_days_count,
        'total_shipments': total_shipments,
        'workshop1_shipments': shipments_workshop1,
        'workshop3_shipments': shipments_workshop3,
        'upcoming_shipments': Shipment.objects.filter(date__gte=today).count(),
    }

    return render(request, 'calendar.html', context)