from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("mon-espace/", views.redirect_view, name="redirect"),
    path("mon-espace/candidat/", views.candidate_dashboard, name="candidate"),
    path("mon-espace/entreprise/", views.recruiter_dashboard, name="recruiter"),
]
