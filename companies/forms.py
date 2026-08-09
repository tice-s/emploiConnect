from django import forms

from .models import Company, Recruiter


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "sector", "description", "logo", "website", "city", "size"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class RecruiterProfileForm(forms.ModelForm):
    class Meta:
        model = Recruiter
        fields = ["position"]
