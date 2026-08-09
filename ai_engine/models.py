from django.conf import settings
from django.db import models


class AIInteractionLog(models.Model):
    """Journal des appels IA (audit, suivi des coûts, débogage)."""

    class Kind(models.TextChoices):
        CV_EXTRACTION = "cv_extraction", "Extraction de CV"
        CV_GENERATION = "cv_generation", "Génération de CV"
        COVER_LETTER = "cover_letter", "Lettre de motivation"
        MATCHING = "matching", "Explication de matching"
        INTERVIEW_QUESTIONS = "interview_questions", "Questions d'entretien"
        INTERVIEW_FEEDBACK = "interview_feedback", "Analyse de réponse"
        LEARNING_PLAN = "learning_plan", "Plan de progression"
        FRAUD_CHECK = "fraud_check", "Vérification de cohérence"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    kind = models.CharField(max_length=30, choices=Kind.choices)
    success = models.BooleanField(default=True)
    error_message = models.CharField(max_length=500, blank=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["kind", "created_at"])]

    def __str__(self):
        return f"{self.get_kind_display()} - {self.user} ({'OK' if self.success else 'échec'})"
