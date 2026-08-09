from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuditLogEntry, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ("email", "username", "role", "is_active", "is_staff", "date_joined")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "username", "first_name", "last_name")
    fieldsets = UserAdmin.fieldsets + (
        ("Rôle & sécurité", {"fields": ("role", "phone", "failed_login_attempts", "locked_until")}),
    )


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "ip_address")
    list_filter = ("action",)
    search_fields = ("user__email", "action", "detail")
    readonly_fields = [f.name for f in AuditLogEntry._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
