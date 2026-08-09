from django.contrib import admin

from .models import (
    CandidateLanguage, CandidateProfile, CandidateSkill, CoverLetter,
    Education, Experience, GeneratedCV, Language, Skill,
)


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0


class CandidateSkillInline(admin.TabularInline):
    model = CandidateSkill
    extra = 0


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "city", "education_level", "profile_completeness", "updated_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "city")
    inlines = [ExperienceInline, EducationInline, CandidateSkillInline]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


admin.site.register(Language)
admin.site.register(CandidateLanguage)
admin.site.register(GeneratedCV)
admin.site.register(CoverLetter)
