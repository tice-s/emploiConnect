import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView

from ai_engine.services import AIServiceError, check_profile_consistency, compute_match
from jobs.models import JobOffer
from .models import Application

logger = logging.getLogger("ai_engine")


def _build_candidate_summary(profile) -> str:
    experiences = "; ".join(f"{e.title} chez {e.company}" for e in profile.experiences.all()[:5])
    educations = "; ".join(f"{e.degree} ({e.institution})" for e in profile.educations.all()[:3])
    return (
        f"Ville: {profile.city or 'N/A'}. Niveau d'études: {profile.get_education_level_display() or 'N/A'}. "
        f"Expériences: {experiences or 'aucune renseignée'}. Formations: {educations or 'aucune renseignée'}. "
        f"À propos: {profile.bio or 'non renseigné'}."
    )


@login_required
def apply_to_job(request, pk):
    job = get_object_or_404(JobOffer, pk=pk, status=JobOffer.Status.PUBLISHED)

    if not request.user.is_candidate or not hasattr(request.user, "candidate_profile"):
        messages.error(request, "Seul un compte candidat peut postuler.")
        return redirect("jobs:detail", pk=pk)

    profile = request.user.candidate_profile
    if Application.objects.filter(job=job, candidate=profile).exists():
        messages.info(request, "Vous avez déjà postulé à cette offre.")
        return redirect("jobs:detail", pk=pk)

    if request.method != "POST":
        return redirect("jobs:detail", pk=pk)

    candidate_skills = [cs.skill.name for cs in profile.candidate_skills.all()]
    years_experience = sum((e.duration_years or 0) for e in profile.experiences.all())

    try:
        match_result = compute_match(
            candidate_skills=candidate_skills,
            candidate_years_experience=years_experience,
            candidate_education_level=profile.get_education_level_display() if profile.education_level else "",
            job_title=job.title,
            job_description=job.description,
            required_skills=[js.skill.name for js in job.required_skills.all()],
            mandatory_skills=[js.skill.name for js in job.mandatory_skills],
            required_years_experience=job.experience_years_required,
            required_education_level=job.get_education_level_required_display() if job.education_level_required else "",
            user=request.user,
        )
    except AIServiceError as exc:
        messages.error(request, f"Candidature impossible pour le moment : {exc}")
        return redirect("jobs:detail", pk=pk)

    application = Application.objects.create(
        job=job,
        candidate=profile,
        match_score=match_result.get("score", 0),
        match_explanation=match_result,
    )

    # Vérification de cohérence (non bloquante — signale, ne conclut jamais à une fraude)
    try:
        consistency = check_profile_consistency(profile_summary=_build_candidate_summary(profile), user=request.user)
        if consistency.get("needs_review"):
            application.fraud_flag = True
            application.fraud_reason = consistency.get("reason", "")
            application.save(update_fields=["fraud_flag", "fraud_reason"])
    except AIServiceError:
        logger.warning("Vérification de cohérence indisponible pour la candidature %s", application.pk)

    messages.success(
        request,
        f"Candidature envoyée ! Votre score de compatibilité pour ce poste est de {application.match_score}%.",
    )
    return redirect("applications:my_list")


class MyApplicationsListView(LoginRequiredMixin, ListView):
    template_name = "applications/my_list.html"
    context_object_name = "applications"

    def get_queryset(self):
        profile = getattr(self.request.user, "candidate_profile", None)
        if not profile:
            return Application.objects.none()
        return Application.objects.filter(candidate=profile).select_related("job__company")


class ApplicationDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Application
    template_name = "applications/detail.html"
    context_object_name = "application"

    def test_func(self):
        application = self.get_object()
        user = self.request.user
        if user.is_candidate:
            return hasattr(user, "candidate_profile") and application.candidate_id == user.candidate_profile.id
        if user.is_recruiter and hasattr(user, "recruiter_profile"):
            return application.job.company_id == user.recruiter_profile.company_id
        return False


@login_required
def update_application_status(request, pk):
    application = get_object_or_404(Application, pk=pk)
    user = request.user
    if not (user.is_recruiter and hasattr(user, "recruiter_profile")
            and application.job.company_id == user.recruiter_profile.company_id):
        messages.error(request, "Action non autorisée.")
        return redirect("dashboard:redirect")

    new_status = request.POST.get("status")
    valid_statuses = dict(Application.Status.choices)
    if request.method == "POST" and new_status in valid_statuses:
        application.status = new_status
        application.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Statut mis à jour : {valid_statuses[new_status]}")
    return redirect("jobs:candidates", pk=application.job_id)
