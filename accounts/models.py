"""
Modèle utilisateur central.

Un seul modèle User avec un champ `role` (candidat / recruteur) plutôt que
deux tables séparées : simplifie l'authentification et les permissions
Django natives. candidates.CandidateProfile / companies.Recruiter portent
les données métier spécifiques à chaque rôle (relation one-to-one).
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CANDIDATE = "candidate", "Candidat"
        RECRUITER = "recruiter", "Recruteur"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CANDIDATE)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True)

    # Verrouillage anti brute-force (sans dépendance externe)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_candidate(self):
        return self.role == self.Role.CANDIDATE

    @property
    def is_recruiter(self):
        return self.role == self.Role.RECRUITER


class AuditLogEntry(models.Model):
    """Journal d'audit des actions sensibles (connexion, création, suppression...)."""

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_entries")
    action = models.CharField(max_length=100)
    detail = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["action", "created_at"])]

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.user} - {self.action}"
