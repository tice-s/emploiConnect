from django.urls import path

from . import views

app_name = "candidates"

urlpatterns = [
    path("profil/", views.profile_view, name="profile"),
    path("profil/modifier/", views.profile_edit, name="profile_edit"),
    path("cv/importer/", views.cv_upload, name="cv_upload"),
    path("experiences/", views.experience_list, name="experiences"),
    path("experiences/<int:pk>/supprimer/", views.experience_delete, name="experience_delete"),
    path("diplomes/", views.education_list, name="educations"),
    path("diplomes/<int:pk>/supprimer/", views.education_delete, name="education_delete"),
    path("competences/", views.skills_update, name="skills"),
    path("langues/", views.languages_update, name="languages"),
    path("cv/generer/", views.cv_generate, name="cv_generate"),
    path("cv/genere/<int:pk>/", views.generated_cv_detail, name="generated_cv_detail"),
    path("cv/genere/<int:pk>/supprimer/", views.cv_delete, name="generated_cv_delete"),
    path("lettre/generer/", views.cover_letter_generate, name="cover_letter_generate"),
    path("lettres/", views.cover_letter_list, name="cover_letter_list"),
    path("lettres/<int:pk>/", views.cover_letter_detail, name="cover_letter_detail"),
]
