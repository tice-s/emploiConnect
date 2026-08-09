from django.db import models


class InterviewSession(models.Model):
    """Une session de préparation d'entretien pour un poste donné (texte, V1)."""

    candidate = models.ForeignKey(
        "candidates.CandidateProfile", on_delete=models.CASCADE, related_name="interview_sessions"
    )
    job = models.ForeignKey(
        "jobs.JobOffer", on_delete=models.SET_NULL, null=True, blank=True, related_name="interview_sessions"
    )
    company_name = models.CharField(max_length=150, blank=True)
    position_title = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Synthèse globale renvoyée par l'IA une fois toutes les réponses soumises
    overall_feedback = models.TextField(blank=True)
    confidence_score = models.PositiveSmallIntegerField(null=True, blank=True)
    communication_score = models.PositiveSmallIntegerField(null=True, blank=True)
    technical_score = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Entretien {self.position_title or 'poste'} - {self.candidate}"

    @property
    def is_completed(self):
        return self.completed_at is not None


class InterviewQuestion(models.Model):
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveSmallIntegerField(default=0)
    question_text = models.TextField()
    category = models.CharField(max_length=100, blank=True, help_text="Ex: comportemental, technique, motivation")

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.question_text[:80]


class InterviewAnswer(models.Model):
    question = models.OneToOneField(InterviewQuestion, on_delete=models.CASCADE, related_name="answer")
    answer_text = models.TextField()
    ai_feedback = models.TextField(blank=True)
    relevance_score = models.PositiveSmallIntegerField(null=True, blank=True)
    structure_score = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Réponse à: {self.question}"
