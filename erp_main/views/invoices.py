from functools import wraps

from django.core.exceptions import PermissionDenied

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.urls import reverse
from django.db import IntegrityError
from django.views.decorators.http import require_POST

from ..models import Invoice, Organization, LegalEntity
from ..forms import InvoiceForm
from .mixins import UserAccessMixin
from .permissions import get_user_role_from_request, can_add_invoice, ajax_permission_required


# Использование
@login_required
@ajax_permission_required(
    lambda r: can_add_invoice(r.user, get_user_role_from_request(r)),
    "У вас недостаточно прав для выставления счета"
)
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


@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, id=pk)
    orders = invoice.invoice.all()

    if request.method == 'POST':
        form = InvoiceForm(user=request.user, data=request.POST, files=request.FILES, instance=invoice)
        if form.is_valid():
            invoice = form.save()
            file_url = invoice.invoice_file.url if invoice.invoice_file else None

            return JsonResponse({
                'success': True,
                'file_url': file_url,
                'redirect_url': reverse('invoice_detail', args=[invoice.id])
            })
        else:
            error_messages = form.errors.as_json()
            return JsonResponse({'success': False, 'error': error_messages}, status=400)

    else:
        form = InvoiceForm(user=request.user, instance=invoice)

    return render(request, 'invoice_detail.html', {
        'invoice': invoice,
        'orders': orders,
        'form': form
    })


@login_required
def invoices_list(request):
    search_query = request.GET.get('search', '')
    selected_legal_entity_id = request.GET.get('legal_entity', None)
    sort_by = request.GET.get('sort', 'id')
    direction = request.GET.get('direction', 'desc')
    source = request.GET.get('source')

    # Начальное значение для queryset
    if request.user.is_staff:
        invoices = Invoice.objects.all()
    else:
        invoices = Invoice.objects.filter(organization__user=request.user)

    # Фильтрация по поисковому запросу
    if search_query:
        invoices = invoices.filter(
            Q(number__icontains=search_query) |
            Q(organization__name__icontains=search_query)
        )

    # Фильтрация по выбранному юридическому лицу
    if selected_legal_entity_id:
        try:
            selected_legal_entity_id = int(selected_legal_entity_id)
            invoices = invoices.filter(legal_entity_id=selected_legal_entity_id)
        except ValueError:
            pass

    # Сортировка
    if sort_by == 'number':
        invoices = invoices.order_by(f"{'-' if direction == 'desc' else ''}id")
    else:
        invoices = invoices.order_by('-id')

    if source:
        organization = Organization.objects.filter(id=source).first()
        invoices = invoices.filter(organization=organization)

    # Пагинация
    paginator = Paginator(invoices, 10)
    page_number = request.GET.get('page')
    invoices_page = paginator.get_page(page_number)

    # Получение всех юридических лиц для отображения в выпадающем списке
    legal_entities = LegalEntity.objects.all()

    return render(request, 'invoices_list.html', {
        'invoices': invoices_page,
        'legal_entities': legal_entities,
        'selected_legal_entity_id': selected_legal_entity_id,
        'request': request,
    })