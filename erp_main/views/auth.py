from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse

def custom_login(request):
    if request.method == 'GET':
        next_url = request.GET.get('next', '')
        return render(request, 'registration/login.html', {'next': next_url})

    username = request.POST.get('username')
    password = request.POST.get('password')
    next_url = request.POST.get('next', '')

    user = authenticate(request, username=username, password=password)

    if user is None:
        return render(request, 'registration/login.html', {
            'error': 'Неверные имя пользователя или пароль',
            'next': next_url,
        })

    if not user.is_active:
        return render(request, 'registration/login.html', {
            'error': 'Ваш аккаунт деактивирован',
            'next': next_url,
        })

    login(request, user)

    if next_url and url_has_allowed_host_and_scheme(url=next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect(reverse('index'))