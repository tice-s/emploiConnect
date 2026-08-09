import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ai_engine.document_parser import DocumentParsingError, extract_text_from_file
from ai_engine.services import AIServiceError, extract_cv_data, generate_cover_letter
from jobs.models import JobOffer
from .forms import (
    CandidateProfileForm, CoverLetterForm, CVGenerationForm, CVUploadForm,
    EducationForm, ExperienceForm, LanguagesForm, SkillsForm,
)
from .models import (
    CandidateLanguage, CandidateProfile, CandidateSkill, CoverLetter,
    Education, Experience, GeneratedCV, Language, Skill,
)

logger = logging.getLogger("ai_engine")


def _require_candidate(request):
    return request.user.is_authenticated and request.user.is_candidate


@login_required
def profile_view(request):
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    profile.compute_completeness()
    return render(request, "candidates/profile.html", {"profile": profile})


@login_required
def profile_edit(request):
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = CandidateProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            profile.compute_completeness()
            messages.success(request, "Profil mis à jour.")
            return redirect("candidates:profile")
    else:
        form = CandidateProfileForm(instance=profile)
    return render(request, "candidates/profile_edit.html", {"form": form})


@login_required
def cv_upload(request):
    """
    Import du CV (PDF/DOCX) puis extraction automatique par l'IA : diplômes,
    expériences, compétences, langues sont utilisés pour pré-remplir le profil
    sans saisie manuelle (cœur de la promesse produit "CV automatique").
    """
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    if request.method != "POST":
        return render(request, "candidates/cv_upload.html", {"form": CVUploadForm(instance=profile)})

    form = CVUploadForm(request.POST, request.FILES, instance=profile)
    if not form.is_valid():
        messages.error(request, "Fichier invalide (PDF ou DOCX, 5 Mo maximum).")
        return render(request, "candidates/cv_upload.html", {"form": form})

    profile = form.save()

    try:
        cv_text = extract_text_from_file(profile.cv_file)
        extracted = extract_cv_data(cv_text, user=request.user)
    except DocumentParsingError as exc:
        messages.warning(request, f"CV enregistré, mais l'extraction automatique a échoué : {exc}")
        return redirect("candidates:profile")
    except AIServiceError as exc:
        messages.warning(request, f"CV enregistré, mais l'extraction automatique a échoué : {exc}")
        return redirect("candidates:profile")

    _apply_extracted_data(profile, extracted)
    from django.utils import timezone
    profile.cv_imported_at = timezone.now()
    profile.save(update_fields=["cv_imported_at"])
    profile.compute_completeness()

    messages.success(
        request,
        "CV importé et analysé avec succès ! Votre profil a été pré-rempli automatiquement. "
        "Vérifiez et complétez les informations ci-dessous.",
    )
    return redirect("candidates:profile")


def _apply_extracted_data(profile: CandidateProfile, data: dict):
    """Peuple le profil candidat à partir des données structurées renvoyées par l'IA."""
    profile.headline = data.get("headline") or profile.headline
    profile.bio = data.get("bio") or profile.bio
    profile.city = data.get("city") or profile.city
    if data.get("education_level"):
        profile.education_level = data["education_level"]
    profile.save()

    for edu in data.get("educations", []):
        Education.objects.get_or_create(
            profile=profile,
            degree=edu.get("degree", "")[:150],
            institution=edu.get("institution", "")[:150],
            defaults={
                "field_of_study": (edu.get("field_of_study") or "")[:150],
                "start_year": edu.get("start_year"),
                "end_year": edu.get("end_year"),
            },
        )

    for exp in data.get("experiences", []):
        start = _safe_parse_date(exp.get("start_date"))
        Experience.objects.get_or_create(
            profile=profile,
            title=exp.get("title", "")[:150],
            company=exp.get("company", "")[:150],
            defaults={
                "start_date": start,
                "end_date": _safe_parse_date(exp.get("end_date")),
                "is_current": bool(exp.get("is_current")),
                "description": exp.get("description", ""),
            },
        )

    for skill_name in data.get("skills", []):
        skill_name = skill_name.strip()
        if not skill_name:
            continue
        skill = Skill.objects.filter(name__iexact=skill_name).first() or Skill.objects.create(name=skill_name)
        CandidateSkill.objects.get_or_create(profile=profile, skill=skill)

    for lang in data.get("languages", []):
        name = (lang.get("name") or "").strip()
        if not name:
            continue
        language = Language.objects.filter(name__iexact=name).first() or Language.objects.create(name=name)
        CandidateLanguage.objects.get_or_create(
            profile=profile, language=language, defaults={"level": lang.get("level", "B1")}
        )


