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