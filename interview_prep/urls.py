from django.urls import path

from . import views

app_name = "interview_prep"

urlpatterns = [
    path("preparer/", views.start_session, name="start"),
    path("sessions/", views.session_list, name="session_list"),
    path("sessions/<int:pk>/", views.session_detail, name="session_detail"),
    path("sessions/<int:pk>/terminer/", views.complete_session, name="complete"),
    path("questions/<int:pk>/repondre/", views.submit_answer, name="submit_answer"),
]