def _safe_parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@login_required
def experience_list(request):
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ExperienceForm(request.POST)
        if form.is_valid():
            exp = form.save(commit=False)
            exp.profile = profile
            exp.save()
            profile.compute_completeness()
            messages.success(request, "Expérience ajoutée.")
            return redirect("candidates:experiences")
    else:
        form = ExperienceForm()
    return render(request, "candidates/experiences.html", {"form": form, "experiences": profile.experiences.all()})


@login_required
def experience_delete(request, pk):
    exp = get_object_or_404(Experience, pk=pk, profile__user=request.user)
    exp.delete()
    messages.success(request, "Expérience supprimée.")
    return redirect("candidates:experiences")


@login_required
def education_list(request):
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = EducationForm(request.POST)
        if form.is_valid():
            edu = form.save(commit=False)
            edu.profile = profile
            edu.save()
            profile.compute_completeness()
            messages.success(request, "Diplôme ajouté.")
            return redirect("candidates:educations")
    else:
        form = EducationForm()
    return render(request, "candidates/educations.html", {"form": form, "educations": profile.educations.all()})


@login_required
def education_delete(request, pk):
    edu = get_object_or_404(Education, pk=pk, profile__user=request.user)
    edu.delete()
    messages.success(request, "Diplôme supprimé.")
    return redirect("candidates:educations")


@login_required
def skills_update(request):
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = SkillsForm(request.POST)
        if form.is_valid():
            names = [s.strip() for s in form.cleaned_data["skills"].split(",") if s.strip()]
            profile.candidate_skills.all().delete()
            for name in names:
                skill = Skill.objects.filter(name__iexact=name).first() or Skill.objects.create(name=name)
                CandidateSkill.objects.get_or_create(profile=profile, skill=skill)
            profile.compute_completeness()
            messages.success(request, "Compétences mises à jour.")
            return redirect("candidates:profile")
    else:
        initial = ", ".join(cs.skill.name for cs in profile.candidate_skills.all())
        form = SkillsForm(initial={"skills": initial})
    return render(request, "candidates/skills.html", {"form": form})


@login_required
def languages_update(request):
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = LanguagesForm(request.POST)
        if form.is_valid():
            profile.candidate_languages.all().delete()
            for item in form.cleaned_data["languages"].split(","):
                if ":" not in item:
                    continue
                name, level = [p.strip() for p in item.split(":", 1)]
                level = level.upper()
                if not name or level not in dict(CandidateLanguage.Level.choices):
                    continue
                language = Language.objects.filter(name__iexact=name).first() or Language.objects.create(name=name)
                CandidateLanguage.objects.get_or_create(profile=profile, language=language, defaults={"level": level})
            profile.compute_completeness()
            messages.success(request, "Langues mises à jour.")
            return redirect("candidates:profile")
    else:
        initial = ", ".join(f"{cl.language.name}:{cl.level}" for cl in profile.candidate_languages.all())
        form = LanguagesForm(initial={"languages": initial})
    return render(request, "candidates/languages.html", {"form": form})


def _profile_summary_text(profile: CandidateProfile) -> str:
    from applications.views import _build_candidate_summary
    return _build_candidate_summary(profile)


SKILL_LEVEL_PCT = {"debutant": 30, "intermediaire": 55, "avance": 80, "expert": 100}


