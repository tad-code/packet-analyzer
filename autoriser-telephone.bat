@echo off
chcp 65001 >nul
title Autoriser le telephone a joindre l'analyseur

net session >nul 2>&1
if errorlevel 1 (
    echo.
    echo   Ce script doit etre lance en administrateur.
    echo   Clic droit sur le fichier, puis "Executer en tant qu'administrateur".
    echo.
    pause
    exit /b 1
)

echo.
echo   Analyseur reseau - acces depuis un telephone du meme Wi-Fi
echo   ---------------------------------------------------------
echo.

echo   Classement du Wi-Fi en reseau prive...
powershell -NoProfile -Command "Set-NetConnectionProfile -InterfaceAlias 'Wi-Fi' -NetworkCategory Private" >nul 2>&1

for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "(Get-NetConnectionProfile -InterfaceAlias 'Wi-Fi').NetworkCategory"`) do set PROFIL=%%i
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "(Get-NetIPAddress -InterfaceAlias 'Wi-Fi' -AddressFamily IPv4).IPAddress"`) do set IP=%%i

echo   Profil Wi-Fi actuel : %PROFIL%
echo.

if "%PROFIL%"=="Private" (
    echo   Le pare-feu Avast laisse maintenant passer les connexions du reseau local.
) else (
    echo   ATTENTION : le profil est reste en Public.
    echo   Ouvrez Avast, Protection, Pare-feu, Reseaux, et classez votre Wi-Fi
    echo   en reseau de confiance.
)

echo.
echo   Depuis le telephone, ouvrez :  http://%IP%:5000
echo.
echo   L'application demandera un identifiant : c'est normal,
echo   elle ne montre jamais les donnees sans compte.
echo.
echo   Rappel : sur un Wi-Fi public ^(cafe, hotel, aeroport^), repassez en
echo   Public avec la commande :
echo   powershell -Command "Set-NetConnectionProfile -InterfaceAlias 'Wi-Fi' -NetworkCategory Public"
echo.
pause
