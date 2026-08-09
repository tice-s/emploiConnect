"""
Point d'entrée unique vers l'IA pour toute la plateforme.

Moteur : Ollama, exécuté localement sur la machine (aucun compte, aucune clé
API, aucune donnée envoyée à un tiers). Toutes les fonctionnalités "assistant
IA de carrière" du cahier des charges passent par ce module : extraction de
CV, génération de CV/lettre, explication du matching, préparation
d'entretien, plan de progression.

Chaque fonction :
- journalise l'appel dans AIInteractionLog (audit + suivi des temps de réponse) ;
- lève AIServiceError avec un message utilisateur clair en cas de problème
  (Ollama non démarré, modèle absent, réponse invalide) plutôt que de laisser
  fuiter une exception technique jusqu'à la vue.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger("ai_engine")

REQUEST_TIMEOUT = 120  # secondes — un petit modèle local peut être lent sur CPU


class AIServiceError(Exception):
    """Erreur métier destinée à être affichée à l'utilisateur (message FR)."""


def _log(kind: str, user=None, success: bool = True, error: str = "", duration_ms: int = 0):
    from .models import AIInteractionLog

    try:
        AIInteractionLog.objects.create(
            user=user,
            kind=kind,
            success=success,
            error_message=error[:500],
            input_tokens=0,
            output_tokens=duration_ms,  # durée (ms) de la génération, faute de comptage de tokens exposé
        )
    except Exception:  # pragma: no cover - la journalisation ne doit jamais casser le flux
        logger.exception("Échec de journalisation de l'appel IA (%s)", kind)


