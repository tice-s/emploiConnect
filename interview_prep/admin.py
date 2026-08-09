from django.contrib import admin

from .models import InterviewAnswer, InterviewQuestion, InterviewSession


class InterviewQuestionInline(admin.TabularInline):
    model = InterviewQuestion
    extra = 0


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ("candidate", "position_title", "company_name", "created_at", "is_completed")
    inlines = [InterviewQuestionInline]


admin.site.register(InterviewAnswer)
