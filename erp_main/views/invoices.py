from functools import wraps

from django.db.models import Q, F, Sum

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.db import IntegrityError
from django.contrib import messages

from .. import models
from ..models import Invoice, Organization, InternalLegalEntity, Payment, Order, PaymentHistory
from ..forms import InvoiceForm, PaymentForm, PaymentReportForm
from .permissions import get_user_role_from_request, can_add_invoice, ajax_permission_required

import logging
logger = logging.getLogger(__name__)


# Использование
@login_required
# @ajax_permission_required(
#     lambda r: can_add_invoice(r.user, get_user_role_from_request(r)),
#     "У вас недостаточно прав для выставления счета"
# )
def invoice_add(request):
    if request.method == 'POST':
        referer_url = request.META.get('HTTP_REFERER')
        expected_url = request.build_absolute_uri(reverse('invoice_add'))
        form = InvoiceForm(request.user, request.POST, request.FILES)

        if form.is_valid():
            try:
                invoice = form.save()
                if referer_url != expected_url:
                    return JsonResponse({
                        'success': True,
                        'invoice_id': invoice.id,
                        'invoice_number': form.cleaned_data['number'],
                        'message': 'Счет добавлен'
                    })
                else:
                    return redirect('invoices_list')
            except IntegrityError:
                return JsonResponse({
                    'success': False,
                    'error': 'Запись с такими значениями полей уже существует.'
                }, status=400)

        error_messages = form.errors.as_json()
        return JsonResponse({'success': False, 'error': error_messages}, status=400)

    form = InvoiceForm(request.user)
    return render(request, 'invoice_add.html', {'form': form})


# def user_can_view(view_func):
#     @wraps(view_func)
#     def wrapper(request, pk, *args, **kwargs):
#         invoice = get_object_or_404(Invoice, pk=pk)
#
#         # Проверяем права доступа
#         if request.user.is_superuser or invoice.organization.user == request.user:
#             return view_func(request, pk, *args, **kwargs)
#         else:
#             return HttpResponseForbidden("У вас нет прав для просмотра этого счета")



def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    orders = Order.objects.filter(invoice=invoice)

    # Разделяем платежи по статусам
    planned_payments = invoice.payments.filter(status='planned').order_by('payment_date')
    completed_payments = invoice.payments.filter(status='completed').order_by('-payment_date')

    # Получаем историю всех платежей по этому счету
    payment_history = PaymentHistory.objects.filter(
        payment__invoice=invoice
    ).order_by('-changed_at')[:50]  # Последние 50 записей

    # Рассчитываем суммы
    total_planned = planned_payments.aggregate(total=models.Sum('amount'))['total'] or 0
    total_completed = completed_payments.aggregate(total=models.Sum('amount'))['total'] or 0
    total_all_payments = total_planned + total_completed

    remaining_for_new_payments = invoice.amount - total_all_payments

    if request.method == 'POST':
        form = InvoiceForm(request.user,request.POST, request.FILES, instance=invoice)
        if form.is_valid():
            form.save()
            return redirect('invoice_detail', pk=invoice.id)
    else:
        form = InvoiceForm(request.user, instance=invoice)

    return render(request, 'invoice_detail.html', {
        'invoice': invoice,
        'orders': orders,
        'planned_payments': planned_payments,
        'completed_payments': completed_payments,
        'payment_history': payment_history,
        'form': form,
        'remaining_amount': invoice.amount - invoice.payed_amount,
        'remaining_for_new_payments': remaining_for_new_payments,
        'total_planned': total_planned,
        'total_completed': total_completed,
    })


