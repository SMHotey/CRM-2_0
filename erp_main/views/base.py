from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Q
import json
import logging
from django.contrib.auth.models import User

from .permissions import get_user_role_from_request
from ..models import Order, OrderItem, Organization, Invoice, GlassInfo, OrderChangeHistory
from .utils import get_date_filters, apply_status_filters

logger = logging.getLogger(__name__)


def debug_users(request):
    """Временный endpoint для диагностики"""
    users = User.objects.all()
    user_data = []

    for user in users:
        user_data.append({
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        })

    return JsonResponse({
        'total_users': users.count(),
        'users': user_data,
        'debug': 'This is from debug endpoint'
    })


@login_required
def index(request):
    user_role = get_user_role_from_request(request)
    print(user_role)
    if user_role == 'production':
        return redirect('orders_list')

        # Логистика - редирект на календарь отгрузок
    elif user_role == 'logistic':
        return redirect('calendar')
    else:
        """Главная страница со статистикой"""
        start_date_obj, end_date_obj, start_date, end_date = get_date_filters(request)
        invoice_status = request.GET.get('invoice_status', '')
        order_status = request.GET.get('order_status', '')

        # Фильтруем организации по пользователю
        user_orgs = Organization.objects.filter(user=request.user)

        # Базовые запросы с фильтрацией по дате
        invoice_query = Invoice.objects.filter(
            organization__in=user_orgs,
            date__range=[start_date_obj, end_date_obj]
        )

        order_query = Order.objects.filter(
            invoice__organization__in=user_orgs,
            created_at__range=[start_date_obj, end_date_obj]
        )

        # Применяем фильтры статусов
        invoice_query = apply_status_filters(invoice_query, invoice_status, 'is_paid')

        if order_status:
            order_query = order_query.filter(items__p_status=order_status).distinct()

        # Получаем данные
        user_invoices = invoice_query.order_by('-date')
        user_orders = order_query.order_by('-created_at')

        # Подготовка контекста
        context = {
            'current_year': datetime.now().year,
            'start_date': start_date,
            'end_date': end_date,
            'invoice_status': invoice_status,
            'order_status': order_status,
            'orgs_count': user_orgs.count(),
            'orders_count': user_orders.count(),
            'invoices_count': user_invoices.count(),
            'total_invoices_amount': user_invoices.aggregate(total=Sum('amount'))['total'] or 0,
            'invoices': user_invoices,
            'orders': user_orders,
            'organizations': user_orgs,
        }

        return render(request, 'index.html', context)


def glass(request):
    """Страница информации о стеклах"""
    return render(request, 'glass_info.html')


@login_required
def glass_info(request, pk=''):
    """Информация о стеклах для заказов"""
    if pk == '':
        orders = Order.objects.all()
    else:
        orders = [get_object_or_404(Order, pk=pk)]

    return render(request, 'glass_info.html', {
        'orders': orders,
        'glass_options': GlassInfo.OPTIONS_CHOICE,
        'glass_status': GlassInfo.GLASS_STATUS_CHOICE
    })


@require_POST
def update_glass_status(request, glass_id):
    """Обновление статуса стекла"""
    glass = get_object_or_404(GlassInfo, id=glass_id)
    new_status = request.POST.get('status')
    if new_status in dict(GlassInfo.GLASS_STATUS_CHOICE).keys():
        glass.status = new_status
        glass.save()
    return redirect('glass_info')


# @require_POST
# def update_workshop(request, order_id):
#     """Обновление цеха для заказа"""
#     try:
#         data = json.loads(request.body)
#         workshop_value = data.get('workshop')
#
#         # Проверяем существование заказа
#         if not OrderItem.objects.filter(order_id=order_id).exists():
#             return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
#
#         new_status = ''
#         status_list = {'product': '"запущен"', 'stopped': '"остановлен"', 'ready': '"готов"'}
#
#         if workshop_value in ['1', '3']:
#             OrderItem.objects.filter(order_id=order_id).update(workshop=workshop_value)
#             new_status = 'product'
#         elif workshop_value == '2':
#             OrderItem.objects.filter(order_id=order_id).update(workshop=workshop_value)
#             new_status = 'stopped'
#         elif workshop_value == '4':
#             new_status = 'ready'
#         else:
#             return JsonResponse({'success': False, 'error': 'Invalid workshop value'}, status=400)
#
#     #Изменение статуса всех позиций заявки
#
#         OrderItem.objects.filter(order_id=order_id).update(p_status=new_status)
#
#         add_changes = OrderChangeHistory(
#             order_id=order_id,
#             changed_by=request.user,
#             comment='статус заказа изменен на ' + status_list[new_status]
#         )
#         add_changes.save()
#
#         return JsonResponse({'success': True})
#     except json.JSONDecodeError:
#         return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
#     except Exception as e:
#         return JsonResponse({'success': False, 'error': str(e)}, status=500)