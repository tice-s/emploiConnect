from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("inscription/", views.RegisterView.as_view(), name="register"),
    path("connexion/", views.RateLimitedLoginView.as_view(), name="login"),
    path("deconnexion/", views.logout_view, name="logout"),
]
