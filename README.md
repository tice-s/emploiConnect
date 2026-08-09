# EmploiConnect — Plateforme nationale de recherche d'emploi assistée par IA

Assistant IA de carrière de bout en bout : profil candidat auto-rempli depuis un CV,
matching intelligent avec explication, lettres de motivation et CV générés,
préparation d'entretien interactive, et tableau de bord entreprise avec classement
automatique des candidats.

**Stack** : Django 6 + SQLite (base fournie, migration future vers PostgreSQL
possible sans changement de code applicatif) + **IA locale via Ollama** —
aucun compte, aucune clé API, aucune donnée envoyée à un service externe.
Le modèle tourne entièrement sur la machine qui héberge le site.

---

## 1. Installation

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Installer le moteur IA local (Ollama)

Aucun compte à créer, aucune carte bancaire : Ollama est une application qui
fait tourner un modèle de langage directement sur la machine.

```powershell
winget install --id Ollama.Ollama -e
ollama pull llama3.2:3b
```

Ollama démarre automatiquement en tâche de fond après l'installation (icône
dans la barre système) et expose une API locale sur `http://127.0.0.1:11434`.
Rien d'autre à configurer : `.env` pointe déjà dessus par défaut.

```
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
```

**Changer de modèle** : `llama3.2:3b` (2 Go) a été choisi pour rester rapide sur
un PC sans carte graphique dédiée. Avec plus de RAM/CPU disponible, un modèle
plus capable donnera de meilleurs résultats (français plus naturel, matching
plus fin) — par exemple `ollama pull mistral:7b` puis `OLLAMA_MODEL=mistral:7b`
dans `.env`.

**Sans Ollama démarré**, l'application fonctionne normalement (navigation,
comptes, offres, profils) mais les actions IA (import de CV, matching,
lettres, CV générés, entretiens) affichent un message clair invitant à
vérifier qu'Ollama tourne, sans jamais planter.

**Latence attendue** : sur un CPU sans GPU, une génération de CV ou de lettre
de motivation peut prendre 20 à 50 secondes (calcul de matching plus rapide,
~10-20s). C'est le compromis du 100% local/gratuit face à une API cloud
payante — attendu et sans compte à créer.

## 3. Base de données

Les migrations sont déjà générées et appliquées dans ce dépôt (`db.sqlite3`
n'est volontairement pas versionné — voir `.gitignore`). Pour repartir de zéro :

```powershell
python manage.py migrate
python manage.py createsuperuser
```

## 4. Lancer le serveur de développement

```powershell
python manage.py runserver
```

Puis ouvrez http://127.0.0.1:8000/

Compte administrateur créé pendant le développement : `admin@emploiconnect.local`
(mot de passe défini via variable d'environnement lors de la création — à
recréer avec `python manage.py createsuperuser` si besoin).

---

## Structure du projet

| App | Rôle |
|---|---|
| `accounts` | Utilisateur personnalisé (candidat/recruteur), authentification, verrouillage anti brute-force, journal d'audit |
| `candidates` | Profil candidat, CV importé/généré, expériences, diplômes, compétences, langues, lettres de motivation |
| `companies` | Entreprises et recruteurs |
| `jobs` | Offres d'emploi, compétences requises, recherche |
| `applications` | Candidatures, score de matching, statut de traitement |
| `ai_engine` | **Point d'entrée unique vers l'IA locale (Ollama)** — extraction de CV, génération de CV/lettres, matching, questions et analyse d'entretien, plan de progression, vérification de cohérence. Journalise chaque appel (`AIInteractionLog`) |
| `interview_prep` | Sessions de préparation d'entretien (questions générées, réponses, feedback IA, bilan) |
| `dashboard` | Page d'accueil publique + tableaux de bord candidat/entreprise |

## Fonctionnalités IA implémentées (V1)

- **Extraction automatique de CV** (PDF/DOCX → profil structuré, via IA)
- **Génération de CV** en 4 styles × 6 palettes de couleurs (dont Orange/Vert
  par défaut). **Rendu instantané par gabarit Django, sans appel IA** — un
  petit modèle local n'est pas fiable pour recopier des données dans une mise
  en page (voir `candidates/cv_themes.py` et `candidates/views.render_cv_html`)
- **Lettre de motivation personnalisée** par offre (IA)
- **Matching intelligent** avec score, compétences manquantes et conseil
- **Suggestions de postes** (heuristique locale gratuite sur le tableau de bord,
  score fin calculé par l'IA à la demande sur chaque offre)
- **Classement automatique des candidats** côté recruteur, avec explication
- **Vérification de cohérence** du profil (signale, ne conclut jamais seule à une fraude)
- **Préparation d'entretien texte** : génération de questions, analyse de chaque
  réponse, bilan de fin de session (confiance / communication / technique)

**Hors périmètre V1** (décisions prises en amont avec l'utilisateur, voir le fil de
discussion) : simulation d'entretien audio (nécessite transcription + analyse
vocale — chantier à part), Redis/Celery/Docker/CI-CD (le socle est prêt pour
les accueillir sans réécriture : voir `settings.py`, apps découplées).

## Sécurité mise en œuvre

- Validation des mots de passe (longueur, similarité, mots de passe communs)
- Verrouillage temporaire après échecs de connexion répétés
- Protection CSRF/XSS/Clickjacking natives Django + en-têtes de sécurité
- Permissions vérifiées à chaque vue sensible (recruteur ↔ son entreprise,
  candidat ↔ son propre profil)
- Validation d'extension et de taille des fichiers uploadés (CV : PDF/DOCX, 5 Mo max)
- Journal d'audit des actions sensibles (connexion, inscription) et des appels IA

## Prochaines étapes suggérées

1. Essayer un modèle Ollama plus capable (`mistral:7b`, `qwen2.5:7b`) si la
   machine le permet, pour un français plus naturel et un matching plus fin
2. Migrer vers PostgreSQL + Redis/Celery pour la production à grande échelle
3. Ajouter la simulation d'entretien audio (enregistrement navigateur +
   transcription + analyse prosodique) en V2
4. API REST (Django REST Framework) pour une éventuelle application mobile
5. Si le site est déployé pour de vrais utilisateurs (pas seulement en local),
   prévoir un serveur avec assez de RAM/CPU pour héberger Ollama à côté de
   Django, ou revenir à une API cloud (Anthropic/OpenAI) pour la production
