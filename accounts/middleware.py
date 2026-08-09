"""Middleware de journalisation légère des requêtes sensibles (audit)."""
import logging

logger = logging.getLogger("django.security")

SENSITIVE_PREFIXES = ("/comptes/", "/admin/")


class AuditLogMiddleware:
    """Journalise les requêtes non-GET vers les zones sensibles (auth, admin)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.method != "GET" and request.path.startswith(SENSITIVE_PREFIXES):
            user = request.user if request.user.is_authenticated else "anonyme"
            logger.info(
                "AUDIT %s %s -> %s | utilisateur=%s | ip=%s",
                request.method,
                request.path,
                response.status_code,
                user,
                get_client_ip(request),
            )
        return response


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
