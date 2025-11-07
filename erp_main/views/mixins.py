from django.contrib.auth.mixins import LoginRequiredMixin
from ..models import Organization


class UserAccessMixin(LoginRequiredMixin):
    """Миксин для проверки доступа пользователя к организациям"""

    def get_user_organizations(self):
        user = self.request.user
        if user.is_superuser:
            return Organization.objects.all()
        return Organization.objects.filter(user=user)