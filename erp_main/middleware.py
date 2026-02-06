# erp_main/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import get_token, rotate_token


class ForceCSRFRefreshMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Если пользователь заходит на страницу логина после выхода
        if request.path == '/login/' and request.method == 'GET':
            # Принудительно обновляем CSRF токен
            if not request.user.is_authenticated:
                rotate_token(request)
                get_token(request)

        # Если это запрос для получения CSRF токена
        if request.path == '/refresh-csrf/':
            rotate_token(request)

        return None

    def process_response(self, request, response):
        # Убедимся, что CSRF кука всегда установлена
        if hasattr(request, 'csrf_token'):
            if not request.COOKIES.get('csrftoken'):
                response.set_cookie(
                    'csrftoken',
                    request.csrf_token,
                    max_age=31449600,
                    httponly=False,
                    samesite='Lax'
                )

        return response