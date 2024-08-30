from django.shortcuts import render, redirect
from .forms import OrderForm, OrganizationForm, InvoiceForm
from .models import OrderItem, Order  # Убедитесь, что вы импортировали модель
from openpyxl import load_workbook  # Проверьте, что библиотека установлена
import re
from django.contrib.auth.decorators import login_required


def index(request):
    return render(request, 'index.html')


def order_upload(request):
    if request.method == 'POST':
        form = OrderForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['order_file']  # Проверьте, что вы используете правильное имя поля
            order = Order.objects.create()

            # Логика проверки правильности загруженного файла
            try:
                wb = load_workbook(uploaded_file)
            except Exception as e:
                form.add_error(None, 'Ошибка загрузки файла: ' + str(e))
                return render(request, 'order_upload.html', {'form': form})

            sheet = wb.active
            max_row = 0
            cur_row, cur_column = 9, 15
            position = []

            def get_value(row, column):
                return sheet.cell(row=row, column=column).value

            while get_value(cur_row, cur_column) != 'шт.':
                cur_row += 1
            max_row = cur_row

            seq = [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 7, 8]
            for row in range(8, max_row):
                line = []
                if get_value(row, 1):  # Если у текущей строки есть номер позиции
                    for column in seq:
                        line.append(get_value(row, column))
                else:
                    line.append(get_value(row, 7))
                    line.append(get_value(row, 8))
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

            for i in range(0, len(position)):
                n_num = position[i][0]
                name = position[i][1]
                print(n_num, name)
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
                n_glass = list(zip(glass[::2], glass[1::2])) if glass else []

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
                    p_glass=n_glass,
                    status='in_query'
                )
                new_item.save()
                print(new_item)

            form = OrderForm()  # Сброс формы после успешной загрузки
            return render(request, 'order_upload.html', {'form': form})

    else:
        form = OrderForm()

    return render(request, 'order_upload.html', {'form': form})


@login_required
def organization_add(request):
    user = request.user
    if request.method == 'POST':
        form = OrganizationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')  # Перенаправьте на нужную страницу после сохранения
    else:
        form = OrganizationForm()

    return render(request, 'organization_add.html', {'form': form, 'user': user})


@login_required
def invoice_add(request):
    user = request.user
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')  # Перенаправьте на нужную страницу после сохранения
    else:
        form = InvoiceForm()

    return render(request, 'invoice_add.html', {'form': form, 'user': user})




