

import os
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent.parent

adresse = None
for ligne in (RACINE / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
    ligne = ligne.strip()
    if ligne.startswith("SUPABASE_URL="):
        adresse = ligne.split("=", 1)[1].strip()

if not adresse:
    print("  Aucune adresse Supabase dans le fichier .env.")
    raise SystemExit(0)

print("=" * 74)
print("  ETAT DU PROJET SUPABASE")
print("=" * 74)
print()
print(f"  adresse : {adresse}")
print()

try:
    r = requests.get(f"{adresse}/rest/v1/", timeout=20)
    print(f"  racine de l'API : code {r.status_code}")
    corps = r.text[:300].replace("\n", " ")
    print(f"  reponse         : {corps}")
except requests.exceptions.Timeout:
    print("  racine de l'API : delai depasse — le domaine ne repond pas.")
except requests.exceptions.ConnectionError as e:
    print(f"  racine de l'API : connexion impossible — {e}")
except Exception as e:
    print(f"  racine de l'API : erreur {type(e).__name__} — {e}")

print()

try:
    r2 = requests.get(adresse, timeout=20)
    print(f"  domaine du projet : code {r2.status_code}, {len(r2.text)} octets")
    texte = r2.text.lower()
    if "paused" in texte or "pause" in texte or "inactive" in texte:
        print("  ---> MENTION DE PAUSE DETECTEE DANS LA REPONSE")
    elif "restore" in texte or "resume" in texte:
        print("  ---> MENTION DE RESTAURATION DETECTEE DANS LA REPONSE")
except Exception as e:
    print(f"  domaine du projet : erreur {type(e).__name__} — {e}")

print()
print("=" * 74)
print("  CE QUE CELA SIGNIFIE")
print("=" * 74)
print()
print("  Si les deux requetes ci-dessus repondent autre chose qu'un code 401")
print("  accompagnant du JSON, le projet est probablement en pause et doit etre")
print("  reactive depuis le tableau de bord Supabase.")
