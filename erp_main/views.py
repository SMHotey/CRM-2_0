import json
import os
from django.conf import settings
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import FormView, CreateView, ListView, DetailView, UpdateView
from .models import Order, OrderItem, Organization, Invoice, LegalEntity, GlassInfo, OrderChangeHistory
from .forms import OrderForm, OrganizationForm, InvoiceForm, UserCreationForm, OrderFileForm, LegalEntityForm
import logging
from docx import Document
from datetime import datetime
from collections import Counter
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse
from openpyxl import load_workbook
from django.contrib.auth.mixins import LoginRequiredMixin
import re
from django.contrib import messages


logger = logging.getLogger(__name__)

def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')  # Перенаправление на главную страницу
        else:
            messages.error(request, 'Неверный логин или пароль.')
    return render(request, 'registration/login.html')


def index(request):
    if request.user.is_authenticated:
        return render(request, 'index.html')
    return render(request, 'registration/login.html')


class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'organization_add.html'

    def form_valid(self, form):
        type_ = self.request.POST.get('type')

        organization = form.save(commit=False)
        if type_ == 'organization':
            organization.inn = form.cleaned_data.get('inn')
            organization.name = form.cleaned_data.get('name')
            organization.phone_number = None
            organization.name_fl = None
        elif type_ == 'individual':
            organization.name_fl = form.cleaned_data.get('name_fl')
            organization.phone_number = form.cleaned_data.get('phone_number')
            organization.inn = None
            organization.name = None

        organization.user = self.request.user
        organization.save()
        return redirect('organization_list')


class OrganizationListView(LoginRequiredMixin, ListView):
    model = Organization
    template_name = 'organization_list.html'
    context_object_name = 'organizations'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Organization.objects.all()
        return Organization.objects.filter(user=user)


class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    template_name = 'organization_detail.html'
    context_object_name = 'organization'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['legal_entities'] = LegalEntity.objects.all()
        return context


