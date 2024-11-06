import json
import os
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime
from collections import Counter
import re
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView
from openpyxl import load_workbook
from .models import Order, OrderItem, Organization, Invoice, LegalEntity
from .forms import OrderForm, OrganizationForm, InvoiceForm, UserCreationForm, OrderFileForm, LegalEntityForm
import logging
from docx import Document

logger = logging.getLogger(__name__)


def index(request):
    if request.user.is_authenticated:
        return render(request, 'index.html')
    return render(request, 'registration/login.html')


@method_decorator(login_required(login_url='login'), name='dispatch')
class OrderUploadView(FormView):
    template_name = 'order_upload.html'
    form_class = OrderForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organizations'] = Organization.objects.all()
        return context

    def get_form_kwargs(self):
        """ Передаем текущего пользователя в форму """
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        uploaded_file = form.cleaned_data.get('order_file')
        organizations = Organization.objects.all()

        if not uploaded_file:
            form.add_error('order_file', 'Пожалуйста, загрузите файл.')
            return self.render_to_response(self.get_context_data(form=form, organizations=organizations))

        order = form.save(commit=False)

        # Сохраните дату готовности, если она была предоставлена
        due_date = self.request.POST.get('due_date')
        if due_date:
            order.due_date = datetime.strptime(due_date, '%Y-%m-%d')
        order.save()

        # Логика проверки правильности загруженного файла
        try:
            wb = load_workbook(uploaded_file)
        except Exception as e:
            form.add_error(None, 'Ошибка загрузки файла: ' + str(e))
            return self.render_to_response(self.get_context_data(form=form, organizations=organizations))

        # Обработка загруженного файла
        sheet = wb.active
        header_cell_value = sheet.cell(row=1, column=3).value
        if header_cell_value != "Бланк №":
            form.add_error('order_file', 'Выберите правильный файл заказа')
            return self.render_to_response(self.get_context_data(form=form, organizations=organizations))
        cur_row, cur_column = 9, 15
        position, line = [], []

        def get_value(r, c):
            return sheet.cell(row=r, column=c).value

        while get_value(cur_row, cur_column) != 'шт.':
            cur_row += 1
        max_row = cur_row

        seq = [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 7, 8]
        for row in range(8, max_row):
            if get_value(row, 2):
                if 8 < row < max_row:
                    position.append(line)
                line = []
                for column in seq:
                    line.append(get_value(row, column))
            else:
                line.append(get_value(row, 7))
                line.append(get_value(row, 8))
            if row == max_row - 1:
                position.append(line)

        kind_mapping = {
            'дверь': 'door',
            'люк': 'hatch',
            'ворота': 'gate',
            'калитка': 'door',
            'фрамуга': 'transom'
        }
        type_mapping = {
            'ei-60': 'ei-60',
            'eis-60': 'eis-60',
            'eiws-60': 'eiws-60',
            'тех': 'tech',
            'ревиз': 'revision'
        }

        for i in range(len(position)):
            n_num = position[i][0]
            name = position[i][1]
            n_kind = next((value for key, value in kind_mapping.items() if re.search(key, name, re.IGNORECASE)), None)
            n_type = next((value for key, value in type_mapping.items() if re.search(key, name, re.IGNORECASE)), None)
            n_construction = 'NK' if re.search('-м', name.lower()) else 'SK'

            n_width, n_height = position[i][2], position[i][3]
            n_active_trim = position[i][4]
            n_open = position[i][5]
            n_platband = position[i][6]
            n_furniture = position[i][7]
            n_door_closer = position[i][8]
            n_step = position[i][9]
            n_ral = position[i][10]
            n_quantity = position[i][11]
            n_comment = position[i][12]

            glass = position[i][13:]
            counted_glass = dict(Counter(list(zip(glass[::2], glass[1::2]))))
            if (None, None) in counted_glass:
                del counted_glass[(None, None)]
            n_glass = sum(counted_glass.values()) if counted_glass else 0

            new_item = OrderItem(
                order=order,
                position_num=n_num,
                p_kind=n_kind,
                p_type=n_type,
                p_construction=n_construction,
                p_width=n_width,
                p_height=n_height,
                p_active_trim=n_active_trim,
                p_open=n_open,
                p_platband=n_platband,
                p_furniture=n_furniture,
                p_door_closer=n_door_closer,
                p_step=n_step,
                p_ral=n_ral,
                p_quantity=n_quantity,
                p_comment=n_comment,
                p_glass=counted_glass,
            )
            new_item.save()

        return redirect('orders_list')

    def form_invalid(self, form):
        organizations = Organization.objects.all()
        return self.render_to_response(self.get_context_data(form=form, organizations=organizations))


def change_order(request):
    pass


@login_required(login_url='login')
def organization_add(request):
    if request.method == 'POST':
        form = OrganizationForm(request.POST)

        # Получаем тип из POST данных
        type_ = request.POST.get('type')

        if form.is_valid():
            organization = form.save(commit=False)  # Создаём объект, но не сохраняем пока в БД

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

            organization.user = request.user  # Если нужно сохранить пользователя, который добавляет
            organization.save()
            return redirect('organization_list')  # Обновите на именованный URL или представление

    else:
        form = OrganizationForm()

    return render(request, 'organization_add.html', {'form': form})


