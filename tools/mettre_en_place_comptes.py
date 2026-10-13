

import os
import sys
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from authentification import service
from config import config
from stockage import supabase

COMPTES = [
    ("demonstration", None, None),
    ("analyste", "analyste@example.com", "Analyste-Local-2026!"),
    ("test", "test-cloisonnement@example.com", "Cloisonnement-Test-2026!"),
]

def titre(texte):

    print()
    print("=" * 74)
    print(f"  {texte}")
    print("=" * 74)
    print()

def reference_du_projet():

    adresse = config.supabase_url or ""
    morceau = adresse.replace("https://", "").split(".")
    return morceau[0] if morceau else ""

def appliquer_le_sql():

    titre("1. POLITIQUES DE SECURITE PAR LIGNE (SQL)")

    jeton = os.getenv("SUPABASE_ACCESS_TOKEN", "").strip()
    reference = reference_du_projet()
    script = (RACINE / "sql" / "cloisonnement.sql").read_text(encoding="utf-8")

    if not jeton:
        print("  SUPABASE_ACCESS_TOKEN n'est pas renseignee : le SQL n'est pas envoye.")
        print("  Collez sql/cloisonnement.sql dans l'editeur SQL de Supabase, puis relancez.")
        return False

    reponse = requests.post(
        f"https://api.supabase.com/v1/projects/{reference}/database/query",
        headers={"Authorization": f"Bearer {jeton}", "Content-Type": "application/json"},
        json={"query": script},
        timeout=60,
    )

    print(f"  projet {reference} — reponse de l'API Management : {reponse.status_code}")
    if reponse.status_code >= 400:
        print(f"  {reponse.text[:300]}")
        return False

    return True

def creer_les_comptes():

    titre("2. COMPTES")

    trouves = {}

    for role, courriel, mot_de_passe in COMPTES:
        if role == "demonstration":
            courriel = config.compte_demonstration_courriel
            mot_de_passe = config.compte_demonstration_mot_de_passe
        if not courriel:
            continue

        compte, cree = service.creer_ou_retrouver(courriel, mot_de_passe)
        trouves[role] = compte
        etat = "cree" if cree else "deja present"
        print(f"  {role:<14} {courriel:<32} {etat}  id={compte['identifiant']}")

        if not cree:
            ok, message = service.verifier(courriel, mot_de_passe)
            print(f"  {'':<14} mot de passe : {message}")

    return trouves

def attribuer_les_captures(compte):

    titre("3. CAPTURES DEJA ENREGISTREES")

    if not supabase.disponible()[0]:
        print("  Base non configuree : attribution impossible.")
        return

    restantes = supabase.lire("reseau_analyses", filtre="proprietaire_id=is.null",
                              ordre="id.asc", limite=200)
    print(f"  captures sans proprietaire avant attribution : {len(restantes)}")
    for ligne in restantes:
        print(f"    capture {ligne['id']:<4} du {ligne.get('debut')} — {ligne.get('nb_paquets')} paquets")

    if restantes:
        modifiees = supabase.modifier("reseau_analyses", "proprietaire_id=is.null",
                                      {"proprietaire_id": compte["identifiant"]})
        print(f"  attribuees au compte de demonstration : {len(modifiees or [])}")

    controle = supabase.lire("reseau_analyses", filtre=f"proprietaire_id=eq.{compte['identifiant']}",
                             ordre="id.asc", limite=200)
    print(f"  le compte de demonstration possede maintenant {len(controle)} capture(s) : "
          f"{[l['id'] for l in controle]}")

def main():

    titre("MISE EN PLACE DU CLOISONNEMENT PAR COMPTE")

    print(f"  projet Supabase : {config.supabase_url}")
    print(f"  comptes prets   : {config.authentification_prete()}")

    appliquer_le_sql()
    comptes = creer_les_comptes()

    demonstration = comptes.get("demonstration")
    if demonstration:
        attribuer_les_captures(demonstration)

    titre("TERMINE")
    for role, compte in comptes.items():
        print(f"  {role:<14} {compte['courriel']:<32} id={compte['identifiant']}")

if __name__ == "__main__":
    main()
