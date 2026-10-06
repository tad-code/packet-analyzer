"""
Captures d'ecran de l'interface, pour la documentation.

Le script demarre une capture, fabrique du trafic, puis photographie chaque page.
Il termine par l'arret de la capture.

Pourquoi fabriquer du trafic : une capture d'ecran d'un tableau vide ne prouve
rien. Les images doivent montrer des donnees reelles.

Prerequis : playwright installe dans l'interpreteur qui execute ce script, et
Google Chrome installe sur la machine.

Deux precautions necessaires sur cette machine :
    - channel="chrome"        : on emploie le Chrome installe ;
    - args --no-proxy-server  : un proxy systeme fait echouer Chrome sur 127.0.0.1.
"""

import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
DOSSIER = Path(__file__).resolve().parent.parent / "docs"

PAGES = [
    ("tableau-de-bord", "/"),
    ("communications", "/communications"),
    ("capture", "/capture"),
    ("historique", "/historique"),
]


def poster(chemin, donnees=None):
    corps = urllib.parse.urlencode(donnees or {}).encode()
    requete = urllib.request.Request(BASE + chemin, data=corps, method="POST")
    requete.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(requete, timeout=30) as r:
            return r.status
    except Exception as e:
        print(f"  [erreur] {chemin} : {e}")
        return -1


def fabriquer_trafic():
    try:
        import socket

        for nom in ("portswigger.net", "wikipedia.org", "github.com"):
            socket.gethostbyname(nom)
    except Exception:
        pass
    for site in ("http://example.com", "http://neverssl.com", "http://info.cern.ch"):
        try:
            urllib.request.urlopen(site, timeout=8).read(300)
        except Exception:
            pass


# --- 1. Capture --------------------------------------------------------------
print("  demarrage de la capture...")
poster("/capture/demarrer", {"interface": "Wi-Fi"})
time.sleep(2)

print("  generation de trafic...")
for _ in range(4):
    fabriquer_trafic()
    time.sleep(2)

# --- 2. Photographies --------------------------------------------------------
DOSSIER.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    navigateur = p.chromium.launch(
        channel="chrome", headless=True,
        args=["--no-proxy-server", "--disable-gpu"],
    )
    page = navigateur.new_page(viewport={"width": 1600, "height": 1100})

    for nom, chemin in PAGES:
        # « networkidle » ne convient pas : pendant une capture, la page se
        # recharge toutes les 2 secondes et le reseau n'est donc jamais au repos.
        # L'attente du DOM suffit, et fonctionne dans les deux cas.
        page.goto(BASE + chemin, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1200)
        sortie = DOSSIER / f"{nom}.png"
        page.screenshot(path=str(sortie), full_page=True)
        print(f"  {sortie.name:22s} {sortie.stat().st_size} octets")

    # --- 3. La vue detaillee d'une communication reelle ----------------------
    page.goto(BASE + "/communications", wait_until="domcontentloaded")
    lien = page.query_selector("tbody td a")
    if lien:
        # L'attribut href est relatif (« /communication/... ») : le navigateur
        # exige une adresse complete, on la reconstitue.
        adresse = lien.get_attribute("href")
        if adresse and adresse.startswith("/"):
            adresse = BASE + adresse
        page.goto(adresse, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        sortie = DOSSIER / "communication.png"
        page.screenshot(path=str(sortie), full_page=True)
        print(f"  {sortie.name:22s} {sortie.stat().st_size} octets")
    else:
        print("  aucune communication a detailler")

    navigateur.close()

poster("/capture/arreter")
print("  capture arretee")