@login_required
def invoices_list(request):
    search_query = request.GET.get('search', '')
    selected_internal_legal_entity_id = request.GET.get('internal_legal_entity', None)
    sort_by = request.GET.get('sort', 'id')
    direction = request.GET.get('direction', 'desc')
    source = request.GET.get('source')
    hide_paid = request.GET.get('hide_paid', '')

    # Начальное значение для queryset
    if request.user.is_staff:
        invoices = Invoice.objects.all()
    else:
        invoices = Invoice.objects.filter(organization__user=request.user)

    if hide_paid == 'true':
        invoices = invoices.filter(Q(payed_amount__lt=F('amount')) | Q(payed_amount__lt=0))

    # Фильтрация по поисковому запросу - исправлено
    if search_query:
        invoices = invoices.filter(
            Q(number__icontains=search_query) |
            Q(organization__legalentity__name__icontains=search_query) |
            Q(organization__individualentrepreneur__full_name__icontains=search_query) |
            Q(organization__physicalperson__full_name__icontains=search_query)
        )

    # Фильтрация по выбранному юридическому лицу
    if selected_internal_legal_entity_id:
        try:
            selected_internal_legal_entity_id = int(selected_internal_legal_entity_id)
            invoices = invoices.filter(internal_legal_entity_id=selected_internal_legal_entity_id)
        except ValueError:
            pass

    # Сортировка - исправлено
    order_prefix = '-' if direction == 'desc' else ''

    if sort_by == 'number':
        invoices = invoices.order_by(f"{order_prefix}number")
    elif sort_by == 'date':
        invoices = invoices.order_by(f"{order_prefix}date")
    elif sort_by == 'amount':
        invoices = invoices.order_by(f"{order_prefix}amount")
    else:
        invoices = invoices.order_by(f"{order_prefix}id")

    if source:
        organization = Organization.objects.filter(id=source).first()
        if organization:
            invoices = invoices.filter(organization=organization)

    # Расчет статистики для всех отфильтрованных счетов
    total_amount = invoices.aggregate(total=Sum('amount'))['total'] or 0
    total_paid = invoices.aggregate(total=Sum('payed_amount'))['total'] or 0

    # Пагинация
    paginator = Paginator(invoices, 10)
    page_number = request.GET.get('page')
    invoices_page = paginator.get_page(page_number)

    # Получение всех юридических лиц для отображения в выпадающем списке
    internal_legal_entities = InternalLegalEntity.objects.all()

    return render(request, 'invoices_list.html', {
        'invoices': invoices_page,
        'hide_paid': hide_paid,
        'internal_legal_entity': internal_legal_entities,
        'selected_internal_legal_entity_id': selected_internal_legal_entity_id,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'request': request,
    })


@login_required
def add_payment(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_date = request.POST.get('payment_date')
        payment_type = request.POST.get('payment_type', 'bank_transfer')
        status = request.POST.get('status', 'planned')
        comment = request.POST.get('comment')

        if amount and payment_date:
            # Рассчитываем общую сумму всех платежей (планируемых + исполненных)
            total_payments = invoice.payments.aggregate(
                total=models.Sum('amount'))['total'] or 0
            total_completed = invoice.payments.filter(status='completed').aggregate(
                total=models.Sum('amount'))['total'] or 0
            planned_payments = invoice.payments.filter(status='planned').aggregate(
                total=models.Sum('amount'))['total'] or 0

            # Проверяем, что сумма всех платежей не превышает сумму счета
            new_total = total_payments + int(amount)
            if new_total <= invoice.amount:
                payment = Payment.objects.create(
                    invoice=invoice,
                    amount=amount,
                    payment_date=payment_date,
                    payment_type=payment_type,
                    status=status,
                    comment=comment,
                    created_by=request.user,
                    updated_by=request.user
                )

                # Если платеж сразу исполнен, обновляем счет
                if status == 'completed':
                    payment.update_invoice_amount()

                return redirect('invoice_detail', pk=invoice.id)
            else:
                messages.error(request,
                               f'Сумма всех платежей ({new_total} руб.) превышает сумму счета ({invoice.amount} руб.)')

    return redirect('invoice_detail', pk=invoice.id)


@login_required
def edit_payment(request, pk, payment_id):
    invoice = get_object_or_404(Invoice, pk=pk)
    payment = get_object_or_404(Payment, id=payment_id, invoice=invoice)

    print(f"DEBUG: Edit payment - Invoice: {pk}, Payment: {payment_id}, User: {request.user}, Method: {request.method}")

    # Проверка прав
    if not request.user.is_superuser and payment.status != 'planned':
        if request.method == 'POST':
            return JsonResponse({'error': 'Вы не можете редактировать исполненный платеж'}, status=403)
        else:
            return render(request, 'edit_payment_form.html', {
                'invoice': invoice,
                'payment': payment,
                'request': request,
                'error': 'Вы не можете редактировать исполненный платеж',
                'form': None
            })

    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment, invoice=invoice, request=request)

        if form.is_valid():
            try:
                # Сохраняем платеж
                payment = form.save(commit=False)
                payment.updated_by = request.user
                payment.invoice = invoice  # Убедимся, что платеж привязан к счету
                payment.save()

                print(f"DEBUG: Payment saved successfully")
                return JsonResponse({'success': True})

            except Exception as e:
                print(f"DEBUG: Error saving payment: {str(e)}")
                return JsonResponse({'error': f'Ошибка сохранения: {str(e)}'}, status=500)
        else:
            # Возвращаем ошибки валидации
            errors = form.errors.as_json()
            print(f"DEBUG: Form errors: {errors}")
            return JsonResponse({'error': 'Ошибки в форме', 'errors': errors}, status=400)

    # GET запрос - показываем форму
    form = PaymentForm(instance=payment, invoice=invoice, request=request)
    return render(request, 'edit_payment_form.html', {
        'invoice': invoice,
        'payment': payment,
        'form': form,
        'request': request,
    })

