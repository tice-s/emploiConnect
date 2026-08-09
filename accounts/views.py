import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView

from .forms import EmailAuthenticationForm, RegisterForm
from .middleware import get_client_ip
from .models import AuditLogEntry, User

logger = logging.getLogger("django.security")


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        AuditLogEntry.objects.create(
            user=self.object, action="inscription", ip_address=get_client_ip(self.request)
        )
        messages.success(self.request, "Compte créé avec succès. Vous pouvez maintenant vous connecter.")
        return response


class RateLimitedLoginView(LoginView):
    """
    Connexion avec verrouillage temporaire après N échecs (protection brute-force),
    sans dépendance externe. Le compteur est stocké sur l'utilisateur lui-même.
    """

    form_class = EmailAuthenticationForm
    template_name = "accounts/login.html"

    def form_valid(self, form):
        user = form.get_user()
        if user.locked_until and user.locked_until > timezone.now():
            messages.error(
                self.request,
                "Compte temporairement verrouillé suite à plusieurs échecs de connexion. Réessayez plus tard.",
            )
            return self.form_invalid(form)

        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_attempts", "locked_until"])
        AuditLogEntry.objects.create(user=user, action="connexion", ip_address=get_client_ip(self.request))
        return super().form_valid(form)

    def form_invalid(self, form):
        email = self.request.POST.get("username", "").strip()
        if email:
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                user = None
            if user:
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= settings.LOGIN_ATTEMPT_LIMIT:
                    user.locked_until = timezone.now() + timezone.timedelta(
                        minutes=settings.LOGIN_LOCKOUT_MINUTES
                    )
                    logger.warning("Verrouillage du compte %s après trop d'échecs de connexion", email)
                user.save(update_fields=["failed_login_attempts", "locked_until"])
        return super().form_invalid(form)


def logout_view(request):
    if request.user.is_authenticated:
        AuditLogEntry.objects.create(user=request.user, action="deconnexion")
    auth_logout(request)
    return redirect("accounts:login")