def _extract_json(text: str) -> dict:
    """Extrait le premier objet JSON valide d'une réponse de modèle local
    (les petits modèles ajoutent parfois du texte autour du JSON malgré la consigne)."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise json.JSONDecodeError("Aucun JSON valide trouvé", text, 0)


def _clean_generated_text(text: str) -> str:
    """
    Retire les préambules parasites qu'un petit modèle local ajoute parfois
    avant le texte utile (méta-commentaires, excuses, 'voici la lettre...').
    Ex. remonté : "Je suis désolé, mais je ne peux pas générer... Je vais
    essayer de rédiger une lettre..." avant la vraie lettre.
    """
    bad_starts = (
        "je suis désolé", "je m'excuse", "en tant qu'ia", "en tant qu'assistant",
        "je ne peux pas", "voici", "je vais", "bien sûr", "d'accord,", "je comprends",
        "note :", "note:", "remarque :",
    )
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    while paragraphs and paragraphs[0].lower().startswith(bad_starts):
        paragraphs.pop(0)
    return "\n\n".join(paragraphs).strip()


def _call_ollama(kind: str, system: str, user_prompt: str, *, user=None, json_mode: bool = False,
                  num_predict: int = 1024, temperature: float = 0.4) -> str:
    """Appelle l'API locale d'Ollama (aucun réseau externe, aucune clé)."""
    import time

    payload = {
        "model": settings.OLLAMA_MODEL,
        # Garde le modèle chargé en mémoire 30 min entre deux appels : évite de
        # payer le coût de rechargement à chaque requête (le gain le plus net
        # sur la latence perçue lors d'une session avec plusieurs actions IA).
        "keep_alive": "30m",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": temperature, "num_predict": num_predict},
    }
    if json_mode:
        payload["format"] = "json"

    started = time.monotonic()
    try:
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat", json=payload, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.ConnectionError as exc:
        _log(kind, user=user, success=False, error=str(exc))
        raise AIServiceError(
            "Le moteur IA local (Ollama) n'est pas joignable. Vérifiez qu'Ollama est bien lancé "
            "sur cette machine (aucun compte requis, il tourne en tâche de fond après installation)."
        ) from exc
    except requests.exceptions.Timeout as exc:
        _log(kind, user=user, success=False, error=str(exc))
        raise AIServiceError(
            "Le modèle IA local met trop de temps à répondre. Réessayez, ou utilisez un modèle "
            "plus léger (voir OLLAMA_MODEL dans le fichier .env)."
        ) from exc
    except requests.exceptions.HTTPError as exc:
        _log(kind, user=user, success=False, error=str(exc))
        if response.status_code == 404:
            raise AIServiceError(
                f"Le modèle '{settings.OLLAMA_MODEL}' n'est pas installé localement. "
                f"Lancez : ollama pull {settings.OLLAMA_MODEL}"
            ) from exc
        raise AIServiceError("Le moteur IA local a renvoyé une erreur. Merci de réessayer.") from exc
    except Exception as exc:
        _log(kind, user=user, success=False, error=str(exc))
        logger.exception("Erreur IA (%s)", kind)
        raise AIServiceError("Le moteur IA local a rencontré un problème. Merci de réessayer.") from exc

    duration_ms = int((time.monotonic() - started) * 1000)
    _log(kind, user=user, success=True, duration_ms=duration_ms)

    content = (data.get("message") or {}).get("content", "")
    if not content.strip():
        raise AIServiceError("Réponse IA vide, merci de réessayer.")
    return content


def _call_structured(kind: str, system: str, user_prompt: str, schema_hint: str, *, user=None,
                      num_predict: int = 1024) -> dict:
    """Appelle le modèle local en mode JSON et parse la réponse. `schema_hint` décrit le
    schéma attendu en langage naturel (Ollama ne supporte pas les schémas JSON stricts
    comme les API cloud : on le décrit explicitement dans le prompt et on valide côté Python)."""
    full_system = f"{system}\n\nTu dois répondre UNIQUEMENT avec un objet JSON valide, sans texte autour, respectant exactement cette structure :\n{schema_hint}"
    content = _call_ollama(kind, full_system, user_prompt, user=user, json_mode=True, num_predict=num_predict)
    try:
        return _extract_json(content)
    except json.JSONDecodeError as exc:
        logger.error("Réponse IA non-JSON pour %s : %s", kind, content[:300])
        raise AIServiceError("Réponse IA invalide, merci de réessayer.") from exc


def _call_text(kind: str, system: str, user_prompt: str, *, user=None, num_predict: int = 800,
                temperature: float = 0.4) -> str:
    """Appelle le modèle local pour une réponse texte libre (lettre de motivation, plan...)."""
    raw = _call_ollama(kind, system, user_prompt, user=user, json_mode=False,
                        num_predict=num_predict, temperature=temperature)
    return _clean_generated_text(raw)


# ---------------------------------------------------------------------------
# 1. Extraction automatique du CV (import PDF/DOCX -> profil structuré)
# ---------------------------------------------------------------------------

CV_EXTRACTION_SCHEMA_HINT = """{
  "headline": "string (titre professionnel court)",
  "bio": "string (résumé en 2-3 phrases)",
  "city": "string",
  "education_level": "une valeur parmi: '', 'secondaire', 'bac', 'bac2', 'licence', 'master', 'doctorat'",
  "educations": [{"degree": "string", "institution": "string", "field_of_study": "string", "start_year": null, "end_year": null}],
  "experiences": [{"title": "string", "company": "string", "start_date": "AAAA-MM-JJ ou null", "end_date": "AAAA-MM-JJ ou null", "is_current": false, "description": "string"}],
  "skills": ["string", "..."],
  "languages": [{"name": "string", "level": "A1|A2|B1|B2|C1|C2"}],
  "total_years_experience": 0
}"""

CV_EXTRACTION_SYSTEM = (
    "Tu es un expert en analyse de CV pour une plateforme de recrutement ivoirienne. "
    "Extrais les informations du CV fourni de façon fidèle et structurée, sans inventer "
    "de données absentes (laisse les champs vides/null si l'information n'apparaît pas). "
    "Les compétences doivent être des mots-clés courts et normalisés (ex: 'Django', 'Python', "
    "pas de phrases). Réponds uniquement en français."
)


def extract_cv_data(cv_text: str, *, user=None) -> dict:
    """Transforme le texte brut d'un CV en données structurées prêtes à peupler le profil."""
    prompt = f"Voici le contenu brut extrait d'un CV :\n\n{cv_text[:8000]}"
    data = _call_structured("cv_extraction", CV_EXTRACTION_SYSTEM, prompt, CV_EXTRACTION_SCHEMA_HINT, user=user, num_predict=1500)
    # Garde-fous : un petit modèle local peut omettre des clés — on les complète.
    data.setdefault("headline", "")
    data.setdefault("bio", "")
    data.setdefault("city", "")
    data.setdefault("education_level", "")
    data.setdefault("educations", [])
    data.setdefault("experiences", [])
    data.setdefault("skills", [])
    data.setdefault("languages", [])
    data.setdefault("total_years_experience", 0)
    return data


