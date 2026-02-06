from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie, csrf_exempt
from django.core.cache import cache
from django.http import JsonResponse, HttpResponse
from django.middleware.csrf import get_token, rotate_token
from django.views.decorators.clickjacking import xframe_options_exempt
import time
import json


@require_GET
@ensure_csrf_cookie
def get_csrf_token_view(request):
    """
    Возвращает CSRF-токен для AJAX запросов
    """
    return JsonResponse({'csrfToken': get_token(request)})


@csrf_protect
@ensure_csrf_cookie
@xframe_options_exempt
def custom_login(request):
    """
    Кастомный вход с правильной обработкой CSRF
    """
    # Всегда генерируем новый токен при GET запросе
    if request.method == 'GET':
        get_token(request)  # Это устанавливает токен в куки

        next_url = request.GET.get('next', '')
        animated = request.GET.get('animated', False)

        response = render(request, 'registration/login.html', {
            'next': next_url,
            'animated': animated,
        })

        # Устанавливаем CSRF куку явно
        response.set_cookie(
            'csrftoken',
            get_token(request),
            max_age=31449600,  # 1 год
            httponly=False,
            samesite='Lax'
        )

        return response

    # POST запрос - обработка входа
    ip_address = get_client_ip(request)
    attempts_key = f"login_attempts_{ip_address}"
    attempts = cache.get(attempts_key, 0)

    if attempts >= 15:
        get_token(request)
        return render(request, 'registration/login.html', {
            'error': 'Превышено максимальное количество попыток. Попробуйте позже.',
            'next': request.POST.get('next', '')
        })

    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    next_url = request.POST.get('next', '')

    if not username or not password:
        cache.set(attempts_key, attempts + 1, timeout=300)
        get_token(request)
        return render(request, 'registration/login.html', {
            'error': 'Пожалуйста, заполните все поля',
            'next': next_url,
        })

    user = authenticate(request, username=username, password=password)

    if user is None:
        attempts += 1
        cache.set(attempts_key, attempts, timeout=300)
        time.sleep(0.3 + (attempts * 0.05))

        get_token(request)
        return render(request, 'registration/login.html', {
            'error': 'Неверные имя пользователя или пароль',
            'next': next_url,
        })

    if not user.is_active:
        get_token(request)
        return render(request, 'registration/login.html', {
            'error': 'Ваш аккаунт деактивирован',
            'next': next_url
        })

    cache.delete(attempts_key)

    # ВХОДИМ в систему
    login(request, user)

    # ПОСЛЕ входа меняем CSRF-токен (это важно!)
    rotate_token(request)
    new_csrf_token = get_token(request)

    # Редирект с установкой нового CSRF токена
    response = redirect(next_url if next_url else reverse('index'))
    response.set_cookie(
        'csrftoken',
        new_csrf_token,
        max_age=31449600,
        httponly=False,
        samesite='Lax'
    )

    return response


@require_POST
@csrf_protect
@ensure_csrf_cookie
def custom_logout(request):
    """
    Кастомный выход с сохранением CSRF
    """
    logout(request)

    # НЕ очищаем всю сессию!
    # Удаляем только данные аутентификации
    for key in list(request.session.keys()):
        if key.startswith('_auth'):
            del request.session[key]

    request.session.modified = True

    # Генерируем новый CSRF токен для следующего входа
    rotate_token(request)
    new_csrf_token = get_token(request)

    response = render(request, 'registration/logged_out.html')
    response.set_cookie(
        'csrftoken',
        new_csrf_token,
        max_age=31449600,
        httponly=False,
        samesite='Lax'
    )

    return response


@require_GET
@ensure_csrf_cookie
def refresh_csrf(request):
    """
    Принудительное обновление CSRF токена
    """
    rotate_token(request)
    new_token = get_token(request)

    response = JsonResponse({'csrfToken': new_token, 'refreshed': True})
    response.set_cookie(
        'csrftoken',
        new_token,
        max_age=31449600,
        httponly=False,
        samesite='Lax'
    )

    return response


def get_client_ip(request):
    """
    Получение реального IP адреса клиента
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip