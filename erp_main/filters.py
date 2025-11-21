import django_filters
from django import template
from .models import *

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Получить значение из словаря по ключу"""
    return dictionary.get(key)

class OrganizationFilter(django_filters.FilterSet):
    user = django_filters.NumberFilter(field_name='user__id')
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Organization
        fields = ['kind', 'user']


class InvoiceFilter(django_filters.FilterSet):
    date_range = django_filters.DateFromToRangeFilter(field_name='date')
    is_paid = django_filters.BooleanFilter(field_name='is_paid')
    organization = django_filters.NumberFilter(field_name='organization__id')
    internal_legal_entity = django_filters.NumberFilter(field_name='internal_legal_entity__id')
    number = django_filters.CharFilter(field_name='number', lookup_expr='icontains')

    class Meta:
        model = Invoice
        fields = []


class OrderFilter(django_filters.FilterSet):
    created_range = django_filters.DateFromToRangeFilter(field_name='created_at')
    due_date_range = django_filters.DateFromToRangeFilter(field_name='due_date')
    invoice = django_filters.NumberFilter(field_name='invoice__id')
    organization = django_filters.NumberFilter(field_name='invoice__organization__id')

    class Meta:
        model = Order
        fields = []