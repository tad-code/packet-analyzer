"""
Captures d'ecran.

On emploie le Chrome installe sur la machine, avec --no-proxy-server : le proxy
systeme fait echouer l'acces a 127.0.0.1. Contrainte de cette machine.
"""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RACINE = Path(__file__).resolve().parent.parent
DOCS = RACINE / "docs"
DOCS.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:5000"


def aller(page, adresse, essais=3):
    """
    Ouvre une page, avec reprise.

    Le pilote de navigateur echoue parfois par « ERR_ABORTED » alors que le
    serveur repond normalement, en moins d'une seconde : c'est une instabilite
    du pilote, pas un defaut de l'application. Sans reprise, une capture
    manquerait pour une raison qui n'a rien a voir avec le projet.
    """
    derniere = None
    for _ in range(essais):
        try:
            page.goto(adresse, wait_until="load", timeout=30000)
            time.sleep(0.9)
            return True
        except Exception as e:
            derniere = e
            time.sleep(1.5)
    print(f"      (echec apres {essais} essais : {str(derniere)[:60]})")
    return False


def capturer(page, nom, chemin):
    """Capture une page si elle repond, et rend le compte rendu."""
    if not aller(page, BASE + chemin):
        print(f"  {nom:24s} ECHEC de navigation")
        return False
    cible = DOCS / f"{nom}.png"
    page.screenshot(path=str(cible), full_page=True)
    print(f"  {nom:24s} {cible.stat().st_size:>8} octets  {chemin}")
    return True


PAGES = [
    ("protocoles", "/protocoles"),
    ("glossaire", "/glossaire"),
    ("historique-detail", "/historique/6"),
]

with sync_playwright() as p:
    navigateur = p.chromium.launch(channel="chrome", args=["--no-proxy-server"])
    page = navigateur.new_page(viewport={"width": 1440, "height": 1100})

    for nom, chemin in PAGES:
        capturer(page, nom, chemin)

    # Une communication enregistree : on suit le premier lien trouve.
    if aller(page, BASE + "/historique/6"):
        lien = page.query_selector('a[href*="/communication/"]')
        if lien:
            lien.click()
            page.wait_for_load_state("load")
            time.sleep(1.2)
            cible = DOCS / "communication-enregistree.png"
            page.screenshot(path=str(cible), full_page=True)
            print(f"  {'communication-enregistree':24s} {cible.stat().st_size:>8} octets")
        else:
            print("  aucune communication enregistree a capturer")

    navigateur.close()
