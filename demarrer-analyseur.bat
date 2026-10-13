@echo off
chcp 65001 >nul
title Analyseur reseau - instance locale
cd /d C:\Users\tad\Documents\sprint-python-3

echo ============================================================
echo   ANALYSEUR RESEAU INTELLIGENT - mode local
echo ============================================================
echo.
echo   La capture de paquets n'est possible QUE depuis cette
echo   instance locale. La version en ligne est en lecture seule :
echo   un serveur distant n'a aucun acces a ton reseau.
echo.
echo   Adresse a ouvrir dans le navigateur :
echo       http://127.0.0.1:5000
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
