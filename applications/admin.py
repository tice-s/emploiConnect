from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("candidate", "job", "status", "match_score", "fraud_flag", "applied_at")
    list_filter = ("status", "fraud_flag")
    search_fields = ("candidate__user__email", "job__title")