@login_required(login_url='login')
def invoice_add(request):
    if request.method == 'POST':
        form = InvoiceForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # При успешном сохранении возвращаем JSON ответ
            return JsonResponse({'success': True})

        # Если форма не валидна, возвращаем ошибки в формате JSON
        error_messages = form.errors.as_json()
        return JsonResponse({'success': False, 'error': error_messages}, status=400)

    else:
        form = InvoiceForm(user=request.user)

    return render(request, 'invoice_add.html', {'form': form})


@login_required
def organization_list(request):
    user = request.user
    if user.is_superuser:  # Если пользователь является администратором
        organizations = Organization.objects.all()  # Заранее загружаем связанные заказы
    else:
        organizations = Organization.objects.filter(user=user)

    return render(request, 'organization_list.html', {'organizations': organizations, 'is_admin': user.is_superuser})


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            return redirect('login')  # замените 'login' на имя вашего URL входа
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required(login_url='login')
def orders_list(request):
    if request.user.is_staff:
        return render(request, 'orders_list.html', {'orders': Order.objects.all()})
    else:
        return render(request, 'orders_list.html', {'orders': Order.objects.filter(user=request.user)()})


@login_required(login_url='login')
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    # Отфильтрованные OrderItem, где статус не равен 'changed'
    filtered_items = order.items.exclude(p_status__in=['changed', 'canceled'])  #фильтрация по активным позициям

    if request.method == 'POST':
        form = OrderFileForm(request.POST, request.FILES)
        if form.is_valid():
            order.order_file = form.cleaned_data['order_file']  # Замените файл заказа
            order.save()
            return redirect('order_detail', order_id=order.id)  # Ссылаемся на order_id

    return render(request, 'order_detail.html', {'order': order, 'filtered_items': filtered_items})


@login_required(login_url='login')
def organization_detail(request, pk):
    organization = get_object_or_404(Organization, pk=pk)  # замените на вашу модель
    legal_entities = LegalEntity.objects.all()  # Получаем все экземпляры LegalEntity
    return render(request, 'organization_detail.html', {
        'organization': organization,
        'legal_entities': legal_entities,
    })


@login_required(login_url='login')
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return render(request, 'invoice_detail.html', {'invoice': invoice})


@login_required(login_url='login')
def invoices_list(request):
    invoices = Invoice.objects.all()
    return render(request, 'invoices_list.html', {'invoices': invoices})


@csrf_exempt  # Используйте его только если CSRF токены не применяются, исправьте позже.
def update_order_item_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            status_updates = data.get('status_updates', {})

            for item_id, new_status in status_updates.items():
                order_item = get_object_or_404(OrderItem, id=item_id)

                # Проверка на возможность изменения статуса
                #                if order_item.p_status in ['shipped', 'canceled']:
                #                    return JsonResponse({'status': 'error', 'message': f'Cannot change status for item {item_id}.'}, status=403)

                # Обновление статуса
                order_item.p_status = new_status
                order_item.save()

            return JsonResponse({'status': 'success', 'message': 'Statuses updated successfully!'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON format.'}, status=400)
        except Exception as e:
            logger.exception("Error updating order items' statuses")
            return JsonResponse({'status': 'error', 'message': 'An error occurred while processing your request.'},
                                status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)


def edit_organization(request, pk):
    organization = get_object_or_404(Organization, pk=pk)  # Получаем организацию по первичному ключу
    if request.method == 'POST':
        form = OrganizationForm(request.POST, instance=organization)  # Передаем экземпляр в форму
        if form.is_valid():
            form.save()  # Сохраняем изменения
            return redirect('organization_detail',
                            pk=organization.pk)  # Перенаправление на страницу детализации или список
    else:
        form = OrganizationForm(instance=organization)  # Заполняем форму данными существующей организации

    return render(request, 'organization_edit.html', {'form': form, 'organization': organization})


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
            'ЮЛ': legal_entity.name,
            'юл_огрн': legal_entity.ogrn,
            'юл_инн': legal_entity.inn,
            'юл_должность': legal_entity.ceo_title,
            'юл_фио': legal_entity.ceo_name,
            'организация': organization.name,
            'орг_огрн': organization.ogrn,
            'орг_инн': organization.inn,
            'орг_должность': organization.ceo_title,
            'орг_фио': organization.ceo_name,
            'основание': organization.ceo_footing


        }

        # Полный путь к шаблону
        file_path = os.path.join(settings.BASE_DIR, 'media/Contract/contract.docx')
        doc = Document(file_path)

        # Проходим по всем параграфам и заменяем метки
        for paragraph in doc.paragraphs:
            for key, value in data.items():
                if f'{{{key}}}' in paragraph.text or f'[[{key}]]' in paragraph.text:
                    paragraph.text = paragraph.text.replace(f'{{{key}}}', value)

        # Определяем путь, по которому будет сохраняться новый документ
        new_file_path = os.path.join(settings.MEDIA_ROOT, 'Contract/new_contract.docx')
        # Создаем директорию, если ее нет
        os.makedirs(os.path.dirname(new_file_path), exist_ok=True)

        # Сохраняем изменённый документ
        doc.save(new_file_path)

        # URL к новому файлу
        new_contract_url = os.path.join(settings.MEDIA_URL, 'Contract/new_contract.docx')
        legal_entity = LegalEntity.objects.all()

        return render(request, 'organization_detail.html',
                      {'organization': organization, 'new_contract_url': new_contract_url, 'legal_entities': legal_entity})
