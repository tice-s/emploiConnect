from django.urls import path

from . import views

app_name = "companies"

urlpatterns = [
    path("bienvenue/", views.onboarding, name="onboarding"),
    path("<int:pk>/", views.CompanyDetailView.as_view(), name="detail"),
    path("<int:pk>/modifier/", views.CompanyUpdateView.as_view(), name="edit"),
]
