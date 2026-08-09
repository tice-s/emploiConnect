@echo off
REM ============================================================
REM  EmploiConnect - lancement du site en un clic
REM  Double-cliquez sur ce fichier pour tout demarrer.
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo   EmploiConnect - demarrage
echo ============================================
echo.

REM --- 1. Environnement virtuel Python -------------------------------------
if not exist "venv\Scripts\python.exe" (
    echo [1/4] Environnement virtuel introuvable, creation en cours...
    python -m venv venv
    if errorlevel 1 (
        echo ERREUR : Python n'est pas installe ou introuvable dans le PATH.
        pause
        exit /b 1
    )
    echo       Installation des dependances...
    venv\Scripts\pip.exe install -r requirements.txt --quiet
) else (
    echo [1/4] Environnement virtuel OK.
)

REM --- 2. Verifier que le moteur IA local (Ollama) tourne ------------------
echo [2/4] Verification du moteur IA local (Ollama)...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://127.0.0.1:11434' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo       Ollama n'est pas demarre, lancement...
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe" (
        start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"
        timeout /t 4 /nobreak >nul
    ) else (
        echo       ATTENTION : Ollama ne semble pas installe.
        echo       Installez-le avec : winget install --id Ollama.Ollama -e
        echo       Puis telechargez le modele : ollama pull llama3.2:3b
    )
) else (
    echo       Ollama est deja actif.
)

REM --- 3. Migrations de base de donnees -------------------------------------
echo [3/4] Verification de la base de donnees...
venv\Scripts\python.exe manage.py migrate --noinput

REM --- 4. Lancement du serveur et ouverture du navigateur -------------------
echo [4/4] Lancement du serveur EmploiConnect...
echo.
echo   Le site sera accessible sur : http://127.0.0.1:8000/
echo   Laissez cette fenetre ouverte tant que vous utilisez le site.
echo   Fermez-la (ou Ctrl+C) pour arreter le serveur.
echo.

start "" http://127.0.0.1:8000/
venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

endlocal
