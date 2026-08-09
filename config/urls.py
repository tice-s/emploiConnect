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

# Sert les fichiers uploadés (photo de profil, logo d'entreprise, CV importés)
# aussi bien en local qu'en production. Sur un projet de cette taille, sans
# CDN/S3 dédié, faire porter ça par Django (via WhiteNoise en amont pour le
# reste) reste le choix le plus simple ; à revoir si le trafic média grossit.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
