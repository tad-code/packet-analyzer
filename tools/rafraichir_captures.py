import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
DOCS = RACINE / "docs"
LOCAL = "http://127.0.0.1:5000"
EN_LIGNE = "https://analyseur-reseau.vercel.app"


def aller(page, adresse, essais=3):
    derniere = None
    for _ in range(essais):
        try:
            page.goto(adresse, wait_until="load", timeout=45000)
            time.sleep(1.4)
            return True
        except Exception as e:
            derniere = e
            time.sleep(2)
    print(f"      echec : {str(derniere)[:70]}")
    return False


def capturer(page, nom, adresse):
    if not aller(page, adresse):
        print(f"  {nom:26s} ECHEC")
        return False
    cible = DOCS / f"{nom}.png"
    page.screenshot(path=str(cible), full_page=True)
    print(f"  {nom:26s} {cible.stat().st_size:>8} octets")
    return True


# On lit les identifiants dans la page de l'historique, plutot que d'importer
# la couche de stockage : ce script tourne avec un autre environnement, qui n'a
# pas les memes bibliotheques.
identifiant, communication = 6, 147

PAGES = [
    ("protocoles", f"{LOCAL}/protocoles"),
    ("glossaire", f"{LOCAL}/glossaire"),
    ("historique-detail", f"{LOCAL}/historique/{identifiant}"),
    ("en-ligne", f"{EN_LIGNE}/"),
    ("en-ligne-capture", f"{EN_LIGNE}/capture"),
    ("en-ligne-historique", f"{EN_LIGNE}/historique"),
]
if communication:
    PAGES.append(("communication-enregistree",
                  f"{LOCAL}/historique/{identifiant}/communication/{communication}"))

with sync_playwright() as p:
    navigateur = p.chromium.launch(channel="chrome", args=["--no-proxy-server"])
    page = navigateur.new_page(viewport={"width": 1440, "height": 1100})
    for nom, adresse in PAGES:
        capturer(page, nom, adresse)
    navigateur.close()
