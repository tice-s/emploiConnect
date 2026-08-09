from django.contrib import admin

from .models import Company, Recruiter


class RecruiterInline(admin.TabularInline):
    model = Recruiter
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "sector", "city", "size", "is_verified", "created_at")
    list_filter = ("is_verified", "size", "sector")
    search_fields = ("name", "sector", "city")
    inlines = [RecruiterInline]


@admin.register(Recruiter)
class RecruiterAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "position", "is_company_admin")
    search_fields = ("user__email", "company__name")
