from django.contrib import admin

from .models import JobAlert, JobOffer, JobRequiredSkill


class JobRequiredSkillInline(admin.TabularInline):
    model = JobRequiredSkill
    extra = 1


@admin.register(JobOffer)
class JobOfferAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "contract_type", "status", "applications_count", "created_at")
    list_filter = ("status", "contract_type", "remote_type")
    search_fields = ("title", "company__name")
    inlines = [JobRequiredSkillInline]


@admin.register(JobAlert)
class JobAlertAdmin(admin.ModelAdmin):
    list_display = ("candidate", "job", "match_score", "is_read", "created_at")
    list_filter = ("is_read",)
