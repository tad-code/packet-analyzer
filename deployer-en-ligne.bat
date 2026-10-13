@echo off
chcp 65001 >nul
title Deployer l'analyseur en ligne
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo   Environnement Python introuvable dans .venv
    echo   Lancez d'abord l'installation du projet.
    echo.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" deployer-en-ligne.py

pause
