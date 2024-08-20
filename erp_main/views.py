from django.shortcuts import render
from .models import Order, OrderItem
from .forms import UploadFileForm
from openpyxl import load_workbook
import re
from django.contrib.auth.decorators import login_required


def upload_order(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']

            order = Order.objects.create()

            order_number = order.internal_order_number

            wb = load_workbook(uploaded_file)
            sheet = wb.active

            doors_nk, doors_2nk, hatches_nk = 0, 0, 0
            doors_sk, doors_2sk, hatches_sk, gates = 0, 0, 0, 0
            vent = 0
            glass_order = {}

            max_row, cur_column = 9, 15
            line = []
            order = []

            def get_value(row, column):
                return sheet.cell(row=row, column=column).value

            # Определяем размер таблицы с данными
            while get_value(max_row, cur_column) != 'шт.':
                max_row += 1

            # Читаем файл с заявкой
            seq = [1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14, 15, 7, 8]
            for row in range(8, max_row):
                line.clear()
                for column in seq:
                    line.append(get_value(row, column))

                if get_value(row, 1):

                    order.append(Position(*line))
                else:
                    add_glass = (get_value(row, 7), get_value(row, 8))
                    order[-1].glasses += add_glass

            for i in range(0, len(order)):
                quantity = order[i].quantity
                name = order[i].name
                if re.search('дверь', name.lower()):
                    if re.search('-м', name.lower()):
                        if order[i].active_length:
                            doors_2nk += quantity
                        else:
                            doors_nk += quantity
                    elif order[i].active_length:
                        doors_2sk += quantity
                    else:
                        doors_sk += quantity

                if re.search('ворота', name.lower()):
                    gates += quantity
                if re.search('люк', name.lower()):
                    if re.search('-м', name.lower()):
                        hatches_nk += quantity
                    else:
                        hatches_sk += quantity

                if order[i].glasses[0]:
                    for glass in range(0, len(order[i].glasses), 2):
                        key = (order[i].glasses[glass], order[i].glasses[glass + 1])
                        glass_order[str(key)] = glass_order.get(str(key), 0) + order[i].quantity

                if re.search('фрамуга', name.lower()):
                    vent += quantity

            order = Order(
                doors_nk=doors_nk,
                doors_sk=doors_sk,
                doors_2nk=doors_2nk,
                doors_2sk=doors_2sk,
                hatches_nk=hatches_nk,
                hatches_sk=hatches_sk,
                gates=gates,
                glass_order=glass_order,
                vent=vent,
                total_glasses=sum(glass_order.values()),

            )
            order.save()
            return render(request, 'success.html')

    form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})


def orders_list(request):
    orders = Order.objects.all()
    return render(request, 'orders_list.html', {'orders': orders})


@login_required
def add_order(request):
    if request.method == 'POST':
        external_order_number = request.POST.get('external_order_number')

        if external_order_number:
            new_order = Order(
                external_order_number=external_order_number,
                user=request.user  # Присваиваем текущего пользователя
            )
            new_order.save()
            return redirect('success_url')  # Замените на URL успешного завершения

    return render(request, 'add_order.html')  # Замените на ваш шаблон
