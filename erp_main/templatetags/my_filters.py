import calendar

from django import template

register = template.Library()


@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={'class': css_class})


@register.filter
def multiply(value, arg):
    return value * arg


@register.filter
def month_calendar(date):
    """Возвращает список недель для отображения календаря."""
    cal = calendar.Calendar()
    return cal.monthdayscalendar(date.year, date.month)


@register.filter
def format_date(year_month, day):
    """Формирует дату в формате YYYY-MM-DD."""
    return f"{year_month}{day:02d}"