# ---------------------------------------------------------------------------
# 2. Génération automatique de CV — désormais par gabarit Django, sans IA.
# Voir candidates/cv_themes.py et candidates/views.py::render_cv_html.
# (Un petit modèle local recopiait parfois des `{champ}` littéraux au lieu
# des vraies données — le rendu déterministe élimine le problème et est
# instantané. Cette fonction a été retirée.)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 3. Lettre de motivation personnalisée
# ---------------------------------------------------------------------------
# Comme pour le CV, on ne demande à l'IA QUE ce qu'elle sait bien faire :
# rédiger le corps du texte (2-3 paragraphes de motivation). L'en-tête, la
# date, les blocs d'adresse et la formule de politesse sont générés par un
# gabarit Django à partir des vraies données du profil (candidates/views.py::
# render_letter_html) — jamais par le modèle, qui écrivait des `[Votre nom]`,
# `[Ville]`, `[Siret]` littéraux au lieu de les remplir, inventait des
# expériences absentes du profil, et ajoutait parfois un préambule
# ("Je suis désolé, je ne peux pas...") avant la lettre elle-même.
# Réduire ce que l'IA doit produire réduit aussi nettement le temps de
# réponse (moins de mots à générer sur un modèle CPU).

COVER_LETTER_SYSTEM = (
    "Tu rédiges UNIQUEMENT le corps d'une lettre de motivation professionnelle en "
    "français : 2 paragraphes courts (100 à 140 mots au total maximum), sans en-tête, "
    "sans date, sans adresse, sans 'Madame, Monsieur' en début, sans formule de "
    "politesse finale ni signature — seulement les paragraphes qui expliquent "
    "la motivation et l'adéquation avec le poste, en te basant EXCLUSIVEMENT sur "
    "les compétences, expériences et diplômes listés ci-dessous. N'invente JAMAIS "
    "une expérience, une entreprise, un diplôme ou une compétence absente de cette "
    "liste. Ne commente jamais ta propre réponse, ne t'excuse jamais, n'ajoute "
    "aucun texte avant ou après les paragraphes demandés — écris directement la "
    "lettre, rien d'autre."
)


def _format_experiences_for_prompt(experiences: list[dict]) -> str:
    if not experiences:
        return "aucune expérience professionnelle renseignée"
    return "\n".join(
        f"- {e.get('title', '')} chez {e.get('company', '')}"
        + (f" ({e.get('period')})" if e.get("period") else "")
        + (f" : {e.get('description')}" if e.get("description") else "")
        for e in experiences
    )


def _format_educations_for_prompt(educations: list[dict]) -> str:
    if not educations:
        return "aucun diplôme renseigné"
    return "\n".join(
        f"- {e.get('degree', '')} — {e.get('institution', '')}"
        for e in educations
    )


def generate_cover_letter(*, full_name: str, headline: str, skills: list[str], experiences: list[dict],
                           educations: list[dict], job_title: str, company_name: str, job_description: str,
                           user=None) -> str:
    prompt = (
        f"CANDIDAT : {full_name}"
        + (f" — {headline}" if headline else "") + "\n"
        f"Compétences : {', '.join(skills) or 'non renseignées'}\n"
        f"Expériences professionnelles :\n{_format_experiences_for_prompt(experiences)}\n"
        f"Diplômes :\n{_format_educations_for_prompt(educations)}\n\n"
        f"POSTE VISÉ : {job_title} chez {company_name}\n"
        f"Description de l'offre : {job_description[:1500] or 'non précisée'}"
    )
    # num_predict volontairement bas : moins de mots à générer = réponse plus rapide
    # sur un modèle local CPU, et une lettre concise tient mieux sur une page A4.
    return _call_text("cover_letter", COVER_LETTER_SYSTEM, prompt, user=user, num_predict=260, temperature=0.3)


# ---------------------------------------------------------------------------
# 4. Matching intelligent (score + explication + conseils)
# ---------------------------------------------------------------------------

