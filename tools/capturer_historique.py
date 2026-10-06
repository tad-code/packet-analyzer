"""
Captures d'ecran de l'historique rempli.

On emploie le navigateur Chrome installe sur la machine, et non le Chromium
embarque : le proxy systeme fait echouer l'acces a 127.0.0.1, d'ou l'option
--no-proxy-server. C'est une contrainte de cette machine, pas un choix.
"""

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RACINE = Path(__file__).resolve().parent.parent
DOCS = RACINE / "docs"
DOCS.mkdir(exist_ok=True)

BASE = "http://127.0.0.1:5000"

PAGES = [
    ("historique", "/historique"),
    ("historique-detail", "/historique/5"),
]

with sync_playwright() as p:
    navigateur = p.chromium.launch(channel="chrome", args=["--no-proxy-server"])
    page = navigateur.new_page(viewport={"width": 1440, "height": 1000})

    for nom, chemin in PAGES:
        try:
            page.goto(BASE + chemin, wait_until="load", timeout=30000)
        except Exception as e:
            print(f"  {nom:22s} ECHEC : {e}")
            continue
        time.sleep(1.2)
        cible = DOCS / f"{nom}.png"
        page.screenshot(path=str(cible), full_page=True)
        print(f"  {nom:22s} {cible.stat().st_size:>8} octets  {chemin}")

    navigateur.close()
