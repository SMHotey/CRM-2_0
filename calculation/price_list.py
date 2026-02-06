# models.py
from decimal import Decimal

from django.db import models
from django.contrib.auth import get_user_model

import json

User = get_user_model()


class PriceTemplate(models.Model):
    """ШАБЛОН прайса"""
    name = models.CharField('Название', max_length=200)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    organization = models.ForeignKey('Organization', blank=True, null=True, on_delete=models.CASCADE)

    prices_data = models.JSONField(
        'Данные прайса',
        default=dict,
        help_text='JSON со всеми ценами'
    )

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    version = models.IntegerField('Версия', default=1)
    is_active = models.BooleanField('Активен', default=True)

    class Meta:
        verbose_name = 'Шаблон прайса'
        verbose_name_plural = 'Шаблоны прайсов'
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.name} (v{self.version})"

    def get_price(self, category, size, fire_rating):
        """Удобный доступ к цене"""
        key = f"{category}_{size}_{fire_rating}"
        return self.prices_data.get(key)

    def set_price(self, category, size, fire_rating, price):
        """Установка цены"""
        key = f"{category}_{size}_{fire_rating}"
        self.prices_data[key] = str(price)  # Decimal → string
        self.save()

    def increment_version(self):
        """Увеличивает версию"""
        self.version += 1
        self.save()

    def get_default_structure(self):
        """Возвращает структуру по умолчанию"""
        return {
            # Двери 1-ств. до 2200*1000
            "door_1_2200_1000_teh": "0.00",
            "door_1_2200_1000_ei60": "0.00",
            "door_1_2200_1000_eis60": "0.00",

            # Двери 1-ств. до 2200*1100
            "door_1_2200_1100_teh": "0.00",
            "door_1_2200_1100_ei60": "0.00",
            "door_1_2200_1100_eis60": "0.00",

            # Двери 2-ств. до 2200*1300
            "door_2_2200_1300_teh": "0.00",
            "door_2_2200_1300_ei60": "0.00",
            "door_2_2200_1300_eis60": "0.00",

            # Люки до 1000*1000
            "hatch_1_1000_1000_teh": "0.00",
            "hatch_1_1000_1000_ei60": "0.00",
            "hatch_1_1000_1000_eis60": None,

            # Люки до 1100*1100
            "hatch_1_1100_1100_teh": "0.00",
            "hatch_1_1100_1100_ei60": "0.00",
            "hatch_1_1100_1100_eis60": None,

            # Ворота
            "gate_teh": "0.00",
            "gate_ei60": "0.00",
            "gate_eis60": None,

            "big_gate_teh": "0.00",
            "big_gate_ei60": "0.00",

            # Нестандартные
            "not_standard_teh": "0.00",
            "not_standard_ei60": "0.00",
            "not_standard_eis60": "0.00",
        }

    def save(self, *args, **kwargs):
        # Инициализируем структуру при создании
        if not self.prices_data:
            self.prices_data = self.get_default_structure()
        super().save(*args, **kwargs)


