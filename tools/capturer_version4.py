

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RACINE = Path(__file__).resolve().parent.parent
DOCS = RACINE / "docs"
DOCS.mkdir(exist_ok=True)

def aller(page, adresse, essais=3):
    derniere = None
    for _ in range(essais):
        try:
            page.goto(adresse, wait_until="load", timeout=30000)
            time.sleep(0.9)
            return True
        except Exception as e:
            derniere = e
            time.sleep(1.5)
    print(f"      (echec : {str(derniere)[:60]})")
    return False

PAGES = [
    ("alertes",             "http://127.0.0.1:5000/alertes"),
    ("en-ligne",            "http://127.0.0.1:5001/"),
    ("en-ligne-capture",    "http://127.0.0.1:5001/capture"),
]

with sync_playwright() as p:
    navigateur = p.chromium.launch(channel="chrome", args=["--no-proxy-server"])
    page = navigateur.new_page(viewport={"width": 1440, "height": 1100})

    for nom, adresse in PAGES:
        if not aller(page, adresse):
            print(f"  {nom:22s} ECHEC")
            continue
        cible = DOCS / f"{nom}.png"
        page.screenshot(path=str(cible), full_page=True)
        print(f"  {nom:22s} {cible.stat().st_size:>8} octets")

    navigateur.close()
