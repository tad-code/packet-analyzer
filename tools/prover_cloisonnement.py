

import re
import sys
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from authentification import service
from config import config
from stockage import supabase

COMPTE_DEMONSTRATION = (config.compte_demonstration_courriel,
                        config.compte_demonstration_mot_de_passe)

COMPTE_ANALYSTE = ("analyste@example.com", "Analyste-Local-2026!")

COMPTE_TEST = ("test-cloisonnement@example.com", "Cloisonnement-Test-2026!")

CAPTURE_CONNUE = 17

COMMUNICATIONS_FACTICES = [
    ("192.168.1.20:49712-93.184.216.34:443-TCP", "192.168.1.20", 49712,
     "93.184.216.34", 443, "TCP", "HTTPS", 42, 18422, "terminee", "SYN,ACK"),
    ("192.168.1.20:53110-192.168.1.1:53-UDP", "192.168.1.20", 53110,
     "192.168.1.1", 53, "UDP", "DNS", 6, 812, "terminee", None),
    ("192.168.1.20:60122-140.82.121.3:22-TCP", "192.168.1.20", 60122,
     "140.82.121.3", 22, "TCP", "SSH", 18, 6210, "ouverte", "SYN,ACK"),
]

RESULTATS = []

def titre(texte):

    print()
    print("=" * 74)
    print(f"  {texte}")
    print("=" * 74)
    print()

def retenir(nom, ok, detail):

    RESULTATS.append((nom, ok, detail))
    marque = "OK  " if ok else "ECHEC"
    print(f"  [{marque}] {nom} : {detail}")

def communications_factices():

    trouvailles = []
    for cle, ip1, port1, ip2, port2, protocole, service_nom, nb, octets, etat, drapeaux in COMMUNICATIONS_FACTICES:
        trouvailles.append({
            "cle": cle,
            "premiere_extremite": {"ip": ip1, "port": port1},
            "seconde_extremite": {"ip": ip2, "port": port2},
            "initiateur": "premiere",
            "protocole": protocole,
            "port_service": port2,
            "service_probable": service_nom,
            "nb_paquets": nb,
            "octets": octets,
            "duree": 2.4,
            "etat": etat,
            "drapeaux_vus": drapeaux,
        })
    return trouvailles

def preparer():

    titre("0. COMPTES ET CAPTURE DU SECOND COMPTE")

    comptes = {}
    for role, (courriel, mot_de_passe) in {
        "demonstration": COMPTE_DEMONSTRATION,
        "analyste": COMPTE_ANALYSTE,
        "test": COMPTE_TEST,
    }.items():
        compte, cree = service.creer_ou_retrouver(courriel, mot_de_passe)
        comptes[role] = compte
        print(f"  {role:<14} {courriel:<32} {'cree' if cree else 'deja present'} "
              f"id={compte['identifiant']}")

    test = comptes["test"]

    deja = supabase.lire("reseau_analyses",
                         filtre=f"proprietaire_id=eq.{test['identifiant']}", limite=20)

    if deja:
        print(f"  capture du second compte deja presente : {[l['id'] for l in deja]}")
        return comptes, {l["id"] for l in deja}

    communications = communications_factices()
    identifiant, nombre = supabase.enregistrer_analyse(
        interface="poste de test",
        paquets=66,
        communications=communications,
        resume_par_communication={
            c["cle"]: "Communication enregistree pour le test de cloisonnement."
            for c in communications
        },
        proprietaire=test["identifiant"],
    )
    print(f"  capture enregistree pour le second compte : id={identifiant}, "
          f"{nombre} communications")
    return comptes, {identifiant}

def preuve_base(comptes):

    titre("1. PREUVE PAR LA BASE (API REST Supabase, cle publique + jeton du compte)")

    url = config.supabase_url
    publique = config.supabase_cle_publique

    for role in ("demonstration", "test", "analyste"):
        courriel, mot_de_passe = {"demonstration": COMPTE_DEMONSTRATION,
                                  "test": COMPTE_TEST,
                                  "analyste": COMPTE_ANALYSTE}[role]
        ouverte = service.connecter(courriel, mot_de_passe)
        entetes = {"apikey": publique, "Authorization": f"Bearer {ouverte['jeton']}"}

        r = requests.get(f"{url}/rest/v1/reseau_analyses?select=id&order=id.asc",
                         headers=entetes, timeout=20)
        identifiants = [l["id"] for l in (r.json() if r.status_code == 200 else [])]
        retenir(f"base / {role} / liste des captures", True,
                f"code {r.status_code} :: {identifiants}")

        r = requests.get(f"{url}/rest/v1/reseau_analyses?select=id&id=eq.{CAPTURE_CONNUE}",
                         headers=entetes, timeout=20)
        corps = r.json() if r.status_code == 200 else r.text[:120]
        retenir(f"base / {role} / capture {CAPTURE_CONNUE} demandee directement",
                (corps == [] or role == "demonstration"),
                f"code {r.status_code} :: {corps}")

        r = requests.get(f"{url}/rest/v1/reseau_communications?select=id,analyse_id&limit=200",
                         headers=entetes, timeout=20)
        corps = r.json() if r.status_code == 200 else r.text[:120]
        analyses_vues = sorted({l["analyse_id"] for l in corps}) if isinstance(corps, list) else corps
        retenir(f"base / {role} / communications", True,
                f"code {r.status_code} :: captures concernees {analyses_vues}")

        r = requests.get(f"{url}/rest/v1/reseau_analyses?select=id", timeout=20,
                         headers={"apikey": publique})
        corps = r.json() if r.status_code == 200 else r.text[:120]
        retenir("base / sans compte (cle publique seule)", corps == [],
                f"code {r.status_code} :: {corps}")

