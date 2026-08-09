from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, render
from django.views.generic import DetailView, UpdateView

from accounts.models import User
from .forms import CompanyForm
from .models import Company, Recruiter


def _require_recruiter(request):
    return request.user.is_authenticated and request.user.role == User.Role.RECRUITER


@login_required
def onboarding(request):
    """Un recruteur sans entreprise doit en créer une (ou en rejoindre une existante) avant de publier."""
    if not _require_recruiter(request):
        messages.error(request, "Cette section est réservée aux recruteurs.")
        return redirect("dashboard:redirect")

    if Recruiter.objects.filter(user=request.user).exists():
        return redirect("dashboard:redirect")

    if request.method == "POST":
        form = CompanyForm(request.POST, request.FILES)
        if form.is_valid():
            existing = Company.objects.filter(name__iexact=form.cleaned_data["name"]).first()
            if existing:
                Recruiter.objects.create(user=request.user, company=existing)
                messages.success(request, f"Vous avez rejoint l'entreprise {existing.name}.")
            else:
                company = form.save()
                Recruiter.objects.create(user=request.user, company=company, is_company_admin=True)
                messages.success(request, "Entreprise créée avec succès.")
            return redirect("dashboard:redirect")
    else:
        form = CompanyForm()
    return render(request, "companies/onboarding.html", {"form": form})


class CompanyDetailView(DetailView):
    model = Company
    template_name = "companies/detail.html"
    context_object_name = "company"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["job_offers"] = self.object.job_offers.filter(status="published")
        return ctx


class CompanyUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "companies/edit.html"

    def test_func(self):
        return Recruiter.objects.filter(user=self.request.user, company=self.get_object()).exists()

    def get_success_url(self):
        messages.success(self.request, "Profil entreprise mis à jour.")
        return self.object.get_absolute_url()