def _build_cv_context(profile: CandidateProfile) -> dict:
    """Données du profil mises en forme pour l'affichage du CV (aucun appel IA —
    rendu déterministe et instantané par gabarit Django)."""
    return {
        "full_name": profile.user.get_full_name() or profile.user.email,
        "headline": profile.headline,
        "bio": profile.bio,
        "city": profile.city,
        "email": profile.user.email,
        "phone": profile.user.phone,
        "photo_url": profile.photo.url if profile.photo else "",
        "educations": [
            {
                "degree": e.degree, "institution": e.institution, "field_of_study": e.field_of_study,
                "period": f"{e.start_year or ''} - {e.end_year or ''}".strip(" -"),
            }
            for e in profile.educations.all()
        ],
        "experiences": [
            {
                "title": e.title, "company": e.company, "description": e.description,
                "period": (
                    f"{e.start_date:%Y} - {'Aujourd’hui' if e.is_current else (f'{e.end_date:%Y}' if e.end_date else '')}"
                    if e.start_date else ""
                ).strip(" -"),
            }
            for e in profile.experiences.all()
        ],
        "skills": [
            {"name": cs.skill.name, "level_pct": SKILL_LEVEL_PCT.get(cs.level, 60)}
            for cs in profile.candidate_skills.all()
        ],
        "languages": [{"name": cl.language.name, "level": cl.level} for cl in profile.candidate_languages.all()],
    }


SAMPLE_CV_DATA = {
    "full_name": "Aïcha Koffi", "headline": "Chargée de communication",
    "bio": "Professionnelle organisée et créative, 3 ans d'expérience en communication digitale.",
    "city": "Abidjan", "email": "aicha.koffi@exemple.com", "phone": "+225 07 00 00 00", "photo_url": "",
    "educations": [{"degree": "Licence Communication", "institution": "Université FHB", "field_of_study": "", "period": "2019 - 2022"}],
    "experiences": [
        {"title": "Chargée de communication", "company": "SOFEMCI", "period": "2022 - Aujourd’hui", "description": "Gestion des réseaux sociaux et campagnes digitales."},
        {"title": "Assistante marketing", "company": "AgenceX", "period": "2021 - 2022", "description": "Support aux campagnes clients."},
    ],
    "skills": [
        {"name": "Communication", "level_pct": 90}, {"name": "Réseaux sociaux", "level_pct": 75},
        {"name": "Canva", "level_pct": 60}, {"name": "Rédaction", "level_pct": 85},
    ],
    "languages": [{"name": "Français", "level": "C2"}, {"name": "Anglais", "level": "B2"}],
}


def _render_cv_document(data: dict, style: str, theme_key: str) -> str:
    from django.template.loader import render_to_string

    from .cv_themes import THEMES

    context = dict(data)
    context["style"] = style
    context["theme"] = {"id": theme_key, **THEMES[theme_key]}
    return render_to_string("candidates/cv_templates/cv_document.html", context)


def render_cv_html(profile: CandidateProfile, style: str, theme_key: str) -> str:
    """Rend le CV en HTML via gabarit Django — instantané, fiable, sans IA."""
    from .cv_themes import DEFAULT_STYLE, DEFAULT_THEME, STYLES, THEMES

    style = style if style in STYLES else DEFAULT_STYLE
    theme_key = theme_key if theme_key in THEMES else DEFAULT_THEME
    return _render_cv_document(_build_cv_context(profile), style, theme_key)


def render_cv_style_previews(theme_key: str = "cote_ivoire") -> dict:
    """Miniatures des 8 mises en page avec un profil fictif, pour que le
    candidat choisisse visuellement (rendu gabarit — instantané, sans IA)."""
    from .cv_themes import STYLES

    return {style: _render_cv_document(SAMPLE_CV_DATA, style, theme_key) for style in STYLES}


@login_required
def cv_generate(request):
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = CVGenerationForm(request.POST)
        if form.is_valid():
            style = form.cleaned_data["style"]
            theme_key = form.cleaned_data["theme"]
            html = render_cv_html(profile, style, theme_key)
            cv = GeneratedCV.objects.create(profile=profile, style=style, theme=theme_key, content_html=html)
            messages.success(request, "CV généré ! Vous pouvez changer de style ou de couleur à tout moment.")
            return redirect("candidates:generated_cv_detail", pk=cv.pk)
    else:
        form = CVGenerationForm()
    from .cv_themes import STYLES, THEMES
    return render(request, "candidates/cv_generate.html", {
        "form": form, "cvs": profile.generated_cvs.all(),
        "styles_meta": STYLES, "themes_meta": THEMES,
        "style_previews": render_cv_style_previews(),
    })


