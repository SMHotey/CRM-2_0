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

    def save_model(self, request, obj, form, change):
        # Важный шаг: используем метод set_password для хэширования
        if form.cleaned_data.get('password'):
            obj.set_password(form.cleaned_data['password'])
        super().save_model(request, obj, form, change)


# Убираем стандартную группу
admin.site.unregister(Group)
admin.site.unregister(User)

# Регистрируем с новым названием
admin.site.register(Group, CustomGroupAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Organization)

# Измените названия на нужные
Group._meta.verbose_name = _('Отдел')
Group._meta.verbose_name_plural = _('Отделы')

User._meta.verbose_name = _('Сотрудник')
User._meta.verbose_name_plural = _('Сотрудники')
