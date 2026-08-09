"""
Modèles du profil candidat : profil principal, parcours (diplômes,
expériences), compétences, langues, CV importé/généré et lettres de
motivation. Conçu pour être rempli soit manuellement, soit automatiquement
par l'IA à partir d'un CV importé (voir ai_engine.services.extract_cv_data).
"""
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


def cv_upload_path(instance, filename):
    return f"cv/{instance.user_id}/{filename}"


def photo_upload_path(instance, filename):
    return f"photos/{instance.user_id}/{filename}"


class CandidateProfile(models.Model):
    class EducationLevel(models.TextChoices):
        SECONDAIRE = "secondaire", "Secondaire"
        BAC = "bac", "Baccalauréat"
        BAC2 = "bac2", "Bac+2 (BTS/DUT)"
        LICENCE = "licence", "Licence / Bac+3"
        MASTER = "master", "Master / Bac+5"
        DOCTORAT = "doctorat", "Doctorat"

    class Availability(models.TextChoices):
        IMMEDIATE = "immediate", "Disponible immédiatement"
        UN_MOIS = "1_mois", "Sous 1 mois"
        TROIS_MOIS = "3_mois", "Sous 3 mois"
        NEGOCIABLE = "negociable", "À négocier"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="candidate_profile")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    birth_date = models.DateField(null=True, blank=True)
    education_level = models.CharField(max_length=20, choices=EducationLevel.choices, blank=True)
    headline = models.CharField(max_length=150, blank=True, help_text="Ex: Développeur Backend Django")
    bio = models.TextField(blank=True, verbose_name="À propos")
    desired_salary = models.PositiveIntegerField(null=True, blank=True, help_text="Salaire mensuel souhaité (FCFA)")
    availability = models.CharField(max_length=20, choices=Availability.choices, default=Availability.NEGOCIABLE)
    photo = models.ImageField(upload_to=photo_upload_path, blank=True, null=True)
    cv_file = models.FileField(
        upload_to=cv_upload_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "docx"])],
        help_text="CV importé (PDF ou DOCX, 5 Mo max)",
    )
    cv_imported_at = models.DateTimeField(null=True, blank=True)
    profile_completeness = models.PositiveSmallIntegerField(default=0, help_text="Score de complétude du profil (0-100)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil candidat"
        verbose_name_plural = "Profils candidats"

    def __str__(self):
        return f"Profil de {self.user}"

    def compute_completeness(self):
        """Recalcule un score simple de complétude du profil (utilisé par le dashboard)."""
        fields_weights = [
            (bool(self.city), 10),
            (bool(self.education_level), 10),
            (bool(self.bio), 10),
            (bool(self.photo), 5),
            (self.experiences.exists(), 20),
            (self.candidate_skills.exists(), 20),
            (self.candidate_languages.exists(), 10),
            (bool(self.cv_file), 15),
        ]
        score = sum(weight for present, weight in fields_weights if present)
        self.profile_completeness = min(score, 100)
        self.save(update_fields=["profile_completeness"])
        return self.profile_completeness


class Education(models.Model):
    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="educations")
    degree = models.CharField(max_length=150, verbose_name="Diplôme")
    institution = models.CharField(max_length=150, verbose_name="Établissement")
    field_of_study = models.CharField(max_length=150, blank=True, verbose_name="Domaine d'étude")
    start_year = models.PositiveSmallIntegerField(null=True, blank=True)
    end_year = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-end_year", "-start_year"]

    def __str__(self):
        return f"{self.degree} - {self.institution}"


class Experience(models.Model):
    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="experiences")
    title = models.CharField(max_length=150, verbose_name="Poste")
    company = models.CharField(max_length=150, verbose_name="Entreprise")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False, verbose_name="Poste actuel")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-is_current", "-start_date"]

    def __str__(self):
        return f"{self.title} chez {self.company}"

    @property
    def duration_years(self):
        from datetime import date
        end = self.end_date or date.today()
        if not self.start_date:
            return None
        return round((end - self.start_date).days / 365.25, 1)


class Skill(models.Model):
    """Catalogue global de compétences (partagé avec les offres d'emploi pour le matching)."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CandidateSkill(models.Model):
    class Level(models.TextChoices):
        DEBUTANT = "debutant", "Débutant"
        INTERMEDIAIRE = "intermediaire", "Intermédiaire"
        AVANCE = "avance", "Avancé"
        EXPERT = "expert", "Expert"

    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="candidate_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="candidate_links")
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.INTERMEDIAIRE)

    class Meta:
        unique_together = ("profile", "skill")

    def __str__(self):
        return f"{self.skill} ({self.get_level_display()})"


class Language(models.Model):
    name = models.CharField(max_length=60, unique=True)

    def __str__(self):
        return self.name


class CandidateLanguage(models.Model):
    class Level(models.TextChoices):
        A1 = "A1", "A1 - Débutant"
        A2 = "A2", "A2 - Élémentaire"
        B1 = "B1", "B1 - Intermédiaire"
        B2 = "B2", "B2 - Intermédiaire avancé"
        C1 = "C1", "C1 - Avancé"
        C2 = "C2", "C2 - Bilingue / natif"

    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="candidate_languages")
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    level = models.CharField(max_length=2, choices=Level.choices, default=Level.B1)

    class Meta:
        unique_together = ("profile", "language")

    def __str__(self):
        return f"{self.language} ({self.level})"


class GeneratedCV(models.Model):
    """
    CV généré à partir du profil, dans un style et une palette de couleurs
    choisis par le candidat. Rendu par gabarit Django (instantané, fiable) —
    voir candidates.cv_themes et candidates.views.render_cv_html.

    Les styles et couleurs disponibles sont définis dans candidates.cv_themes
    (source unique) plutôt que dupliqués ici, pour pouvoir en ajouter sans
    toucher au modèle.
    """

    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="generated_cvs")
    style = models.CharField(max_length=30, default="moderne")
    theme = models.CharField(max_length=30, default="cote_ivoire")
    content_html = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def get_style_display(self):
        from .cv_themes import STYLES

        return STYLES.get(self.style, {}).get("label", self.style)

    def get_theme_display(self):
        from .cv_themes import THEMES

        return THEMES.get(self.theme, {}).get("label", self.theme)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"CV {self.get_style_display()} - {self.profile.user}"


class CoverLetter(models.Model):
    """Lettre de motivation générée par l'IA, personnalisée pour une offre précise."""

    profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="cover_letters")
    job = models.ForeignKey("jobs.JobOffer", on_delete=models.SET_NULL, null=True, blank=True, related_name="cover_letters")
    company_name = models.CharField(max_length=150, blank=True)
    position_title = models.CharField(max_length=150, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Lettre pour {self.position_title or 'poste'} - {self.profile.user}"
