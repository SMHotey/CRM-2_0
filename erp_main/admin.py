from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.utils.translation import gettext_lazy as _
from erp_main.models import Organization


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


# Сначала отменяем стандартную регистрацию
admin.site.unregister(Group)
admin.site.unregister(User)

# Регистрируем с кастомными админами
admin.site.register(Group, CustomGroupAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Organization)

# Изменяем названия моделей в интерфейсе
Group._meta.verbose_name = _('Отдел')
Group._meta.verbose_name_plural = _('Отделы')

User._meta.verbose_name = _('Сотрудник')
User._meta.verbose_name_plural = _('Сотрудники')
