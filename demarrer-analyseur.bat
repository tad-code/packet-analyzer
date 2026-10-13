@echo off
chcp 65001 >nul
title Analyseur reseau - instance locale
cd /d C:\Users\tad\Documents\sprint-python-3

rem Ecoute sur toutes les cartes : l'application devient joignable depuis le
rem telephone, sur le meme reseau Wi-Fi. Toute requete venue du reseau suit le
rem parcours normal et doit s'identifier ; seule cette machine ouvre la session
rem automatiquement.
set HOST=0.0.0.0

set IPRESEAU=
for /f "delims=" %%a in ('.venv\Scripts\python.exe -c "import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(('8.8.8.8',80));print(s.getsockname()[0])"') do set IPRESEAU=%%a

echo ============================================================
echo   ANALYSEUR RESEAU INTELLIGENT - mode local
echo ============================================================
echo.
echo   La capture de paquets n'est possible QUE depuis cette
echo   instance locale. La version en ligne est en lecture seule :
echo   un serveur distant n'a aucun acces a ton reseau.
echo.
echo   Sur cette machine (session ouverte automatiquement) :
echo       http://127.0.0.1:5000
echo.
if defined IPRESEAU (
echo   Depuis le telephone, sur le meme reseau Wi-Fi :
echo       http://%IPRESEAU%:5000
echo.
echo   Depuis le telephone, l'application demande un identifiant :
echo   les captures de cette machine ne s'affichent pas toutes seules.
echo   ^(Si le telephone n'y arrive pas, autoriser le port 5000 une
echo    fois, en administrateur : voir le README, section "^4^".^)
) else (
echo   Adresse reseau introuvable : connecte-toi au Wi-Fi puis relance.
)
echo.
echo   Laisse cette fenetre ouverte pendant l'utilisation.
echo   Ferme-la (ou Ctrl+C) pour arreter l'analyseur.
echo.
echo ============================================================
echo.

.venv\Scripts\python.exe app.py

echo.
echo   L'analyseur s'est arrete.
pause
