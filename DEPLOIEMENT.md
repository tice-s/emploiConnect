# Héberger EmploiConnect en production

## Point clé à comprendre avant de choisir un hébergeur

Ce site utilise une **IA locale (Ollama)**, pas une API cloud payante. C'est
un choix qui te libère d'un compte/d'une facturation externe, mais qui a une
conséquence directe sur l'hébergement : **il te faut un serveur où tu peux
installer et faire tourner un programme en arrière-plan** (Ollama), avec
suffisamment de RAM/CPU pour le modèle.

**Ce qui NE fonctionnera PAS** : un hébergement mutualisé classique (OVH
"hébergement web", o2switch, Hostinger mutualisé, etc.) ou une offre gratuite
type PythonAnywhere/Render free tier. Ces offres n'autorisent pas d'installer
un logiciel comme Ollama et n'ont ni les droits systèmes ni la RAM nécessaires.

**Ce qu'il te faut** : un **VPS** (serveur privé virtuel) avec accès root —
c'est un petit serveur Linux à toi tout seul, loué au mois. C'est l'option
recommandée pour avoir l'IA fonctionnelle en production, ci-dessous.

Si tu veux d'abord un lien public **gratuit** pour montrer le site (sans les
fonctions IA en ligne), la section suivante explique le déploiement
Render + Neon.

---

## Option gratuite : Render (site) + Neon (base PostgreSQL)

Le dépôt est déjà prêt pour ça (`render.yaml`, `Procfile`, `build.sh`,
`whitenoise`, `dj-database-url` dans `requirements.txt` — rien à modifier).

⚠️ **Limite importante** : le plan gratuit Render ne permet pas d'installer
un programme séparé comme Ollama (pas d'accès système, 512 Mo de RAM à
peine suffisants pour Django lui-même). **Les fonctions IA (import de CV,
matching, lettres, entretien) ne fonctionneront pas** tant qu'`OLLAMA_BASE_URL`
ne pointe pas vers une instance Ollama accessible — soit ton PC exposé (non
recommandé, pas fiable), soit un petit VPS séparé pour Ollama uniquement
(~4-5 €/mois, voir "Option alternative" plus bas). Le reste du site (comptes,
offres, profils, candidatures) fonctionne normalement sans Ollama.

### 1. Créer la base PostgreSQL sur Neon (gratuit, permanent)

1. Va sur [neon.tech](https://neon.tech), crée un compte (gratuit, pas de
   carte bancaire).
2. "Create a project" → choisis une région proche de tes utilisateurs.
3. Dans l'onglet **Connection string**, copie l'URL au format
   `postgresql://user:password@xxxxx.neon.tech/dbname?sslmode=require`.

### 2. Pousser le code sur GitHub

Render déploie depuis un dépôt Git. Si ce n'est pas déjà fait :

```bash
cd D:\siteWeb\siteDjango\AIDemp
git init
git add .
git commit -m "Initial commit"
```

Crée un dépôt vide sur GitHub puis :
```bash
git remote add origin https://github.com/TON-COMPTE/emploiconnect.git
git push -u origin main
```

### 3. Créer un compte Cloudinary (stockage permanent des photos/logos)

Render a un **disque éphémère** : toute photo de profil ou logo uploadé est
supprimé au prochain déploiement. Cloudinary stocke ces fichiers ailleurs,
de façon permanente, gratuitement.

1. Va sur [cloudinary.com](https://cloudinary.com) → "Sign up" (gratuit, pas
   de carte bancaire, 25 Go inclus).
2. Sur le dashboard, section **"API Environment variable"**, copie la valeur
   du type `cloudinary://123456789012345:AbCdEfGhIjKlMnOpQrStUvWxYz@ton-cloud`.

### 4. Créer le service sur Render

