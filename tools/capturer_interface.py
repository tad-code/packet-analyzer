

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

def aller(page, adresse, essais=3, attente="domcontentloaded"):

    import time as _t
    derniere = None
    for _ in range(essais):
        try:
            page.goto(adresse, wait_until=attente, timeout=60000)
            return True
        except Exception as e:
            derniere = e
            _t.sleep(1.5)
    print(f"      (echec apres {essais} essais : {str(derniere)[:60]})")
    return False

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

print("  demarrage de la capture...")
poster("/capture/demarrer", {"interface": "Wi-Fi"})
time.sleep(2)

print("  generation de trafic...")
for _ in range(4):
    fabriquer_trafic()
    time.sleep(2)

DOSSIER.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    navigateur = p.chromium.launch(
        channel="chrome", headless=True,
        args=["--no-proxy-server", "--disable-gpu"],
    )
    page = navigateur.new_page(viewport={"width": 1600, "height": 1100})

    for nom, chemin in PAGES:

        if not aller(page, BASE + chemin):
            continue
        page.wait_for_timeout(1200)
        sortie = DOSSIER / f"{nom}.png"
        page.screenshot(path=str(sortie), full_page=True)
        print(f"  {sortie.name:22s} {sortie.stat().st_size} octets")

    page.goto(BASE + "/communications", wait_until="domcontentloaded")
    lien = page.query_selector("tbody td a")
    if lien:

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
