import datetime

from django.urls.base import reverse

from .models import Order, Shipment


def base_context(request):
    orders = Order.objects.all()
    date = datetime.date.today()
    date_now = date.today()
    today, overdue, ships = {}, {}, {}
    for order in orders:
        if order.due_date == date:
            order_url = reverse('order_detail', args=[order.pk])
            today[order.pk] = order_url
        if order.due_date is not None and order.due_date < date and order.status in ['в очереди', 'запущен']:
            order_url = reverse('order_detail', args=[order.pk])
            overdue[order.pk] = order_url
        if Shipment.objects.filter(order=order, date=date_now).exists():
            order_url = reverse('order_detail', args=[order.pk])
            ships[order.pk] = order_url

    return {'today': today, 'overdue': overdue, 'ships': ships}

