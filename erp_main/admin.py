from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.utils.translation import gettext_lazy as _

from erp_main.forms import InternalLegalEntityForm
from erp_main.models import LegalEntity, IndividualEntrepreneur, PhysicalPerson, InternalLegalEntity


class CustomGroupAdmin(GroupAdmin):
    """Кастомный админ для групп с переводом"""
    list_display = ['name', 'id']
    search_fields = ['name']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs


class CustomUserAdmin(UserAdmin):
    """Кастомный админ для пользователей с переводом"""

    # Отображение в списке
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_active', 'is_superuser', 'groups']
    search_fields = ['username', 'first_name', 'last_name', 'email']

    # Порядок полей в формах
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Персональная информация'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Права доступа'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Важные даты'), {'fields': ('last_login', 'date_joined')}),
    )

    # Поля при создании пользователя
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'first_name', 'last_name'),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs


@admin.register(InternalLegalEntity)
class InternalLegalEntityAdmin(admin.ModelAdmin):
    form = InternalLegalEntityForm
    list_display = ['type', 'name', 'inn', 'ogrn', 'email']
    search_fields = ['name', 'inn', 'ogrn', 'ceo_name']

    def get_fieldsets(self, request, obj=None):
        # Для типа WITHOUT_INVOICE показываем только тип
        if obj and obj.type == 'WITHOUT_INVOICE':
            return (
                ('Основная информация', {
                    'fields': ('type',)
                }),
            )

        # Для INDIVIDUAL
        elif obj and obj.type == 'INDIVIDUAL':
            return (
                ('Основная информация', {
                    'fields': ('type', 'ceo_name', 'inn', 'ogrn', 'legal_address')
                }),
                ('Контактная информация', {
                    'fields': ('email',)
                }),
                ('Банковские реквизиты', {
                    'fields': ('bank_name', 'account_number', 'bik', 'correspondent_account')
                }),
            )

        # Для LEGAL (и по умолчанию для новых объектов)
        else:
            return (
                ('Основная информация', {
                    'fields': ('type', 'name', 'inn', 'ogrn', 'kpp', 'legal_address')
                }),
                ('Контактная информация', {
                    'fields': ('email', 'postal_address')
                }),
                ('Руководитель', {
                    'fields': ('ceo_title', 'ceo_name')
                }),
                ('Банковские реквизиты', {
                    'fields': ('bank_name', 'account_number', 'bik', 'correspondent_account')
                }),
            )

    def save_model(self, request, obj, form, change):
        """Кастомная логика сохранения модели"""
        # Можно добавить дополнительную логику перед сохранением
        if not change:  # Если это создание нового объекта
            # Например, логирование кто создал
            pass

        # Автоматическое заполнение некоторых полей при необходимости
        if obj.type == 'INDIVIDUAL' and not obj.name:
            obj.name = f"ИП {obj.ceo_name}"

        super().save_model(request, obj, form, change)
    class Media:
        js = ('admin/js/internal_legal_entity.js',)

@admin.register(LegalEntity)
class LegalEntityAdmin(admin.ModelAdmin):
    list_display = ['name', 'legal_form', 'inn', 'internal_legal_entity', 'user', 'created_at']
    list_filter = ['legal_form', 'internal_legal_entity', 'created_at']
    search_fields = ['name', 'inn', 'ogrn']
    readonly_fields = ['history']

@admin.register(IndividualEntrepreneur)
class IndividualEntrepreneurAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'inn', 'internal_legal_entity', 'user', 'created_at']
    list_filter = ['internal_legal_entity', 'created_at']
    search_fields = ['full_name', 'inn', 'ogrnip']
    readonly_fields = ['history']

@admin.register(PhysicalPerson)
class PhysicalPersonAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone', 'user', 'created_at']
    search_fields = ['full_name', 'phone']
    readonly_fields = ['history']

# Сначала отменяем стандартную регистрацию
admin.site.unregister(Group)
admin.site.unregister(User)

# Регистрируем с кастомными админами
admin.site.register(Group, CustomGroupAdmin)
admin.site.register(User, CustomUserAdmin)

# Изменяем названия моделей в интерфейсе
Group._meta.verbose_name = _('Отдел')
Group._meta.verbose_name_plural = _('Отделы')

User._meta.verbose_name = _('Сотрудник')
User._meta.verbose_name_plural = _('Сотрудники')