1. Va sur [render.com](https://render.com), crée un compte (gratuit).
2. "New +" → **Blueprint** → connecte ton dépôt GitHub → Render détecte
   automatiquement `render.yaml`.
3. Render te demandera de renseigner les variables marquées `sync: false` :
   - `DATABASE_URL` : colle l'URL Neon copiée à l'étape 1.
   - `CLOUDINARY_URL` : colle l'URL Cloudinary copiée à l'étape 3.
   - `OLLAMA_BASE_URL` : laisse vide si tu n'as pas encore de VPS Ollama
     (les fonctions IA afficheront un message d'erreur clair sans planter,
     comme prévu dans `ai_engine`).
4. Clique "Apply" — Render construit le site (`build.sh` : installe les
   dépendances, `collectstatic`, `migrate`) puis le démarre avec Gunicorn.

Ton site est en ligne sur `https://emploiconnect.onrender.com` (ou le nom
que tu as choisi) en quelques minutes.

**Créer un compte admin** une fois déployé, depuis l'onglet "Shell" du
dashboard Render :
```bash
python manage.py createsuperuser
```

**Limite à connaître** : le service gratuit se met en veille après 15 min
sans visite ; la première requête suivante prend 30-60 secondes à répondre
(temps de réveil), les suivantes sont normales.

---

## Option recommandée pour l'IA en production : un seul VPS (Django + Ollama ensemble)

### 1. Choisir et commander un VPS

| Fournisseur | Offre indicative | Prix/mois |
|---|---|---|
| Hetzner Cloud | CX22 (4 Go RAM, 2 vCPU) | ~4-5 € |
| Contabo | VPS S (8 Go RAM, 4 vCPU) | ~6-8 € |
| DigitalOcean | Droplet 4 Go RAM | ~24 $ |
| OVHcloud | VPS (4-8 Go RAM) | ~7-15 € |

**Minimum recommandé : 4 Go de RAM** (le modèle `llama3.2:3b` en utilise
environ 2-3 Go pendant les réponses). Avec 8 Go tu peux passer à un modèle
plus capable (`mistral:7b`) plus tard.

Choisis **Ubuntu 22.04 LTS** comme système lors de la commande.

### 2. Se connecter et préparer le serveur

```bash
ssh root@IP_DE_TON_SERVEUR

apt update && apt upgrade -y
apt install -y python3-venv python3-pip nginx git ufw

# Pare-feu : n'ouvrir que ce qui est nécessaire
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw enable
```

### 3. Installer Ollama sur le serveur

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
```

Ollama s'installe comme un service systemd et démarre automatiquement — rien
d'autre à faire, il tourne déjà sur `127.0.0.1:11434`, invisible depuis
l'extérieur (c'est voulu : il n'a aucune authentification, il ne doit
**jamais** être exposé publiquement).

### 4. Déployer le code du site

```bash
mkdir -p /var/www/emploiconnect
cd /var/www/emploiconnect
# Envoie ton code ici (git clone si tu as un dépôt, ou scp/sftp depuis ta machine)

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

### 5. Configurer les variables de production (`.env`)

```
SECRET_KEY=<une longue clé aléatoire différente de celle du développement>
DEBUG=False
ALLOWED_HOSTS=tonnomdedomaine.com,www.tonnomdedomaine.com

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
```

Génère une clé secrète solide :
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 6. Préparer la base et les fichiers statiques

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### 7. Lancer Django avec Gunicorn (au lieu du serveur de développement)

Crée `/etc/systemd/system/emploiconnect.service` :

```ini
[Unit]
Description=EmploiConnect (Gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/emploiconnect
ExecStart=/var/www/emploiconnect/venv/bin/gunicorn config.wsgi:application \
    --bind 127.0.0.1:8000 --workers 3 --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

> Le `--timeout 120` est important : une génération IA locale peut prendre
> 20 à 50 secondes, il faut laisser le temps à Gunicorn de ne pas couper la
> requête.

```bash
chown -R www-data:www-data /var/www/emploiconnect
systemctl daemon-reload
systemctl enable --now emploiconnect
systemctl status emploiconnect
```

### 8. Nginx comme façade (reverse proxy + fichiers statiques)

Crée `/etc/nginx/sites-available/emploiconnect` :

```nginx
server {
    listen 80;
    server_name tonnomdedomaine.com www.tonnomdedomaine.com;

    location /static/ {
        alias /var/www/emploiconnect/staticfiles/;
    }
    location /media/ {
        alias /var/www/emploiconnect/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/emploiconnect /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### 9. Nom de domaine + HTTPS gratuit

1. Achète un nom de domaine (Namecheap, OVH, Gandi...) et pointe son
   enregistrement DNS **A** vers l'IP de ton VPS.
2. Une fois le DNS propagé (quelques minutes à quelques heures) :

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d tonnomdedomaine.com -d www.tonnomdedomaine.com
```

Certbot configure automatiquement le HTTPS et le renouvellement du
certificat. Ton site est en ligne sur `https://tonnomdedomaine.com`.

### 10. Sauvegardes

La base de données est un simple fichier (`db.sqlite3`). Sauvegarde-la
régulièrement (cron quotidien vers un autre stockage) :

```bash
crontab -e
# Ajouter :
0 3 * * * cp /var/www/emploiconnect/db.sqlite3 /var/backups/emploiconnect-$(date +\%F).sqlite3
```

---

## Option alternative : héberger Django à part, Ollama sur un petit VPS séparé

Si tu préfères un hébergeur Django "clé en main" (Railway, Render, PythonAnywhere
payant...) qui ne permet pas d'installer Ollama :

1. Loue quand même un petit VPS (même 4 Go suffit) uniquement pour Ollama.
2. Sur ce VPS, autorise Ollama à écouter au-delà de `127.0.0.1` :
   `OLLAMA_HOST=0.0.0.0 systemctl edit ollama` (variable d'environnement du service).
3. **Protège absolument cet accès** avec un pare-feu qui n'autorise que l'IP
   de ton serveur Django (`ufw allow from IP_DE_TON_DJANGO to any port 11434`)
   — Ollama n'a aucune authentification intégrée, ne jamais l'ouvrir à tout
   Internet.
4. Dans le `.env` de ton hébergement Django : `OLLAMA_BASE_URL=http://IP_DU_VPS_OLLAMA:11434`.

C'est plus de travail de configuration réseau pour un gain limité — l'option
"un seul VPS" ci-dessus est plus simple et recommandée pour démarrer.

---

## Mettre à jour le site après une modification

```bash
cd /var/www/emploiconnect
# récupérer le nouveau code
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart emploiconnect
```

## Checklist avant mise en ligne

- [ ] `DEBUG=False` dans `.env` de production
- [ ] `SECRET_KEY` différente et unique (jamais celle du dépôt de développement)
- [ ] `ALLOWED_HOSTS` renseigné avec ton vrai nom de domaine
- [ ] HTTPS actif (certbot) — active alors aussi les options `SESSION_COOKIE_SECURE`
      etc. déjà prévues dans `settings.py` (activées automatiquement quand `DEBUG=False`)
- [ ] Sauvegarde automatique de `db.sqlite3` en place
- [ ] Ollama non accessible depuis l'extérieur (vérifier avec `curl http://IP_PUBLIQUE:11434` depuis ta machine — doit échouer)
