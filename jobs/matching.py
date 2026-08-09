"""
Pré-filtrage local (sans appel IA) utilisé uniquement pour les suggestions du
tableau de bord — rapide et gratuit. Le score de compatibilité affiché lors
d'une candidature reste toujours celui, plus fin, calculé par
ai_engine.services.compute_match (voir jobs.views.compute_my_match et
applications.views.apply_to_job).
"""
from django.db.models import Count


def quick_overlap_score(candidate_skill_names: set[str], job) -> int:
    required = {js.skill.name.lower() for js in job.required_skills.all()}
    if not required:
        return 50  # score neutre si l'offre n'a pas encore de compétences renseignées
    matched = candidate_skill_names & required
    return round(100 * len(matched) / len(required))


def suggest_jobs_for_candidate(profile, limit: int = 5):
    """Suggestions automatiques : offres publiées les plus proches du profil, même
    si le candidat n'a pas cherché ce type de poste (cf. cahier des charges)."""
    from .models import JobOffer

    candidate_skill_names = {cs.skill.name.lower() for cs in profile.candidate_skills.all()}
    jobs = (
        JobOffer.objects.filter(status=JobOffer.Status.PUBLISHED)
        .exclude(applications__candidate=profile)
        .prefetch_related("required_skills__skill")
        .annotate(n_skills=Count("required_skills"))
    )
    scored = [(job, quick_overlap_score(candidate_skill_names, job)) for job in jobs]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]
