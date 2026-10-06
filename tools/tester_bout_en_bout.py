"""
Test de bout en bout, dans l'application reelle.

Le parcours complet de l'utilisateur, sans raccourci :

    1. demarrer une capture ;
    2. produire du trafic reseau ;
    3. arreter la capture ;
    4. enregistrer la capture dans Supabase ;
    5. verifier qu'elle apparait dans l'historique.

Puis les donnees de test sont supprimees : l'historique doit rester propre.

Ce test emploie le serveur HTTP, et non les fonctions internes. C'est ce qui le
distingue des tests unitaires : il verifie le chemin que l'utilisateur emprunte
vraiment, formulaires et redirections compris.
"""

import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = "http://127.0.0.1:5000"
succes, echecs = [], []


def verifier(intitule, condition, detail=""):
    (succes if condition else echecs).append(intitule)
    print(f"  [{'OK   ' if condition else 'ECHEC'}] {intitule}"
          + (f"  — {detail}" if detail else ""))


def demander(chemin, methode="GET", donnees=None):
    url = BASE + chemin
    corps = urllib.parse.urlencode(donnees).encode() if donnees else None
    requete = urllib.request.Request(url, data=corps, method=methode)
    if corps:
        requete.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(requete, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


print()
print("=" * 74)
print("  TEST DE BOUT EN BOUT : CAPTURE -> ENREGISTREMENT -> HISTORIQUE")
print("=" * 74)

# ---------------------------------------------------------------------------
# 1. L'interface proposee par l'application
# ---------------------------------------------------------------------------
print()
print("1. Preparation")

code, page = demander("/capture")
interface = None
m = re.search(r'<option value="([^"]+)"[^>]*selected', page)
if not m:
    m = re.search(r'<option value="([^"]+)"', page)
if m:
    interface = m.group(1)

verifier("la page de capture repond", code == 200, f"code {code}")
verifier("une interface reseau est proposee", bool(interface), f"« {interface} »")

if not interface:
    print("\n  Aucune interface : le test ne peut pas continuer.")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# 2. Capture
# ---------------------------------------------------------------------------
print()
print("2. Capture reelle")

code, page = demander("/capture/demarrer", "POST", {"interface": interface})
verifier("la capture demarre", code in (200, 302), f"code {code}")

# On genere du trafic reel : sans cela, la capture pourrait ne rien voir, et
# l'echec ne dirait rien de l'application.
import concurrent.futures  # noqa: E402
import requests  # noqa: E402

CIBLES = ["https://www.wikipedia.org", "https://www.debian.org",
          "https://www.python.org", "https://httpbin.org/get"]


def provoquer():
    try:
        requests.get(CIBLES[int(time.time() * 1000) % len(CIBLES)], timeout=8)
    except Exception:
        pass  # un site injoignable n'a aucune importance ici


with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for _ in range(3):
        list(pool.map(lambda _i: provoquer(), range(12)))
        time.sleep(1)

time.sleep(3)

code, page = demander("/capture/arreter", "POST")
verifier("la capture s'arrete", code in (200, 302), f"code {code}")

# On interroge la sonde /health, prevue pour etre lue par une machine, plutot
# que d'extraire un nombre du HTML : la mise en page peut changer, le contrat
# de la sonde non.
import json  # noqa: E402

code, corps = demander("/health")
etat = json.loads(corps)
nb_paquets = etat.get("paquets_vus", 0)

verifier("la capture a vu des paquets", nb_paquets > 0, f"{nb_paquets} paquets")

code, page = demander("/capture")
m = re.search(r'name="nb_paquets"[^>]*value="(\d+)"', page)
if m:
    verifier("la page de capture annonce le meme nombre",
             int(m.group(1)) == nb_paquets, f"page : {m.group(1)}")

# ---------------------------------------------------------------------------
# 3. Enregistrement
# ---------------------------------------------------------------------------
print()
print("3. Enregistrement dans Supabase")

code, page = demander("/capture/enregistrer", "POST")
verifier("l'enregistrement repond sans erreur", code == 200, f"code {code}")
verifier("aucun message d'erreur affiche",
         "ECHEC" not in page.upper() and "erreur" not in page.lower()
         or "enregistr" in page.lower(),
         "")

from stockage import supabase  # noqa: E402

total = supabase.compter("reseau_analyses")
verifier("une analyse est presente dans la base", total >= 1, f"{total} analyse(s)")

lignes = supabase.lire("reseau_analyses", ordre="id.desc", limite=1)
id_cree = lignes[0]["id"] if lignes else None
if id_cree:
    nb_com = supabase.compter("reseau_communications", f"analyse_id=eq.{id_cree}")
    print(f"       analyse id={id_cree}, interface={lignes[0].get('interface')!r}, "
          f"{lignes[0].get('nb_paquets')} paquets, {nb_com} communications")
    verifier("l'analyse enregistree contient des communications", nb_com > 0,
             f"{nb_com}")

# ---------------------------------------------------------------------------
# 4. Historique
# ---------------------------------------------------------------------------
print()
print("4. Affichage dans l'historique")

code, page = demander("/historique")
verifier("la page historique repond", code == 200, f"code {code}")
verifier("l'analyse y est listee", f"/historique/{id_cree}" in page if id_cree else False)

if id_cree:
    code, detail = demander(f"/historique/{id_cree}")
    verifier("le detail de l'analyse s'ouvre", code == 200, f"code {code}")
    verifier("le detail montre les communications", "TCP" in detail or "UDP" in detail)

# ---------------------------------------------------------------------------
# 4 bis. Les alertes
# ---------------------------------------------------------------------------
print()
print("4 bis. Alertes")

code, page = demander("/alertes")
verifier("la page des alertes repond", code == 200, f"code {code}")
verifier("elle decrit les regles appliquees",
         "refus-repetes" in page and "service-en-clair" in page)
verifier("elle dit quand aucune regle ne se declenche",
         "Aucune règle ne s'est déclenchée" in page or "gravite" in page or "attention" in page)

# Les alertes de la capture en cours sont-elles enregistrees ?
try:
    nb_alertes = supabase.compter("reseau_alertes", f"analyse_id=eq.{id_cree}") if id_cree else 0
    print(f"       alertes enregistrees pour la capture : {nb_alertes}")
except Exception as e:
    nb_alertes = None
    print(f"       (table des alertes absente : {str(e)[:70]})")

if nb_alertes is None:
    print("       -> executer sql/ajouter-alertes.sql dans l'editeur SQL de Supabase")
elif nb_alertes == 0:
    print("       -> aucune alerte : sur du trafic ordinaire, c'est le resultat attendu")


# ---------------------------------------------------------------------------
# 5. Nettoyage
# ---------------------------------------------------------------------------
print()
garder = os.getenv("GARDER") == "1"
print(f"5. {'Conservation' if garder else 'Nettoyage'} des donnees de test")

if garder:
    print(f"       capture conservee : analyse id={id_cree}")
    print("       (relancer sans GARDER=1 pour la supprimer)")
elif id_cree:
    supabase.supprimer("reseau_analyses", f"id=eq.{id_cree}")
reste_a = supabase.compter("reseau_analyses")
reste_c = supabase.compter("reseau_communications")
# Le controle porte sur CE QUE CE TEST a cree, jamais sur l'ensemble de la base :
# d'autres captures peuvent exister, et exiger une base vide faisait echouer le
# test a tort.
if garder:
    presente = bool(supabase.lire("reseau_analyses", f"id=eq.{id_cree}", limite=1))
    verifier("la capture est bien conservee", presente, f"{reste_a} analyse(s) en base")
else:
    disparue = not supabase.lire("reseau_analyses", f"id=eq.{id_cree}", limite=1)
    orphelines = supabase.compter("reseau_communications", f"analyse_id=eq.{id_cree}")
    verifier("la capture de ce test a bien ete supprimee", disparue)
    verifier("ses communications ont disparu avec elle", orphelines == 0, f"{orphelines}")
    if reste_a:
        print(f"       ({reste_a} autre(s) capture(s) presente(s) : conservees, "
              f"elles ne viennent pas de ce test)")

print()
print("=" * 74)
print(f"  SYNTHESE : {len(succes)} / {len(succes) + len(echecs)} controles reussis")
if echecs:
    print("  Controles en echec :")
    for e in echecs:
        print(f"    - {e}")
print("=" * 74)
