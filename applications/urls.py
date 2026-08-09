from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    path("postuler/<int:pk>/", views.apply_to_job, name="apply"),
    path("mes-candidatures/", views.MyApplicationsListView.as_view(), name="my_list"),
    path("<int:pk>/", views.ApplicationDetailView.as_view(), name="detail"),
    path("<int:pk>/statut/", views.update_application_status, name="update_status"),
]
