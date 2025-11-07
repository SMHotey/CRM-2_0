from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone


def get_date_filters(request):
    """Утилита для получения фильтров даты"""
    start_date = request.GET.get('startDate', f'{datetime.now().year}-01-01')
    end_date = request.GET.get('endDate', timezone.now().strftime('%Y-%m-%d'))

    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() + timedelta(days=1)

    return start_date_obj, end_date_obj, start_date, end_date


def apply_status_filters(queryset, status_param, status_field):
    """Применение фильтров статуса"""
    if status_param == 'paid':
        return queryset.filter(is_paid=True)
    elif status_param == 'unpaid':
        return queryset.filter(is_paid=False)
    elif status_param:
        return queryset.filter(**{status_field: status_param}).distinct()
    return queryset