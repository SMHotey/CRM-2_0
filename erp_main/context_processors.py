import datetime

from django.urls.base import reverse

from .models import Order


def base_context(request):
    orders = Order.objects.all()
    date = datetime.date.today()
    today, overdue = {}, {}
    for order in orders:
        if order.due_date == date:
            order_url = reverse('order_detail', args=[order.pk])
            today[order.pk] = order_url
        if order.due_date is not None and order.due_date < date and order.status in ['в очереди', 'запущен']:
            order_url = reverse('order_detail', args=[order.pk])
            overdue[order.pk] = order_url
    return {'today': today, 'overdue': overdue}