class OrganizationUpdateView(LoginRequiredMixin, UpdateView):
    model = Organization
    form_class = OrganizationForm
    template_name = 'organization_edit.html'
    context_object_name = 'organization'

    def get_object(self, queryset=None):
        return get_object_or_404(Organization, pk=self.kwargs['pk'])

    def get_success_url(self):
        return reverse('organization_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        return super().form_valid(form)


class OrderUploadView(LoginRequiredMixin, FormView):
    template_name = 'order_upload.html'
    form_class = OrderForm

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        if self.request.user.is_superuser:
            context['organizations'] = Organization.objects.all()
        else:
            context['organizations'] = Organization.objects.filter(user=self.request.user)

        return context

    def get_form_kwargs(self):
        """Передаем текущего пользователя в форму"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        uploaded_file = form.cleaned_data.get('order_file')
        order_id = self.kwargs.get('order_id')

        if order_id:
            # Извлечение существующего заказа из базы
            order = get_object_or_404(Order, pk=order_id)
            old_file = order.order_file # старый файл заказа для сохранения в истории изменений
            is_update = True
        else:
            # Создание нового заказа на основе данных из формы
            order = Order()
            is_update = False
            order.invoice = form.cleaned_data.get('invoice')  # Извлекаем счёт из формы
            order.due_date = form.cleaned_data.get('due_date')  # Извлекаем дату готовности
            order.comment = form.cleaned_data.get('comment', '')  # Извлекаем комментарий



        # Обновление поля order_file только если файл был загружен
        if uploaded_file:
            order.order_file = uploaded_file  # Загружаем файл, если он был загружен

        # Проверка на наличие файла, если это новый заказ
        if not uploaded_file and not is_update:
            form.add_error('order_file', 'Пожалуйста, загрузите файл.')
            return self._render_form_with_context(form)

        # Сохраняем объект Order
        order.save()

        # Обработка загрузки файла и обновление позиций заказа
        if uploaded_file:  # Обработка файла только если он был загружен
            try:
                wb = load_workbook(uploaded_file)
            except Exception as e:
                form.add_error(None, 'Ошибка загрузки файла: ' + str(e))
                return self._render_form_with_context(form)

            if not self._check_header(wb.active):
                form.add_error('order_file', 'Выберите правильный файл заказа')
                return self._render_form_with_context(form)

            new_positions = self._process_file(wb.active)
            if is_update:
                self._update_order_items(order, new_positions, old_file)  # Обновление позиций для существующего заказа
            else:
                self._create_order_items(order, new_positions)  # Создание новых позиций для нового заказа

        return redirect(reverse('order_detail', args=[order.id]))

    def _render_form_with_context(self, form):
        organizations = Organization.objects.all()
        return self.render_to_response(self.get_context_data(form=form, organizations=organizations))

    def _check_header(self, sheet):
        return sheet.cell(row=1, column=3).value == "Бланк №"

    def _process_file(self, sheet):
        cur_row, cur_column = 9, 15
        while sheet.cell(row=cur_row, column=cur_column).value != 'шт.':
            cur_row += 1
        max_row = cur_row

        seq = [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 7, 8]
        positions = []
        line = []

        for row in range(8, max_row):
            if sheet.cell(row=row, column=2).value:
                if line:
                    positions.append(line)
                line = [sheet.cell(row=row, column=column).value for column in seq]
            else:
                line.extend([sheet.cell(row=row, column=7).value, sheet.cell(row=row, column=8).value])

        if line:
            positions.append(line)

        return positions

    def _update_order_items(self, order, new_positions, old_file):
        current_items = {item.position_num: item for item in OrderItem.objects.filter(order=order)}
        print(current_items)

        current_date = datetime.now().strftime('%d.%m.%Y')
        changes_made = []

        for data in new_positions:
            n_num = str(data[0])
            name = data[1]
            n_kind = self._get_kind(name)
            n_type = self._get_type(name)
            n_construction = 'NK' if re.search('-м', name.lower()) else 'SK'

            new_item_data = {
                'p_kind': n_kind,
                'p_type': n_type,
                'p_construction': n_construction,
                'p_height': data[2],
                'p_width': data[3],
                'p_active_trim': data[4],
                'p_open': data[5],
                'p_platband': data[6],
                'p_furniture': data[7],
                'p_door_closer': data[8],
                'p_step': data[9],
                'p_ral': str(data[10]),
                'p_quantity': data[11],
                'p_comment': data[12],
                'p_glass': self._count_glass(data[13:]),
            }

            if n_num in current_items: # если номер позиции есть в новом бланке заказа
                first = 0
                current_item = current_items[n_num]
                print(current_item)
                for field, new_value in new_item_data.items():
                    old_value = getattr(current_item, field, None)
                    if str(old_value) != str(new_value) and field != 'p_glass':

                        field_name = OrderItem._meta.get_field(field).verbose_name
                        if old_value:
                            if first == 0:
                                changes_made.append(f'<br> поз. {n_num}:  {field_name} с "{old_value}" на "{new_value}"; ')
                                first = 1
                            else:
                                changes_made.append(f'{field_name} с "{old_value}" на "{new_value}";')
                        else:
                            changes_made.append(f'поз. {n_num}: добавлен {field_name} "{new_value}";')
                        setattr(current_item, field, new_value)

                if changes_made:
                    current_item.delete()

                    new_item = OrderItem(order=order, position_num=n_num, **new_item_data)
                    new_item.save()  # сохраняем обновленный объект
            else:
                new_item = OrderItem(order=order, position_num=n_num, **new_item_data)
                new_item.p_status = 'in_query'
                new_item.save()  # Сохраняем новый объект OrderItem

                # Сохраняем информацию о стеклах
                self._save_glass_info(new_item, new_item_data['p_glass'])

        if changes_made:
#            changes_made = ('Изменения от ' + str(current_date) + ': <br>' + str(changes_made))
            comment = str(changes_made).replace('[', '').replace(']', '').replace("'", "").replace(",", "").strip()[5::]
            order.save()  # Сохраняем изменения в заказе
            add_changes = OrderChangeHistory(order=order, order_file=old_file, changed_by=self.request.user, comment=comment)
            add_changes.save()

    def _create_order_items(self, order, new_positions):
        for data in new_positions:
            n_num = data[0]
            name = data[1]
            n_kind = self._get_kind(name)
            n_type = self._get_type(name)
            n_construction = 'NK' if re.search('-м', name.lower()) else 'SK'

            new_item_data = {
                'p_kind': n_kind,
                'p_type': n_type,
                'p_construction': n_construction,
                'p_height': data[2],
                'p_width': data[3],
                'p_active_trim': data[4],
                'p_open': data[5],
                'p_platband': data[6],
                'p_furniture': data[7],
                'p_door_closer': data[8],
                'p_step': data[9],
                'p_ral': data[10],
                'p_quantity': data[11],
                'p_comment': data[12],
                'p_glass': self._count_glass(data[13:]),
            }

            new_item = OrderItem(order=order, position_num=n_num, **new_item_data)
            new_item.p_status = 'in_query'
            new_item.save()  # Сохраняем новый объект

            # Сохраняем информацию о стеклах
            self._save_glass_info(new_item, new_item_data['p_glass'])

    def _get_kind(self, name):
        kind_mapping = {
            'дверь': 'door', 'люк': 'hatch', 'ворота': 'gate',
            'калитка': 'door', 'фрамуга': 'transom'
        }
        return next((value for key, value in kind_mapping.items() if re.search(key, name, re.IGNORECASE)), None)

    def _get_type(self, name):
        type_mapping = {
            'ei-60': 'ei-60', 'eis-60': 'eis-60', 'eiws-60': 'eiws-60',
            'тех': 'tech', 'ревиз': 'revision'
        }
        return next((value for key, value in type_mapping.items() if re.search(key, name, re.IGNORECASE)), None)

    def _save_glass_info(self, new_item, counted_glass):
        """Сохраняет информацию о стеклах для нового элемента заказа."""
        for (height, width), quantity in counted_glass.items():
            if height and width:  # Проверяем, что высота и ширина заданы
                # Создаем новый объект GlassInfo, который содержит внешний ключ к OrderItem
                new_glass = GlassInfo(height=height, width=width, quantity=quantity, order_items=new_item)
                new_glass.save()  # Сохраняем объект GlassInfo

    def _count_glass(self, glass_data):
        counted_glass = dict(Counter(list(zip(glass_data[::2], glass_data[1::2]))))
        counted_glass.pop((None, None), None)
        return counted_glass

    def form_invalid(self, form):
        organizations = Organization.objects.all()
        return self.render_to_response(self.get_context_data(form=form, organizations=organizations))

def glass(request):
    return render(request, 'glass_info.html')


@login_required(login_url='login')
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
                        'message': 'Счет добавлен'})
                else:
                    return redirect(invoices_list)

            except IntegrityError:
                return JsonResponse({
                    'success': False,
                    'error': 'Запись с такими значениями полей уже существует.'
                }, status=400)

        error_messages = form.errors.as_json()
        return JsonResponse({'success': False, 'error': error_messages}, status=400)

    form = InvoiceForm(request.user)  # Создание экземпляра формы
    return render(request, 'invoice_add.html', {'form': form})  # Возвращаем шаблон с формой


def orders_list(request):
    orders = []
    if request.user.is_staff:
        orders = Order.objects.all().order_by('-id')
    else:
        if Order.objects.filter(invoice__organization__user=request.user):
            orders = Order.objects.filter(invoice__organization__user=request.user).order_by('-id')

    paginator = Paginator(orders, 20)  # Создаем пагинатор
    page_number = request.GET.get('page')  # Получаем номер страницы из GET параметров
    orders = paginator.get_page(page_number)  # Получаем заказы для текущей страницы

    return render(request, 'orders_list.html', {'orders': orders})


@login_required(login_url='login')
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    changes = order.changes.all()

    # Отфильтрованные OrderItem, где статус не равен 'changed'
    filtered_items = order.items.exclude(p_status__in=['changed',])  #фильтрация по активным позициям

    if request.method == 'POST':
        form = OrderFileForm(request.POST, request.FILES)
        if form.is_valid():
            order.order_file = form.cleaned_data['order_file']  # Замените файл заказа
            order.save()
            return redirect('order_detail', order_id=order.id)  # Ссылаемся на order_id

    context = {
        'order': order,
        'filtered_items': filtered_items,
        'changes': changes,
    }

    return render(request, 'order_detail.html', context)



@login_required(login_url='login')
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, id=pk)

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

    return render(request, 'invoice_detail.html', {'invoice': invoice, 'form': form})


@login_required(login_url='login')
def invoices_list(request):
    search_query = request.GET.get('search', '')
    selected_legal_entity_id = request.GET.get('legal_entity', None)
    sort_by = request.GET.get('sort', 'id')
    direction = request.GET.get('direction', 'desc')

    # Начальное значение для queryset
    if request.user.is_staff:
        invoices = Invoice.objects.all()
    else:
        invoices = Invoice.objects.filter(organization__user=request.user)

    # Фильтрация по поисковому запросу
    if search_query:
        invoices = invoices.filter(number__icontains=search_query) | invoices.filter(organization__name__icontains=search_query)

    # Фильтрация по выбранному юридическому лицу
    if selected_legal_entity_id:
        # Выберите только если selected_legal_entity_id является числом
        try:
            selected_legal_entity_id = int(selected_legal_entity_id)  # Приводим к числу
            invoices = invoices.filter(legal_entity_id=selected_legal_entity_id)
        except ValueError:
            pass  # Игнорируем, если не удалось привести к числу

    # Сортировка
    if sort_by == 'number':
        invoices = invoices.order_by(f"{'-' if direction == 'desc' else ''}id")
    else:
        invoices = invoices.order_by('-id')  # Сортировка по умолчанию

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


def update_order_item_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            updates = data.get('updates', {})

            for item_id in updates.keys():
                order_item = get_object_or_404(OrderItem, id=item_id)
                new_data = updates[item_id]
                order_item.p_status = new_data['status']
                order_item.workshop = new_data['workshop']
                if order_item.workshop == '2' and new_data['path'] != 'order_detail':
                    order_item.p_status = 'stopped'
                if (order_item.p_status == 'stopped' or order_item.p_status == 'canceled') and new_data['path'] != 'order_detail':
                    order_item.workshop = '2'
                order_item.save()

            return JsonResponse({'status': 'success', 'message': 'Statuses updated successfully!'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
        except Exception as e:
            logger.exception("Error updating order items' statuses")
            return JsonResponse({'status': 'error', 'message': 'An error occurred while processing your request.'},
                                status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)



def create_legal_entity(request):
    if request.method == 'POST':
        form = LegalEntityForm(request.user, request.POST)
        if form.is_valid():
            form.save()  # Сохраните объект LegalEntity
            return redirect('organization_list')  # Перенаправление на страницу успеха
    else:
        form = LegalEntityForm(request.user)

    return render(request, 'legal_entity_form.html', {'form': form})


def create_contract(request, pk):
    if request.method == 'POST':
        legal_entity_id = request.POST.get('legal_entity')
        legal_entity = get_object_or_404(LegalEntity, pk=legal_entity_id)
        num_of = 123
        organization = get_object_or_404(Organization, pk=pk)

        data = {
            'юл': legal_entity.name,
            'юл_огрн': legal_entity.ogrn,
            'юл_инн': legal_entity.inn,
            'юл_должность': legal_entity.ceo_title,
            'юл_фио': legal_entity.ceo_name,
            'юл_кпп': legal_entity.kpp,
            'юл_рс': legal_entity.r_s,
            'юл_банк': legal_entity.bank,
            'юл_бик': legal_entity.bik,
            'юл_корс': legal_entity.k_s,
            'юл_адрес': legal_entity.address,
            'юл_email': legal_entity.email,
            'орг': organization.name,
            'орг_огрн': organization.ogrn,
            'орг_инн': organization.inn,
            'орг_должность': organization.ceo_title,
            'орг_фио': organization.ceo_name,
            'основание': organization.ceo_footing,
            'орг_кпп': organization.kpp,
            'орг_рс': organization.r_s,
            'орг_банк': organization.bank,
            'орг_бик': organization.bik,
            'орг_счет': organization.k_s,
            'орг_адрес': organization.address,
            'орг_email': organization.email,
        }
        # Полный путь к шаблону
        file_path = os.path.join(settings.BASE_DIR, 'media/contracts/contract.docx')
        doc = Document(file_path)

        # Проходим по всем параграфам и заменяем метки
        def replace_in_paragraphs(paragraphs, data):
            for paragraph in paragraphs:
                for key, value in data.items():
                    if f'{{{key}}}' in paragraph.text or f'[[{key}]]' in paragraph.text:
                        paragraph.text = paragraph.text.replace(f'{{{key}}}', value)
                        paragraph.text = paragraph.text.replace(f'[[{key}]]', value)

        # Заменяем метки в главных параграфах
        replace_in_paragraphs(doc.paragraphs, data)

        # Заменяем метки в таблицах
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    replace_in_paragraphs(cell.paragraphs, data)

        # Определяем путь, по которому будет сохраняться новый документ
        new_file_path = os.path.join(settings.MEDIA_ROOT, 'contracts/new_contract.docx')
        # Создаем директорию, если ее нет
        os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

        # Сохраняем изменённый документ
        doc.save(new_file_path)

        # URL к новому файлу
        new_contract_url = os.path.join(settings.MEDIA_URL, 'contracts/new_contract.docx')
        legal_entity = LegalEntity.objects.all()

        return render(request, 'organization_detail.html',
                      {'organization': organization, 'new_contract_url': new_contract_url,
                       'legal_entities': legal_entity})

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'


def glass_info(request, pk=''):
    if pk == '':
        orders = Order.objects.all()
    else:
        orders = [get_object_or_404(Order, pk=pk)]

    return render(request, 'glass_info.html', {'orders': orders,
                                               'glass_options': GlassInfo.OPTIONS_CHOICE,
                                               'glass_status': GlassInfo.GLASS_STATUS_CHOICE})



@require_POST
def update_glass_status(request, glass_id):
    glass = get_object_or_404(GlassInfo, id=glass_id)
    new_status = request.POST.get('status')
    if new_status in dict(GlassInfo.GLASS_STATUS_CHOICE).keys():
        glass.status = new_status
        glass.save()
    return redirect('glass_info')  # Перенаправление обратно на страницу с заказами

def update_workshop(request, order_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        workshop_value = data.get('workshop')
        if workshop_value in ['1', '3']:
            OrderItem.objects.filter(order_id=order_id).update(workshop=workshop_value)
            OrderItem.objects.filter(order_id=order_id).update(p_status='product')
        elif workshop_value == '2':
            OrderItem.objects.filter(order_id=order_id).update(workshop=workshop_value)
            OrderItem.objects.filter(order_id=order_id).update(p_status='stopped')
        elif workshop_value == '4':
            OrderItem.objects.filter(order_id=order_id).update(p_status='ready')
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

def make_passport(self):
    pass

def calculate(self: OrderItem):
    pass