MATCH_SCHEMA_HINT = """{
  "score": 0,
  "matched_skills": ["string", "..."],
  "missing_skills": ["string", "..."],
  "strengths": ["string", "..."],
  "advice": "string"
}"""

MATCH_SYSTEM = (
    "Tu es un expert en recrutement technique. Compare le profil d'un candidat à une offre "
    "d'emploi et calcule un score de compatibilité honnête de 0 à 100 (entier), fondé sur : les "
    "compétences requises (obligatoires pèsent plus que les atouts), le niveau d'expérience, "
    "le niveau d'études, et la cohérence globale. Sois précis et factuel, jamais complaisant. "
    "Réponds uniquement en français."
)


def compute_match(*, candidate_skills: list[str], candidate_years_experience: float,
                   candidate_education_level: str, job_title: str, job_description: str,
                   required_skills: list[str], mandatory_skills: list[str],
                   required_years_experience: int, required_education_level: str, user=None) -> dict:
    prompt = (
        f"OFFRE : {job_title}\n"
        f"Description : {job_description[:2000]}\n"
        f"Compétences requises : {', '.join(required_skills) or 'non précisé'}\n"
        f"Compétences obligatoires : {', '.join(mandatory_skills) or 'aucune'}\n"
        f"Expérience requise : {required_years_experience} an(s)\n"
        f"Niveau d'études requis : {required_education_level or 'non précisé'}\n\n"
        f"CANDIDAT :\n"
        f"Compétences : {', '.join(candidate_skills) or 'aucune renseignée'}\n"
        f"Expérience : {candidate_years_experience} an(s)\n"
        f"Niveau d'études : {candidate_education_level or 'non précisé'}"
    )
    data = _call_structured("matching", MATCH_SYSTEM, prompt, MATCH_SCHEMA_HINT, user=user, num_predict=700)
    data.setdefault("score", 0)
    data.setdefault("matched_skills", [])
    data.setdefault("missing_skills", [])
    data.setdefault("strengths", [])
    data.setdefault("advice", "")
    try:
        data["score"] = max(0, min(100, int(data["score"])))
    except (TypeError, ValueError):
        data["score"] = 0
    return data


# ---------------------------------------------------------------------------
# 5. Préparation d'entretien : questions + analyse des réponses
# ---------------------------------------------------------------------------

INTERVIEW_QUESTIONS_SCHEMA_HINT = """{
  "questions": [
    {"question": "string", "category": "motivation|comportemental|technique|culture_entreprise"}
  ]
}"""

INTERVIEW_QUESTIONS_SYSTEM = (
    "Tu es un recruteur expérimenté qui prépare un candidat à un entretien d'embauche. "
    "Génère entre 5 et 7 questions d'entretien réalistes et variées (motivation, "
    "comportemental, technique lié au poste, culture d'entreprise) pour le poste et "
    "l'entreprise décrits, en tenant compte du profil du candidat. Réponds en français."
)


def generate_interview_questions(*, job_title: str, company_name: str, job_description: str,
                                  candidate_summary: str, user=None) -> list[dict]:
    prompt = (
        f"Poste : {job_title} chez {company_name}\n"
        f"Description : {job_description[:2000]}\n\n"
        f"Profil du candidat :\n{candidate_summary}"
    )
    data = _call_structured(
        "interview_questions", INTERVIEW_QUESTIONS_SYSTEM, prompt, INTERVIEW_QUESTIONS_SCHEMA_HINT,
        user=user, num_predict=900,
    )
    questions = data.get("questions", [])
    valid_categories = {"motivation", "comportemental", "technique", "culture_entreprise"}
    cleaned = []
    for q in questions:
        if isinstance(q, dict) and q.get("question"):
            cleaned.append({
                "question": q["question"],
                "category": q.get("category") if q.get("category") in valid_categories else "motivation",
            })
    return cleaned or [{"question": "Parlez-moi de votre parcours et de votre motivation pour ce poste.", "category": "motivation"}]


ANSWER_FEEDBACK_SCHEMA_HINT = """{
  "relevance_score": 0,
  "structure_score": 0,
  "feedback": "string"
}"""