def _identifiants_visibles(html):

    return sorted({int(m) for m in re.findall(r"/historique/(\d+)", html)})

def preuve_application(base, captures_du_second):

    titre(f"2. PREUVE PAR L'APPLICATION ({base})")

    visiteur = requests.Session()
    r = visiteur.get(f"{base}/historique", timeout=30, allow_redirects=False)
    retenir("application / visiteur sans compte / /historique", r.status_code in (301, 302, 303, 307, 308),
            f"code {r.status_code} :: redirection vers {r.headers.get('Location')}")

    r = visiteur.get(f"{base}/historique/17", timeout=30, allow_redirects=False)
    retenir("application / visiteur sans compte / /historique/17", r.status_code in (301, 302, 303, 307, 308),
            f"code {r.status_code} :: redirection vers {r.headers.get('Location')}")

    captures = {}

    for role in ("demonstration", "test", "analyste"):
        courriel, mot_de_passe = {"demonstration": COMPTE_DEMONSTRATION,
                                  "test": COMPTE_TEST,
                                  "analyste": COMPTE_ANALYSTE}[role]
        session = requests.Session()
        ouverture = session.post(f"{base}/connexion",
                                 data={"courriel": courriel, "mot_de_passe": mot_de_passe, "suite": ""},
                                 timeout=30, allow_redirects=False)
        retenir(f"application / connexion {role}", ouverture.status_code in (302, 303),
                f"code {ouverture.status_code} :: {ouverture.headers.get('Location')}")

        page = session.get(f"{base}/historique", timeout=30)
        vues = _identifiants_visibles(page.text)
        captures[role] = vues
        retenir(f"application / {role} / /historique", page.status_code == 200,
                f"code {page.status_code} :: captures affichees {vues}")

        page = session.get(f"{base}/", timeout=30)
        retenir(f"application / {role} / tableau de bord",
                page.status_code in (200, 302),
                f"code {page.status_code} :: captures citees {_identifiants_visibles(page.text)}")

        for page_nom in ("/communications", "/alertes", "/protocoles", "/historique/17"):
            reponse = session.get(f"{base}{page_nom}", timeout=30)
            extrait = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", reponse.text))[:150]
            retenir(f"application / {role} / {page_nom}",
                    reponse.status_code in (200, 403),
                    f"code {reponse.status_code} :: {extrait}")

        detail = session.get(f"{base}/historique/{CAPTURE_CONNUE}", timeout=30)
        appartient = CAPTURE_CONNUE in captures.get(role, [])
        attendu = 200 if appartient else 403
        retenir(f"application / {role} / acces direct a /historique/{CAPTURE_CONNUE}",
                detail.status_code == attendu,
                f"code {detail.status_code} (attendu {attendu})")

    titre("3. SYNTHESE DU CLOISONNEMENT")

    demonstration = set(captures.get("demonstration", []))
    test = set(captures.get("test", []))

    retenir("le compte de demonstration ne voit aucune capture du second compte",
            not (captures_du_second & demonstration),
            f"captures du second compte {sorted(captures_du_second)} — "
            f"captures vues par le compte de demonstration : {sorted(demonstration)}")
    retenir("le second compte ne voit pas la capture de demonstration",
            CAPTURE_CONNUE not in test,
            f"captures vues par le second compte : {sorted(test)}")

    echecs = [nom for nom, ok, _ in RESULTATS if not ok]
    print()
    print(f"  controles : {len(RESULTATS)} — echecs : {len(echecs)}")
    for nom in echecs:
        print(f"    - {nom}")

    return not echecs

def main():

    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"

    titre("PREUVE DU CLOISONNEMENT PAR COMPTE")

    comptes, captures_du_second = preparer()
    preuve_base(comptes)
    ok = preuve_application(base, captures_du_second)

    print()
    print("  RESULTAT :", "cloisonnement verifie" if ok else "ECART DETECTE")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