@login_required
def cv_delete(request, pk):
    cv = get_object_or_404(GeneratedCV, pk=pk, profile__user=request.user)
    if request.method == "POST":
        cv.delete()
        messages.success(request, "CV supprimé.")
    return redirect("candidates:cv_generate")


@login_required
def generated_cv_detail(request, pk):
    cv = get_object_or_404(GeneratedCV, pk=pk, profile__user=request.user)
    return render(request, "candidates/generated_cv_detail.html", {"cv": cv})


@login_required
def cover_letter_generate(request):
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    initial = {}
    job = None
    job_id = request.GET.get("job") or request.POST.get("job_id")
    if job_id:
        job = JobOffer.objects.filter(pk=job_id).first()
        if job:
            initial = {"job_id": job.pk, "company_name": job.company.name, "position_title": job.title}

    if request.method == "POST":
        form = CoverLetterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            description = data.get("job_description") or (job.description if job else "")
            cv_data = _build_cv_context(profile)
            try:
                # On ne demande à l'IA que le corps du texte (2-3 paragraphes) : l'en-tête,
                # la date et les adresses sont ajoutés par gabarit Django à l'affichage
                # (render_letter_html) — voir la note dans ai_engine.services.
                content = generate_cover_letter(
                    full_name=cv_data["full_name"],
                    headline=cv_data["headline"],
                    skills=cv_data["skills"],
                    experiences=cv_data["experiences"],
                    educations=cv_data["educations"],
                    job_title=data.get("position_title") or (job.title if job else ""),
                    company_name=data.get("company_name") or (job.company.name if job else ""),
                    job_description=description,
                    user=request.user,
                )
            except AIServiceError as exc:
                messages.error(request, str(exc))
                return render(request, "candidates/cover_letter_generate.html", {"form": form, "job": job})
            letter = CoverLetter.objects.create(
                profile=profile,
                job=job,
                company_name=data.get("company_name") or (job.company.name if job else ""),
                position_title=data.get("position_title") or (job.title if job else ""),
                content=content,
            )
            messages.success(request, "Lettre générée ! Vous pouvez l'imprimer directement au format A4.")
            return redirect("candidates:cover_letter_detail", pk=letter.pk)
    else:
        form = CoverLetterForm(initial=initial)
    return render(request, "candidates/cover_letter_generate.html", {"form": form, "job": job})


@login_required
def cover_letter_list(request):
    profile, _ = CandidateProfile.objects.get_or_create(user=request.user)
    return render(request, "candidates/cover_letter_list.html", {"letters": profile.cover_letters.all()})


FRENCH_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def french_date(d) -> str:
    return f"{d.day} {FRENCH_MONTHS[d.month - 1]} {d.year}"


def build_letter_context(letter) -> dict:
    """Assemble les données réelles (profil + lettre) pour l'affichage complet de la
    lettre : en-tête, date et adresses sont toujours à jour et jamais écrits par l'IA."""
    from datetime import date

    profile = letter.profile
    body_paragraphs = [p.strip() for p in letter.content.split("\n\n") if p.strip()]
    return {
        "letter": letter,
        "full_name": profile.user.get_full_name() or profile.user.email,
        "city": profile.city,
        "phone": profile.user.phone,
        "email": profile.user.email,
        "date_str": french_date(date.today()),
        "company_name": letter.company_name,
        "position_title": letter.position_title,
        "body_paragraphs": body_paragraphs,
    }


@login_required
def cover_letter_detail(request, pk):
    letter = get_object_or_404(CoverLetter, pk=pk, profile__user=request.user)
    return render(request, "candidates/cover_letter_detail.html", build_letter_context(letter))
