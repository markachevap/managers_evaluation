from django.contrib import admin
from django import forms
from .models import User


class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = '__all__'

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Email already exists")
        return email


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm