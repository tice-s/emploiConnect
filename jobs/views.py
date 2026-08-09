import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.models import User
from ai_engine.services import AIServiceError, compute_match
from candidates.models import Skill
from companies.models import Recruiter
from .forms import JobOfferForm, JobSearchForm
from .models import JobOffer, JobRequiredSkill

logger = logging.getLogger("ai_engine")


class JobListView(ListView):
    model = JobOffer
    template_name = "jobs/list.html"
    context_object_name = "jobs"
    paginate_by = 10

    def get_queryset(self):
        qs = JobOffer.objects.filter(status=JobOffer.Status.PUBLISHED).select_related("company")
        form = JobSearchForm(self.request.GET or None)
        if form.is_valid():
            data = form.cleaned_data
            if data.get("q"):
                qs = qs.filter(
                    Q(title__icontains=data["q"])
                    | Q(description__icontains=data["q"])
                    | Q(required_skills__skill__name__icontains=data["q"])
                ).distinct()
            if data.get("contract_type"):
                qs = qs.filter(contract_type=data["contract_type"])
            if data.get("remote_type"):
                qs = qs.filter(remote_type=data["remote_type"])
            if data.get("location"):
                qs = qs.filter(location__icontains=data["location"])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["form"] = JobSearchForm(self.request.GET or None)
        return ctx


class JobDetailView(DetailView):
    model = JobOffer
    template_name = "jobs/detail.html"
    context_object_name = "job"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["already_applied"] = False
        if user.is_authenticated and user.is_candidate and hasattr(user, "candidate_profile"):
            ctx["already_applied"] = self.object.applications.filter(candidate=user.candidate_profile).exists()
            ctx["match_result"] = self.request.session.get(f"match_{self.object.pk}_{user.pk}")
        return ctx


def compute_my_match(request, pk):
    """Calcule (et met en cache en session) le score de compatibilité IA pour l'offre."""
    job = get_object_or_404(JobOffer, pk=pk, status=JobOffer.Status.PUBLISHED)
    if not (request.user.is_authenticated and request.user.is_candidate and hasattr(request.user, "candidate_profile")):
        messages.error(request, "Connectez-vous avec un compte candidat pour voir votre compatibilité.")
        return redirect("jobs:detail", pk=pk)

    profile = request.user.candidate_profile
    try:
        result = compute_match(
            candidate_skills=[cs.skill.name for cs in profile.candidate_skills.all()],
            candidate_years_experience=sum(
                (e.duration_years or 0) for e in profile.experiences.all()
            ),
            candidate_education_level=profile.get_education_level_display() if profile.education_level else "",
            job_title=job.title,
            job_description=job.description,
            required_skills=[js.skill.name for js in job.required_skills.all()],
            mandatory_skills=[js.skill.name for js in job.mandatory_skills],
            required_years_experience=job.experience_years_required,
            required_education_level=job.get_education_level_required_display() if job.education_level_required else "",
            user=request.user,
        )
        request.session[f"match_{job.pk}_{request.user.pk}"] = result
    except AIServiceError as exc:
        messages.error(request, str(exc))
    return redirect("jobs:detail", pk=pk)


def _require_recruiter_with_company(request):
    if not (request.user.is_authenticated and request.user.role == User.Role.RECRUITER):
        return None
    return Recruiter.objects.filter(user=request.user).select_related("company").first()


class RecruiterJobMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        self.recruiter = _require_recruiter_with_company(self.request)
        return self.recruiter is not None

    def handle_no_permission(self):
        messages.error(self.request, "Vous devez être un recruteur rattaché à une entreprise.")
        return redirect("companies:onboarding")


class JobCreateView(RecruiterJobMixin, CreateView):
    model = JobOffer
    form_class = JobOfferForm
    template_name = "jobs/form.html"

    def form_valid(self, form):
        form.instance.company = self.recruiter.company
        form.instance.created_by = self.recruiter
        response = super().form_valid(form)
        _sync_skills(self.object, form)
        messages.success(self.request, "Offre enregistrée avec succès.")
        return response


class JobUpdateView(RecruiterJobMixin, UpdateView):
    model = JobOffer
    form_class = JobOfferForm
    template_name = "jobs/form.html"

    def get_queryset(self):
        return JobOffer.objects.filter(company=self.recruiter.company) if hasattr(self, "recruiter") else JobOffer.objects.none()

    def test_func(self):
        ok = super().test_func()
        if not ok:
            return False
        job = self.get_object()
        return job.company_id == self.recruiter.company_id

    def form_valid(self, form):
        response = super().form_valid(form)
        _sync_skills(self.object, form)
        messages.success(self.request, "Offre mise à jour.")
        return response


def _sync_skills(job: JobOffer, form: JobOfferForm):
    JobRequiredSkill.objects.filter(job=job).delete()
    required_names = form.parse_skill_names(form.cleaned_data.get("skills_required", ""))
    mandatory_names = {n.lower() for n in form.parse_skill_names(form.cleaned_data.get("skills_mandatory", ""))}
    for name in required_names:
        skill = Skill.objects.filter(name__iexact=name).first()
        if skill is None:
            skill = Skill.objects.create(name=name)
        JobRequiredSkill.objects.create(job=job, skill=skill, is_mandatory=name.lower() in mandatory_names)


class RecruiterJobListView(RecruiterJobMixin, ListView):
    model = JobOffer
    template_name = "jobs/recruiter_list.html"
    context_object_name = "jobs"

    def get_queryset(self):
        return JobOffer.objects.filter(company=self.recruiter.company).order_by("-created_at")


class JobCandidatesView(RecruiterJobMixin, DetailView):
    """Classement automatique des candidats pour une offre (cœur du logiciel côté entreprise)."""

    model = JobOffer
    template_name = "jobs/candidates_ranking.html"
    context_object_name = "job"

    def get_queryset(self):
        return JobOffer.objects.filter(company=self.recruiter.company)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["applications"] = self.object.applications.select_related("candidate__user").order_by(
            "-match_score", "-applied_at"
        )
        return ctx
