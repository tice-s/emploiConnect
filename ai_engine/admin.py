from django.contrib import admin

from .models import AIInteractionLog


@admin.register(AIInteractionLog)
class AIInteractionLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "user", "success", "input_tokens", "output_tokens")
    list_filter = ("kind", "success")
    search_fields = ("user__email",)

    def has_add_permission(self, request):
        return False
