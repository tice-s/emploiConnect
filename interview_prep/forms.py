from django import forms


class StartInterviewForm(forms.Form):
    job_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    company_name = forms.CharField(label="Entreprise", required=False)
    position_title = forms.CharField(label="Poste visé", required=True)
    job_description = forms.CharField(
        label="Description du poste (si hors plateforme)",
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
    )


class AnswerForm(forms.Form):
    answer_text = forms.CharField(label="Votre réponse", widget=forms.Textarea(attrs={"rows": 5}))
