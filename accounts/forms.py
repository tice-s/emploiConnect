from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    """Inscription — le rôle détermine tout le parcours ensuite."""

    email = forms.EmailField(required=True, label="Adresse e-mail")
    first_name = forms.CharField(required=True, label="Prénom")
    last_name = forms.CharField(required=True, label="Nom")
    role = forms.ChoiceField(choices=User.Role.choices, widget=forms.RadioSelect, label="Je suis un(e)")
    phone = forms.CharField(required=False, label="Téléphone")

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "role", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Un compte existe déjà avec cette adresse e-mail.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Adresse e-mail")
