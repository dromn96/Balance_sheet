from django.shortcuts import render, redirect
from django.contrib.auth import login as login_func, logout as logout_func, get_user_model, authenticate
from .forms import *

from core.models import Profile

def login(request):
    form = LoginForm()
    if request.method == 'POST':
        # передача данных из __init__ из forms
        form = LoginForm(request, request.POST)
        if form.is_valid():
            user = form.get_user()
            login_func(request, user)
            return redirect('/')

    context = {'form': form}
    return render(request, 'users/login.html', context)

def logout(request):
    logout_func(request)
    return redirect('/')

def register(request):
    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # Создание нового пользователя
            User = get_user_model()
            new_user = User(username=data['username'])
            new_user.set_password(data['password1'])
            new_user.save()

            Profile.objects.create(user=new_user)

            #  Логиним пользователя на сайте
            user = authenticate(request, username=new_user.username, password=data['password1'])
            login_func(request, user)

            return redirect('/')

    context = {'form': form}
    return render(request, 'users/register.html', context)

