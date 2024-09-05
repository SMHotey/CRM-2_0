from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import OrderForm, OrganizationForm, InvoiceForm, UserCreationForm
from .models import OrderItem, Order, Organization  # Убедитесь, что вы импортировали модель
from openpyxl import load_workbook  # Проверьте, что библиотека установлена
import re
from django.contrib.auth.decorators import login_required


def index(request):
    return render(request, 'index.html')


@login_required(login_url='login')
def order_upload(request):
    global line
    if request.method == 'POST':
        form = OrderForm(user=request.user, data=request.POST, files=request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['order_file']  # Проверьте, что вы используете правильное имя поля
            order = form.save()

            # Логика проверки правильности загруженного файла
            try:
                wb = load_workbook(uploaded_file)
            except Exception as e:
                form.add_error(None, 'Ошибка загрузки файла: ' + str(e))
                return render(request, 'order_upload.html', {'form': form})

            sheet = wb.active
            max_row = 0
            cur_row, cur_column = 9, 15
            position, line = [], []

            def get_value(r, c):
                return sheet.cell(row=r, column=c).value

            while get_value(cur_row, cur_column) != 'шт.':
                cur_row += 1
            max_row = cur_row

            seq = [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 7, 8]
            row = 8
            for row in range(8, max_row):
                if get_value(row, 2):  # Если у текущей строки есть номер позиции
                    print(max_row)
                    if 8 < row < max_row:
                        print(line, '  ', row)
                        position.append(line)
                    line = []
                    for column in seq:
                        print(row, column)
                        line.append(get_value(row, column))
                else:
                    line.append(get_value(row, 7))
                    line.append(get_value(row, 8))
                if row == max_row-1:
                    print(line, ' end ', row)
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

                )
                new_item.save()


#            form = OrderForm()  # Сброс формы после успешной загрузки
            return redirect('orders_list')

    else:
        form = OrderForm(user=request.user)

    return render(request, 'order_upload.html', {'form': form})


@login_required(login_url='login')
def organization_add(request):
    if request.method == 'POST':
        form = OrganizationForm(request.POST)
        if form.is_valid():
            organization = form.save(commit=False)
            organization.user = request.user  # Добавьте текущего пользователя в объект
            organization.save()

            return redirect('organization_list')  # Перенаправьте на нужную страницу после сохранения
    else:
        form = OrganizationForm()

    return render(request, 'organization_add.html', {'form': form})


@login_required(login_url='login')
def invoice_add(request):
    if request.method == 'POST':
        form = InvoiceForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')  # Перенаправьте на нужную страницу после сохранения
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
            messages.success(request, f'Аккаунт для {username} был создан!')
            return redirect('login')  # замените 'login' на имя вашего URL входа
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


def orders_list(request):
    return render(request, 'orders_list.html',{'orders': Order.objects.all()})

