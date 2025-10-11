# accounts/urls.py
from django.urls import path, include
from .views import RegisterView
from django.contrib.auth import views as auth_views

app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(template_name="registration/login.html"), name="logout"),
]
