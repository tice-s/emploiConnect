from django import forms

from .cv_themes import DEFAULT_STYLE, DEFAULT_THEME, style_choices, theme_choices
from .models import CandidateProfile, Education, Experience, GeneratedCV


class CandidateProfileForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = [
            "photo", "headline", "bio", "city", "birth_date",
            "education_level", "desired_salary", "availability",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "birth_date": forms.DateInput(attrs={"type": "date"}),
        }


class CVUploadForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = ["cv_file"]


class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = ["title", "company", "start_date", "end_date", "is_current", "description"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ["degree", "institution", "field_of_study", "start_year", "end_year"]


class SkillsForm(forms.Form):
    skills = forms.CharField(
        label="Compétences",
        help_text="Séparées par des virgules, ex: Django, Python, Git, Linux",
        widget=forms.TextInput(attrs={"placeholder": "Django, Python, Git, Linux"}),
    )


class LanguagesForm(forms.Form):
    languages = forms.CharField(
        label="Langues",
        help_text="Format: Langue:Niveau (A1 à C2), séparées par des virgules. Ex: Français:C2, Anglais:B2",
        widget=forms.TextInput(attrs={"placeholder": "Français:C2, Anglais:B2"}),
    )


class CVGenerationForm(forms.Form):
    style = forms.ChoiceField(
        choices=style_choices(), initial=DEFAULT_STYLE, label="Mise en page",
        widget=forms.RadioSelect,
    )
    theme = forms.ChoiceField(
        choices=theme_choices(), initial=DEFAULT_THEME, label="Palette de couleurs",
        widget=forms.RadioSelect,
    )


class CoverLetterForm(forms.Form):
    job_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    company_name = forms.CharField(label="Entreprise", required=False)
    position_title = forms.CharField(label="Intitulé du poste", required=False)
    job_description = forms.CharField(
        label="Description de l'offre (si hors plateforme)",
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
    )
