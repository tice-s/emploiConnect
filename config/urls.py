"""URLs racine du projet."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("comptes/", include("accounts.urls")),
    path("candidat/", include("candidates.urls")),
    path("entreprise/", include("companies.urls")),
    path("offres/", include("jobs.urls")),
    path("candidatures/", include("applications.urls")),
    path("entretien/", include("interview_prep.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
