from functools import wraps
from django.contrib import messages
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.shortcuts import redirect


def get_user_role_from_request(request):
    """Получаем роль пользователя из request (для function-based views)"""
    user = request.user
    if user.is_superuser:
        return 'admin'

    group_names = user.groups.values_list('name', flat=True)
    role_priority = ['admin', 'director', 'production', 'logistic', 'manager']

    for role in role_priority:
        if role in group_names:
            return role

    return 'user'


def role_required(required_roles):
    """Декоратор для проверки прав в function-based views"""

    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            user_role = get_user_role_from_request(request)
            if user_role not in required_roles:
                return JsonResponse({'error': 'Permission denied'}, status=403)
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


def has_permission_for_action(user_role, current_status, current_workshop, action):
    """Проверяем права доступа для действия согласно бизнес-логике"""

    # Админы и директоры имеют все права
    if user_role in ['admin', 'director']:
        return True

    # Логисты могут только отгружать готовые заказы
    if user_role == 'logistic':
        return action == 'ship' and current_status == 'готов'

    # Менеджеры
    if user_role == 'manager':
        if current_status == 'в очереди':
            return action == 'cancel'
        elif current_status == 'запущен':
            return action == 'stop'
        elif current_status == 'остановлен':
            return action in ['cancel', 'to_queue']
        elif current_status == 'готов':
            return action == 'ship'
        return False

    # Производство
    if user_role == 'production':
        if current_status == 'в очереди':
            return action in ['start_1', 'start_3', 'cancel']
        elif current_status == 'запущен':
            if current_workshop == '1':
                return action in ['stop', 'switch_3', 'ready']
            elif current_workshop == '3':
                return action in ['stop', 'switch_1', 'ready']
        elif current_status == 'остановлен':
            return action in ['start_1', 'start_3', 'cancel', 'to_queue']
        elif current_status == 'готов':
            return action in ['start_1', 'start_3']
        return False

    return False


def can_view_order(user, user_role, order):
    """Проверяет, может ли пользователь просматривать заказ"""
    if user_role in ['admin', 'director', 'production', 'logistic']:
        return True
    # Менеджеры видят заказы своих клиентов
    if user_role == 'manager':
        try:
            return order.invoice.organization.user == user
        except (AttributeError, ObjectDoesNotExist):
            return False

    # По умолчанию - нет доступа
    return False


def can_edit_order_detail(user, user_role, order):
    """Проверяет, может ли пользователь редактировать заказ"""
    # Только админы, директоры и менеджеры могут редактировать
    if user_role in ['admin', 'director', 'manager']:
        return True
    return False


def can_add_invoice(user, user_role):
    if user_role in ['admin', 'director', 'manager']:
        return True
    else:
        return False




def can_modify_order_item(user, user_role, order_item):
    """Проверяет, может ли пользователь изменять позицию заказа"""
    if user_role in ['admin', 'director']:
        return True
    if user_role in ['manager', 'production', 'logistic']:
        return order_item.order.invoice.organization.user == user
    return False


def ajax_permission_required(permission_check_func, error_message="Недостаточно прав"):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not permission_check_func(request):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'show_modal': True,
                        'modal_title': 'Ошибка доступа',
                        'modal_message': error_message
                    }, status=403)
                else:
                    messages.error(request, error_message)
                    return redirect('index')
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
