from django.urls import path

from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.JobListView.as_view(), name="list"),
    path("gerer/", views.RecruiterJobListView.as_view(), name="recruiter_list"),
    path("nouvelle/", views.JobCreateView.as_view(), name="create"),
    path("<int:pk>/", views.JobDetailView.as_view(), name="detail"),
    path("<int:pk>/modifier/", views.JobUpdateView.as_view(), name="edit"),
    path("<int:pk>/compatibilite/", views.compute_my_match, name="compute_match"),
    path("<int:pk>/candidats/", views.JobCandidatesView.as_view(), name="candidates"),
]