class ManagerPriceList(models.Model):
    """ИНДИВИДУАЛЬНЫЙ прайс менеджера - композиция через JSON"""
    manager = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='manager_prices',
        verbose_name='Менеджер'
    )
    client = models.ForeignKey(
        'Client',
        on_delete=models.CASCADE,
        related_name='client_prices',
        verbose_name='Клиент'
    )
    template = models.ForeignKey(
        PriceTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derived_prices',
        verbose_name='Базовый шаблон'
    )

    # СНИМОК данных шаблона на момент создания
    snapshot_data = models.JSONField(
        'Снимок прайса',
        default=dict,
        help_text='Данные из шаблона в момент создания'
    )

    # Индивидуальные настройки (могут переопределять snapshot)
    custom_prices = models.JSONField(
        'Индивидуальные цены',
        default=dict,
        help_text='Переопределения цен для этого клиента'
    )

    # Общие настройки
    markup_percent = models.DecimalField(
        'Общая наценка %',
        max_digits=5,
        decimal_places=2,
        default=0
    )
    discount_percent = models.DecimalField(
        'Общая скидка %',
        max_digits=5,
        decimal_places=2,
        default=0
    )

    # Метаданные
    name = models.CharField('Название', max_length=200)
    is_active = models.BooleanField('Активен', default=True)
    valid_from = models.DateField('Действует с', auto_now_add=True)
    valid_until = models.DateField('Действует до', null=True, blank=True)

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Прайс менеджера'
        verbose_name_plural = 'Прайсы менеджеров'
        ordering = ['-date_created']
        unique_together = ['manager', 'client', 'name']
        indexes = [
            models.Index(fields=['manager', 'client', 'is_active']),
            models.Index(fields=['valid_from', 'valid_until']),
        ]

    def __str__(self):
        return f"{self.name} - {self.client.name}"

    def save(self, *args, **kwargs):
        # Автоматически создаем snapshot при первом сохранении
        if self.template and not self.snapshot_data:
            self._create_snapshot()

        # Генерируем имя, если не указано
        if not self.name and self.client:
            base_name = self.template.name if self.template else 'Прайс'
            self.name = f"{base_name} - {self.client.name}"

        super().save(*args, **kwargs)

    def _create_snapshot(self):
        """Создает снимок данных шаблона"""
        from decimal import Decimal

        self.snapshot_data = {
            'template_id': self.template.id,
            'template_name': self.template.name,
            'template_version': self.template.version,
            'snapshot_date': timezone.now().isoformat(),
            'original_prices': self.template.prices_data.copy(),
        }

    def get_price(self, category, size, fire_rating):
        """
        Получает цену с учетом всех переопределений
        Приоритет: custom_prices > snapshot_data
        """
        key = f"{category}_{size}_{fire_rating}"

        # 1. Проверяем индивидуальные настройки
        if key in self.custom_prices:
            price_str = self.custom_prices[key]
            if price_str is None:
                return None
            price = Decimal(price_str)

        # 2. Используем снимок шаблона
        elif 'original_prices' in self.snapshot_data and key in self.snapshot_data['original_prices']:
            price_str = self.snapshot_data['original_prices'][key]
            if price_str is None:
                return None
            price = Decimal(price_str)

        # 3. Цена не найдена
        else:
            return None

        # Применяем общие коэффициенты
        price = self._apply_coefficients(price)
        return price

    def set_custom_price(self, category, size, fire_rating, price):
        """Устанавливает индивидуальную цену"""
        key = f"{category}_{size}_{fire_rating}"

        if price is None:
            self.custom_prices[key] = None
        else:
            self.custom_prices[key] = str(price)

        self.save()

    def reset_custom_price(self, category, size, fire_rating):
        """Сбрасывает индивидуальную цену к шаблонной"""
        key = f"{category}_{size}_{fire_rating}"
        if key in self.custom_prices:
            del self.custom_prices[key]
            self.save()

    def _apply_coefficients(self, price):
        """Применяет наценки и скидки"""
        from decimal import Decimal

        # Наценка
        if self.markup_percent:
            price = price * (1 + self.markup_percent / Decimal('100'))

        # Скидка
        if self.discount_percent:
            price = price * (1 - self.discount_percent / Decimal('100'))

        return price

    def get_all_prices(self):
        """Возвращает все цены с учетом переопределений"""
        from decimal import Decimal

        result = {}

        # Базовые цены из snapshot
        base_prices = self.snapshot_data.get('original_prices', {})

        for key, base_price_str in base_prices.items():
            # Пропускаем null значения
            if base_price_str is None:
                result[key] = None
                continue

            # Используем переопределение или базовую цену
            if key in self.custom_prices:
                custom_price_str = self.custom_prices[key]
                if custom_price_str is None:
                    result[key] = None
                    continue
                price = Decimal(custom_price_str)
            else:
                price = Decimal(base_price_str)

            # Применяем коэффициенты
            price = self._apply_coefficients(price)
            result[key] = price

        return result

    def create_quote(self, items):
        """
        Создает коммерческое предложение на основе прайса
        items = [
            {
                'category': 'door_1',
                'size': '2200_1000',
                'fire_rating': 'ei60',
                'quantity': 2,
                'notes': 'Срочно'
            },
            # ...
        ]
        """
        from decimal import Decimal

        quote_items = []
        total = Decimal('0')

        for item in items:
            key = f"{item['category']}_{item['size']}_{item['fire_rating']}"
            unit_price = self.get_price(
                item['category'],
                item['size'],
                item['fire_rating']
            )

            if unit_price is None:
                continue

            quantity = item.get('quantity', 1)
            item_total = unit_price * quantity

            quote_items.append({
                'description': self._format_description(item),
                'unit_price': unit_price,
                'quantity': quantity,
                'total': item_total,
                'notes': item.get('notes', ''),
            })

            total += item_total

        return {
            'manager_price_id': self.id,
            'client': self.client.name,
            'manager': self.manager.get_full_name(),
            'date': timezone.now().date().isoformat(),
            'items': quote_items,
            'subtotal': total,
            'total': total,  # можно добавить НДС и т.д.
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
        }

    def _format_description(self, item):
        """Форматирует описание позиции"""
        descriptions = {
            'door_1': 'Дверь 1-створчатая',
            'door_2': 'Дверь 2-створчатая',
            'hatch_1': 'Люк',
            'gate': 'Ворота',
            'big_gate': 'Ворота большие',
            'not_standard': 'Нестандартное изделие',
        }

        fire_rating_desc = {
            'teh': 'Технические',
            'ei60': 'EI 60',
            'eis60': 'EIS 60',
        }

        category = descriptions.get(item['category'], item['category'])
        fire_rating = fire_rating_desc.get(item['fire_rating'], item['fire_rating'])

        return f"{category} {fire_rating}"


# Утилитарные модели
class Client(models.Model):
    """Клиент"""
    name = models.CharField('Название', max_length=200)
    contact_person = models.CharField('Контактное лицо', max_length=200, blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    email = models.EmailField('Email', blank=True)

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'

    def __str__(self):
        return self.name





