from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import redirect, render

from accounts.models import User
from applications.models import Application
from candidates.models import CandidateProfile
from companies.models import Recruiter
from jobs.matching import suggest_jobs_for_candidate
from jobs.models import JobOffer


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard:redirect")
    latest_jobs = JobOffer.objects.filter(status=JobOffer.Status.PUBLISHED).select_related("company").order_by("-created_at")[:6]
    stats = {
        "jobs_count": JobOffer.objects.filter(status=JobOffer.Status.PUBLISHED).count(),
        "companies_count": Recruiter.objects.values("company").distinct().count(),
    }
    return render(request, "dashboard/home.html", {"latest_jobs": latest_jobs, "stats": stats})


@login_required
def redirect_view(request):
    if request.user.is_candidate:
        return redirect("dashboard:candidate")
    if request.user.role == User.Role.RECRUITER:
        if not Recruiter.objects.filter(user=request.user).exists():
            return redirect("companies:onboarding")
        return redirect("dashboard:recruiter")
    return redirect("dashboard:candidate")


@login_required
def candidate_dashboard(request):
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    profile.compute_completeness()

    applications = Application.objects.filter(candidate=profile).select_related("job__company")
    avg_score = applications.aggregate(avg=Avg("match_score"))["avg"] or 0
    suggestions = suggest_jobs_for_candidate(profile)

    context = {
        "profile": profile,
        "applications_count": applications.count(),
        "avg_match_score": round(avg_score),
        "recent_applications": applications.order_by("-applied_at")[:5],
        "suggestions": suggestions,
        "profile_views_count": 0,  # extension future : compteur de consultations par les recruteurs
    }
    return render(request, "dashboard/candidate_dashboard.html", context)


@login_required
def recruiter_dashboard(request):
    recruiter = Recruiter.objects.filter(user=request.user).select_related("company").first()
    if not recruiter:
        return redirect("companies:onboarding")

    jobs = JobOffer.objects.filter(company=recruiter.company).annotate(n_applications=Count("applications"))
    total_applications = Application.objects.filter(job__company=recruiter.company).count()

    top_skills = (
        JobOffer.objects.filter(company=recruiter.company)
        .values("required_skills__skill__name")
        .annotate(n=Count("required_skills__skill"))
        .exclude(required_skills__skill__isnull=True)
        .order_by("-n")[:8]
    )

    context = {
        "company": recruiter.company,
        "jobs": jobs.order_by("-created_at"),
        "total_jobs": jobs.count(),
        "published_jobs": jobs.filter(status=JobOffer.Status.PUBLISHED).count(),
        "total_applications": total_applications,
        "top_skills": top_skills,
    }
    return render(request, "dashboard/recruiter_dashboard.html", context)
