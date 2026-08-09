from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class JobOffer(models.Model):
    class ContractType(models.TextChoices):
        CDI = "cdi", "CDI"
        CDD = "cdd", "CDD"
        STAGE = "stage", "Stage"
        FREELANCE = "freelance", "Freelance / Prestation"
        ALTERNANCE = "alternance", "Alternance"

    class RemoteType(models.TextChoices):
        PRESENTIEL = "presentiel", "Présentiel"
        HYBRIDE = "hybride", "Hybride"
        TELETRAVAIL = "teletravail", "Télétravail complet"

    class EducationLevel(models.TextChoices):
        AUCUN = "", "Non requis"
        BAC = "bac", "Baccalauréat"
        BAC2 = "bac2", "Bac+2 (BTS/DUT)"
        LICENCE = "licence", "Licence / Bac+3"
        MASTER = "master", "Master / Bac+5"
        DOCTORAT = "doctorat", "Doctorat"

    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        PUBLISHED = "published", "Publiée"
        CLOSED = "closed", "Clôturée"

    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="job_offers")
    created_by = models.ForeignKey(
        "companies.Recruiter", on_delete=models.SET_NULL, null=True, related_name="created_jobs"
    )
    title = models.CharField(max_length=150, verbose_name="Intitulé du poste")
    description = models.TextField()
    responsibilities = models.TextField(blank=True, verbose_name="Missions")
    contract_type = models.CharField(max_length=20, choices=ContractType.choices, default=ContractType.CDI)
    location = models.CharField(max_length=150, blank=True, verbose_name="Lieu")
    remote_type = models.CharField(max_length=20, choices=RemoteType.choices, default=RemoteType.PRESENTIEL)
    salary_min = models.PositiveIntegerField(null=True, blank=True, help_text="FCFA/mois")
    salary_max = models.PositiveIntegerField(null=True, blank=True, help_text="FCFA/mois")
    experience_years_required = models.PositiveSmallIntegerField(default=0)
    education_level_required = models.CharField(max_length=20, choices=EducationLevel.choices, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    skills = models.ManyToManyField("candidates.Skill", through="JobRequiredSkill", related_name="job_offers")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Offre d'emploi"
        verbose_name_plural = "Offres d'emploi"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"{self.title} - {self.company}"

    def get_absolute_url(self):
        return reverse("jobs:detail", kwargs={"pk": self.pk})

    @property
    def is_expired(self):
        return bool(self.expires_at and self.expires_at < timezone.now().date())

    @property
    def mandatory_skills(self):
        return self.required_skills.filter(is_mandatory=True)

    @property
    def applications_count(self):
        return self.applications.count()


class JobRequiredSkill(models.Model):
    job = models.ForeignKey(JobOffer, on_delete=models.CASCADE, related_name="required_skills")
    skill = models.ForeignKey("candidates.Skill", on_delete=models.CASCADE, related_name="required_in_jobs")
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        unique_together = ("job", "skill")

    def __str__(self):
        return f"{self.skill} ({'obligatoire' if self.is_mandatory else 'atout'})"


class JobAlert(models.Model):
    """Alerte quotidienne : nouvelles offres correspondant au profil d'un candidat."""

    candidate = models.ForeignKey(
        "candidates.CandidateProfile", on_delete=models.CASCADE, related_name="job_alerts"
    )
    job = models.ForeignKey(JobOffer, on_delete=models.CASCADE, related_name="alerts")
    match_score = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("candidate", "job")

    def __str__(self):
        return f"Alerte {self.job} pour {self.candidate} ({self.match_score}%)"
