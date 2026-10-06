"""
Captures d'ecran des pages de la version 3.

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

PAGES = [
    ("protocoles", "/protocoles"),
    ("glossaire", "/glossaire"),
    ("historique-detail", "/historique/6"),
]

with sync_playwright() as p:
    navigateur = p.chromium.launch(channel="chrome", args=["--no-proxy-server"])
    page = navigateur.new_page(viewport={"width": 1440, "height": 1100})

    for nom, chemin in PAGES:
        try:
            page.goto(BASE + chemin, wait_until="load", timeout=30000)
            time.sleep(1.2)
            cible = DOCS / f"{nom}.png"
            page.screenshot(path=str(cible), full_page=True)
            print(f"  {nom:22s} {cible.stat().st_size:>8} octets")
        except Exception as e:
            print(f"  {nom:22s} ECHEC : {str(e)[:80]}")

    # Une communication enregistree : on suit le premier lien trouve.
    try:
        page.goto(BASE + "/historique/6", wait_until="load", timeout=30000)
        lien = page.query_selector('a[href*="/communication/"]')
        if lien:
            lien.click()
            page.wait_for_load_state("load")
            time.sleep(1.2)
            cible = DOCS / "communication-enregistree.png"
            page.screenshot(path=str(cible), full_page=True)
            print(f"  {'communication-enreg.':22s} {cible.stat().st_size:>8} octets")
    except Exception as e:
        print(f"  communication-enregistree ECHEC : {str(e)[:70]}")

    navigateur.close()
