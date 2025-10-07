from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Infos supplémentaires", {"fields": ("phone", "address")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Infos supplémentaires", {"fields": ("phone", "address")}),
    )