ANSWER_FEEDBACK_SYSTEM = (
    "Tu es un coach de carrière qui évalue la réponse d'un candidat à une question "
    "d'entretien. Analyse la pertinence par rapport à la question (note de 0 à 10) et la "
    "clarté/structure de la réponse (note de 0 à 10). Sois bienveillant mais honnête et "
    "donne un conseil concret et actionnable. Réponds en français."
)


def evaluate_interview_answer(*, question: str, answer: str, job_title: str, user=None) -> dict:
    prompt = f"Poste visé : {job_title}\n\nQuestion posée : {question}\n\nRéponse du candidat : {answer}"
    data = _call_structured("interview_feedback", ANSWER_FEEDBACK_SYSTEM, prompt, ANSWER_FEEDBACK_SCHEMA_HINT, user=user, num_predict=500)
    data.setdefault("relevance_score", 5)
    data.setdefault("structure_score", 5)
    data.setdefault("feedback", "")
    return data


SESSION_SUMMARY_SCHEMA_HINT = """{
  "overall_feedback": "string",
  "confidence_score": 0,
  "communication_score": 0,
  "technical_score": 0
}"""

SESSION_SUMMARY_SYSTEM = (
    "Tu es un coach de carrière. À partir de l'ensemble des questions/réponses d'une "
    "simulation d'entretien, produis une synthèse globale : un retour d'ensemble (3-5 phrases) "
    "et trois notes sur 10 (confiance, communication, compétence technique). Réponds en français."
)


def summarize_interview_session(*, qa_pairs: list[dict], user=None) -> dict:
    prompt = "\n\n".join(
        f"Q{i+1} ({qa['category']}) : {qa['question']}\nRéponse : {qa['answer']}"
        for i, qa in enumerate(qa_pairs)
    )
    data = _call_structured("interview_feedback", SESSION_SUMMARY_SYSTEM, prompt, SESSION_SUMMARY_SCHEMA_HINT, user=user, num_predict=600)
    data.setdefault("overall_feedback", "")
    data.setdefault("confidence_score", 5)
    data.setdefault("communication_score", 5)
    data.setdefault("technical_score", 5)
    return data


# ---------------------------------------------------------------------------
# 6. Plan de progression (coach de carrière : passer de 65% à 90% de compatibilité)
# ---------------------------------------------------------------------------

LEARNING_PLAN_SYSTEM = (
    "Tu es un coach de carrière. Un candidat n'est pas encore totalement compatible avec "
    "une offre d'emploi. À partir des compétences manquantes fournies, propose un plan de "
    "progression concret et réaliste (3 à 5 étapes), avec pour chaque étape une compétence "
    "ciblée, une ressource ou un type de formation suggéré, et une durée estimée. Termine par "
    "une phrase d'encouragement. Réponds en français, en Markdown simple (listes à puces)."
)


def generate_learning_plan(*, missing_skills: list[str], job_title: str, user=None) -> str:
    prompt = (
        f"Poste visé : {job_title}\n"
        f"Compétences manquantes : {', '.join(missing_skills)}"
    )
    return _call_text("learning_plan", LEARNING_PLAN_SYSTEM, prompt, user=user, num_predict=600)


# ---------------------------------------------------------------------------
# 7. Détection d'incohérences (vérification, jamais de conclusion automatique de fraude)
# ---------------------------------------------------------------------------

FRAUD_CHECK_SCHEMA_HINT = """{
  "needs_review": false,
  "reason": "string (vide si aucune incohérence)"
}"""

FRAUD_CHECK_SYSTEM = (
    "Tu vérifies la cohérence des informations d'un profil candidat (dates d'obtention de "
    "diplôme, années d'expérience déclarées, chronologie des postes). Tu ne dois JAMAIS "
    "conclure à une fraude : signale uniquement si une vérification manuelle est recommandée, "
    "avec une explication factuelle et neutre. Si tout est cohérent, needs_review=false."
)


def check_profile_consistency(*, profile_summary: str, user=None) -> dict:
    data = _call_structured("fraud_check", FRAUD_CHECK_SYSTEM, profile_summary, FRAUD_CHECK_SCHEMA_HINT, user=user, num_predict=300)
    data.setdefault("needs_review", False)
    data.setdefault("reason", "")
    return data