@login_required
def delete_payment(request, pk, payment_id):
    invoice = get_object_or_404(Invoice, pk=pk)
    payment = get_object_or_404(Payment, id=payment_id, invoice=invoice)

    if not payment.can_delete(request.user):
        messages.error(request, 'Вы не можете удалить исполненный платеж')
        return redirect('invoice_detail', pk=pk)

    if request.method == 'POST':
        payment.delete()
        messages.success(request, 'Платеж удален')

    return redirect('invoice_detail', pk=pk)


@login_required
def update_payment_status(request, pk, payment_id):
    invoice = get_object_or_404(Invoice, pk=pk)
    payment = get_object_or_404(Payment, id=payment_id, invoice=invoice)

    if request.method == 'POST':
        status = request.POST.get('status')

        if status in ['planned', 'completed']:
            # Только админ может менять статус исполненных платежей
            if payment.status == 'completed' and not request.user.is_superuser:
                return JsonResponse({'error': 'Только администратор может изменять статус исполненных платежей'},
                                    status=403)

            payment.status = status
            payment.updated_by = request.user
            payment.save()

            return JsonResponse({'success': True})

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def payment_report(request):
    form = PaymentReportForm(request.GET or None)
    payments = []
    total_amount = 0
    report_type = None
    report_type_display = ''  # Сначала пустая строка

    if form.is_valid():
        data = form.cleaned_data
        report_type = data['report_type']

        # Определяем отображаемое название ПОСЛЕ установки report_type
        report_type_display = {
            'completed': 'исполненным',
            'planned': 'планируемым'
        }.get(report_type, '')

        print(f"DEBUG: report_type={report_type}, report_type_display={report_type_display}")  # Для отладки
        start_date = data['start_date']
        end_date = data['end_date']

        # Базовый QuerySet
        if report_type == 'completed':
            payments = Payment.objects.filter(
                status='completed',
                payment_date__range=[start_date, end_date]
            ).select_related(
                'invoice',
                'invoice__organization',
                'invoice__internal_legal_entity',
                'invoice__organization__user'
            )
        else:  # planned
            payments = Payment.objects.filter(
                status='planned',
                payment_date__range=[start_date, end_date],
                invoice__is_paid=False  # только неоплаченные счета
            ).select_related(
                'invoice',
                'invoice__organization',
                'invoice__internal_legal_entity',
                'invoice__organization__user'
            )

        # Применение фильтров
        if data['organization']:
            payments = payments.filter(invoice__organization=data['organization'])

        if data['invoice_number']:
            payments = payments.filter(invoice__number__icontains=data['invoice_number'])

        if data['internal_legal_entity']:
            payments = payments.filter(invoice__internal_legal_entity=data['internal_legal_entity'])

        if data['manager']:
            payments = payments.filter(invoice__organization__user=data['manager'])

        # Ограничение для менеджеров (видят только свои организации)
        if not request.user.is_superuser:
            payments = payments.filter(invoice__organization__user=request.user)

        # Сортировка
        sort = request.GET.get('sort', 'payment_date')
        direction = request.GET.get('direction', 'asc')
        if direction == 'desc':
            sort = f'-{sort}'
        payments = payments.order_by(sort)

        # Общая сумма
        total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0


    context = {
        'form': form,
        'payments': payments,
        'total_amount': total_amount,
        'report_type': report_type,
        'report_type_display': report_type_display,
        'is_superuser': request.user.is_superuser,
    }

    return render(request, 'reports/payment_report.html', context)