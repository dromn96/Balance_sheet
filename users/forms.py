from django import forms
from django.contrib.auth import authenticate, get_user_model

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput())

    def __init__(self,request=None, *args, **kwargs):
       self.request = request
       self.user = None
       # вызов родительского метода init
       super().__init__(*args, *kwargs)
    # Валидация пароля
    def clean(self):
        data = self.cleaned_data
        username = data['username']
        password = data['password']
        # Проверка пароля пользователя
        self.user = authenticate(self.request, username=username, password=password)

        if not self.user:
            raise forms.ValidationError('Неверный логин или пароль')
        return data

    def get_user(self):
        return self.user

class RegisterForm(forms.Form):
    username = forms.CharField()
    password1 = forms.CharField(widget=forms.PasswordInput(), label='пароль')
    password2 = forms.CharField(widget=forms.PasswordInput(), label='повторение пароля')

    def clean_username(self):
       username = self.cleaned_data['username']
       User = get_user_model()
       if User.objects.filter(username=username).exists():
           raise forms.ValidationError('Такой логин уже есть')
       return username

    def clean(self):
        password1 = self.cleaned_data['password1']
        password2 = self.cleaned_data['password2']

        if password1 != password2:
            raise forms.ValidationError('пароли не совпадают')
        return self.cleaned_data