from django.db import transaction
from django.contrib.contenttypes.models import ContentType

from erp_main.models import StockOperation, StockOperationItem


class WarehouseService:
    """Сервис для операций со складом"""

    @staticmethod
    @transaction.atomic
    def add_to_stock(user, items, invoice_number=None, supplier=None, comment=""):
        """
        Поставить товар на приход
        items = [
            {
                'item': экземпляр DoorLock или DoorHandle,
                'quantity': 10,
                'purchase_price': 1500.00,  # опционально
            },
            ...
        ]
        """
        # Создаем операцию
        operation = StockOperation.objects.create(
            operation_type='receipt',
            created_by=user,
            invoice_number=invoice_number,
            supplier=supplier,
            comment=comment,
        )

        # Обрабатываем каждую позицию
        for item_data in items:
            item = item_data['item']
            quantity = item_data['quantity']
            purchase_price = item_data.get('purchase_price')

            # Создаем запись в операции
            StockOperationItem.objects.create(
                operation=operation,
                content_type=ContentType.objects.get_for_model(item),
                object_id=item.id,
                quantity=quantity,
                purchase_price=purchase_price,
            )

            # Обновляем остатки у товара
            item.quantity_in_stock += quantity

            # Если указана новая закупочная цена - обновляем
            if purchase_price is not None:
                item.purchase_price = purchase_price

            item.save()

        return operation

    @staticmethod
    @transaction.atomic
    def reserve_items(user, items, comment=""):
        """
        Зарезервировать товары
        items = [
            {
                'item': экземпляр DoorLock или DoorHandle,
                'quantity': 2,
            },
            ...
        ]
        """
        # Проверяем доступность перед резервированием
        for item_data in items:
            item = item_data['item']
            quantity = item_data['quantity']

            if not item.can_reserve(quantity):
                raise ValueError(
                    f"Недостаточно {item.name} на складе. "
                    f"Нужно: {quantity}, доступно: {item.available_quantity}"
                )

        # Создаем операцию
        operation = StockOperation.objects.create(
            operation_type='reservation',
            created_by=user,
            comment=comment,
        )

        # Резервируем товары
        for item_data in items:
            item = item_data['item']
            quantity = item_data['quantity']

            # Создаем запись в операции
            StockOperationItem.objects.create(
                operation=operation,
                content_type=ContentType.objects.get_for_model(item),
                object_id=item.id,
                quantity=quantity,
            )

            # Резервируем
            item.reserved_quantity += quantity
            item.save()

        return operation

    @staticmethod
    @transaction.atomic
    def consume_items(user, items, comment=""):
        """
        Списать товары со склада (после использования)
        items = [
            {
                'item': экземпляр DoorLock или DoorHandle,
                'quantity': 2,
            },
            ...
        ]
        """
        # Создаем операцию
        operation = StockOperation.objects.create(
            operation_type='consumption',
            created_by=user,
            comment=comment,
        )

        # Списываем товары
        for item_data in items:
            item = item_data['item']
            quantity = item_data['quantity']

            # Проверяем доступность
            if not item.can_consume(quantity):
                raise ValueError(
                    f"Недостаточно {item.name} на складе. "
                    f"Нужно: {quantity}, доступно: {item.available_quantity}"
                )

            # Создаем запись в операции
            StockOperationItem.objects.create(
                operation=operation,
                content_type=ContentType.objects.get_for_model(item),
                object_id=item.id,
                quantity=quantity,
            )

            # Сначала снимаем с резерва, если есть
            reserved_to_release = min(item.reserved_quantity, quantity)
            if reserved_to_release > 0:
                item.reserved_quantity -= reserved_to_release
                quantity -= reserved_to_release

            # Остальное списываем с остатка
            if quantity > 0:
                item.quantity_in_stock -= quantity

            item.save()

        return operation

    @staticmethod
    @transaction.atomic
    def cancel_reservation(user, items, comment=""):
        """
        Отменить резервирование товаров
        """
        operation = StockOperation.objects.create(
            operation_type='cancel_reservation',
            created_by=user,
            comment=comment,
        )

        for item_data in items:
            item = item_data['item']
            quantity = item_data['quantity']

            # Проверяем, что столько зарезервировано
            if item.reserved_quantity < quantity:
                raise ValueError(
                    f"Нельзя отменить резерв {item.name}. "
                    f"Хотим отменить: {quantity}, зарезервировано: {item.reserved_quantity}"
                )

            # Создаем запись в операции
            StockOperationItem.objects.create(
                operation=operation,
                content_type=ContentType.objects.get_for_model(item),
                object_id=item.id,
                quantity=quantity,
            )

            # Отменяем резерв
            item.reserved_quantity -= quantity
            item.save()

        return operation
