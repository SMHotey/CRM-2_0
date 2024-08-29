from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.utils.translation import gettext_lazy as _

from erp_main.models import Organization


class CustomGroupAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs


class CustomUserAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs


# Убираем стандартную группу
admin.site.unregister(Group)
admin.site.unregister(User)

# Регистрируем с новым названием
admin.site.register(Group, CustomGroupAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Organization)
# Измените названия на нужные
Group._meta.verbose_name = _('Отдел')  #
Group._meta.verbose_name_plural = _('Отделы')  # Множественное

User._meta.verbose_name = _('Сотрудник')  #
User._meta.verbose_name_plural = _('Сотрудники')  # Множественное