from django.conf import settings
from django.db import models
from django.urls import reverse


def logo_upload_path(instance, filename):
    return f"logos/{instance.id or 'new'}/{filename}"


class Company(models.Model):
    class Size(models.TextChoices):
        TPE = "tpe", "1-9 salariés (TPE)"
        PME = "pme", "10-249 salariés (PME)"
        ETI = "eti", "250-4999 salariés (ETI)"
        GE = "ge", "5000+ salariés (Grande entreprise)"

    name = models.CharField(max_length=150, unique=True, verbose_name="Raison sociale")
    sector = models.CharField(max_length=150, blank=True, verbose_name="Secteur d'activité")
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to=logo_upload_path, blank=True, null=True)
    website = models.URLField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=10, choices=Size.choices, blank=True)
    is_verified = models.BooleanField(default=False, help_text="Vérifiée par un administrateur de la plateforme")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Entreprise"
        verbose_name_plural = "Entreprises"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("companies:detail", kwargs={"pk": self.pk})


class Recruiter(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recruiter_profile")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="recruiters")
    position = models.CharField(max_length=150, blank=True, verbose_name="Fonction")
    is_company_admin = models.BooleanField(default=False, help_text="Peut gérer les autres recruteurs de l'entreprise")

    class Meta:
        verbose_name = "Recruteur"
        verbose_name_plural = "Recruteurs"

    def __str__(self):
        return f"{self.user} - {self.company}"
