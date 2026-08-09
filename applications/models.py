from django.db import models


class Application(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Soumise"
        REVIEWED = "reviewed", "Consultée par le recruteur"
        SHORTLISTED = "shortlisted", "Présélectionnée"
        INTERVIEW = "interview", "Entretien planifié"
        REJECTED = "rejected", "Non retenue"
        HIRED = "hired", "Recrutée"

    job = models.ForeignKey("jobs.JobOffer", on_delete=models.CASCADE, related_name="applications")
    candidate = models.ForeignKey(
        "candidates.CandidateProfile", on_delete=models.CASCADE, related_name="applications"
    )
    cover_letter = models.ForeignKey(
        "candidates.CoverLetter", on_delete=models.SET_NULL, null=True, blank=True, related_name="applications"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)

    # Résultat du matching IA au moment de la candidature (voir ai_engine.services.compute_match)
    match_score = models.PositiveSmallIntegerField(default=0, help_text="Score de compatibilité (0-100)")
    match_explanation = models.JSONField(
        default=dict,
        blank=True,
        help_text="Détail structuré : compétences présentes/manquantes, conseils",
    )
    fraud_flag = models.BooleanField(default=False, help_text="Incohérence détectée à vérifier manuellement")
    fraud_reason = models.CharField(max_length=255, blank=True)

    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Candidature"
        verbose_name_plural = "Candidatures"
        unique_together = ("job", "candidate")
        ordering = ["-match_score", "-applied_at"]
        indexes = [models.Index(fields=["job", "status"])]

    def __str__(self):
        return f"{self.candidate} -> {self.job} ({self.match_score}%)"
