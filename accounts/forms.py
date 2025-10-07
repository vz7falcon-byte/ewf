from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser  # IMPORTANT: Changez User en CustomUser

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser  # Changez User en CustomUser
        fields = ("username", "email", "phone", "password1", "password2")