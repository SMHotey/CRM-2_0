# mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from ..models import Organization


class UserAccessMixin(LoginRequiredMixin):
    """Миксин для проверки доступа пользователя к организациям"""

    def get_user_organizations(self):
        user = self.request.user
        if user.is_superuser:
            return Organization.objects.all()
        return Organization.objects.filter(user=user)

    def get_user_role(self):
        """Получаем роль пользователя (можно вынести в отдельный файл)"""
        user = self.request.user
        if user.is_superuser:
            return 'admin'

        # Проверяем группы пользователя
        group_names = user.groups.values_list('name', flat=True)
        role_priority = ['admin', 'director', 'production', 'logistic', 'manager']

        for role in role_priority:
            if role in group_names:
                return role

        return 'user'

    def check_role_permission(self, required_roles):
        """Проверяет, есть ли у пользователя необходимая роль"""
        user_role = self.get_user_role()
        if user_role not in required_roles:
            raise PermissionDenied("У вас недостаточно прав для этого действия")

    def dispatch(self, request, *args, **kwargs):
        """Добавляем проверку роли перед обработкой запроса"""
        if hasattr(self, 'required_roles'):
            self.check_role_permission(self.required_roles)
        return super().dispatch(request, *args, **kwargs)