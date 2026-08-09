from django import forms

from .models import JobOffer


class JobOfferForm(forms.ModelForm):
    skills_required = forms.CharField(
        label="Compétences requises",
        help_text="Séparées par des virgules, ex: Django, Python, PostgreSQL",
        widget=forms.TextInput(attrs={"placeholder": "Django, Python, PostgreSQL"}),
    )
    skills_mandatory = forms.CharField(
        label="Dont compétences obligatoires",
        required=False,
        help_text="Sous-ensemble des compétences ci-dessus, séparées par des virgules",
        widget=forms.TextInput(attrs={"placeholder": "Django, Python"}),
    )

    class Meta:
        model = JobOffer
        fields = [
            "title", "description", "responsibilities", "contract_type", "location",
            "remote_type", "salary_min", "salary_max", "experience_years_required",
            "education_level_required", "status", "expires_at",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "responsibilities": forms.Textarea(attrs={"rows": 4}),
            "expires_at": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["skills_required"].initial = ", ".join(
                s.skill.name for s in self.instance.required_skills.all()
            )
            self.fields["skills_mandatory"].initial = ", ".join(
                s.skill.name for s in self.instance.required_skills.filter(is_mandatory=True)
            )

    @staticmethod
    def parse_skill_names(raw: str) -> list[str]:
        return [s.strip() for s in raw.split(",") if s.strip()]


class JobSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Mot-clé", widget=forms.TextInput(attrs={"placeholder": "Ex: Django, comptable, marketing..."}))
    contract_type = forms.ChoiceField(required=False, choices=[("", "Tous types de contrat")] + list(JobOffer.ContractType.choices))
    remote_type = forms.ChoiceField(required=False, choices=[("", "Tous modes")] + list(JobOffer.RemoteType.choices))
    location = forms.CharField(required=False, label="Lieu")
