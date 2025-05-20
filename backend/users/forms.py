from django.contrib.auth import get_user_model
from .models import CustomRole
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.forms import UserCreationForm



User = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
        required=True
    )
    first_name = forms.CharField(
        label='Имя',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'}),
        required=True
    )
    last_name = forms.CharField(
        label='Фамилия',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'}),
        required=True
    )
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Логин'}),
        required=True
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует")
        return email


class EmailAuthForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autofocus': True})
    )


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label=_("Password"),
        required=True
    )
    password_confirmation = forms.CharField(
        widget=forms.PasswordInput,
        label=_("Password Confirmation"),
        required=True
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'hire_date', 'position', 'password', 'password_confirmation']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirmation = cleaned_data.get('password_confirmation')

        if password and password_confirmation and password != password_confirmation:
            raise forms.ValidationError("Пароли не совпадают")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.system_role = User.SYSTEM_MANAGER  # Устанавливаем роль здесь
        if commit:
            user.save()
        return user


class CustomRoleForm(forms.ModelForm):
    class Meta:
        model = CustomRole
        fields = ['name', 'description']
        labels = {
            'name': _('Name'),
            'description': _('Description'),
        }

    def __init__(self, *args, creator=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.creator = creator

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.created_by = self.creator
        if commit:
            instance.save()
        return instance


class AssignRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['custom_role']
        labels = {
            'custom_role': _('Custom Role'),
        }

    def __init__(self, *args, leader=None, **kwargs):
        super().__init__(*args, **kwargs)
        if leader:
            self.fields['custom_role'].queryset = CustomRole.objects.filter(created_by=leader)


class UserProfileForm(forms.ModelForm):
    current_password = forms.CharField(
        label='Текущий пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )
    new_password = forms.CharField(
        label='Новый пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )
    confirm_password = forms.CharField(
        label='Подтвердите новый пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        current_password = cleaned_data.get('current_password')

        if new_password or confirm_password or current_password:
            if not current_password:
                raise forms.ValidationError("Для смены пароля необходимо ввести текущий пароль")

            if not self.instance.check_password(current_password):
                raise forms.ValidationError("Текущий пароль введен неверно")

            if new_password != confirm_password:
                raise forms.ValidationError("Новые пароли не совпадают")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')

        if new_password:
            user.set_password(new_password)

        if commit:
            user.save()

        return user

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email уже существует")
        return email
