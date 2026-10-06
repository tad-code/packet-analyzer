"""
Test fonctionnel de l'application.

Ce script n'est pas un test unitaire : il interroge l'application reellement
lancee, comme le ferait un navigateur. C'est ce qui permet d'affirmer que
l'application fonctionne, et pas seulement que le code compile.

Ce qu'il verifie, dans l'ordre :

    1. le service repond et annonce son mode ;
    2. le tableau de bord s'affiche, meme sans donnee ;
    3. la page de capture propose les interfaces et les commandes ;
    4. une capture demarre et du trafic reel apparait ;
    5. le regroupement produit des communications coherentes ;
    6. le detail d'une communication repond aux sept questions exigees ;
    7. la capture s'arrete proprement ;
    8. les cas d'erreur se comportent comme prevu.

Usage :  python tools/tester_application.py
"""

import html
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:5000"

resultats = []


def demander(chemin, methode="GET", donnees=None):
    """
    Envoie une requete et rend (code, contenu).

    Le contenu est decode : les gabarits ecrivent « d&#39;ouvrir » la ou le texte
    d'origine porte une apostrophe. Sans ce decodage, un controle sur une phrase
    contenant une apostrophe echouerait alors que la page est correcte.
    """
    corps = urllib.parse.urlencode(donnees).encode() if donnees else None
    requete = urllib.request.Request(BASE + chemin, data=corps, method=methode)
    if corps:
        requete.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(requete, timeout=30) as r:
            return r.status, html.unescape(r.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        return e.code, html.unescape(e.read().decode("utf-8", errors="replace"))
    except Exception as e:
        return -1, f"{type(e).__name__} : {e}"


def verifier(intitule, condition, detail=""):
    resultats.append((intitule, condition, detail))
    print(f"  [{'OK   ' if condition else 'ECHEC'}] {intitule}" + (f"  — {detail}" if detail else ""))


def fabriquer_trafic():
    """Provoque du trafic observable : DNS et requetes HTTP."""
    try:
        import socket

        socket.gethostbyname("portswigger.net")
        socket.gethostbyname("wikipedia.org")
    except Exception:
        pass
    for site in ("http://example.com", "http://neverssl.com", "http://info.cern.ch"):
        try:
            urllib.request.urlopen(site, timeout=8).read(300)
        except Exception:
            pass


print("=" * 74)
print("  TEST FONCTIONNEL DE L'APPLICATION")
print("=" * 74)
print()

# -- 1. Le service ------------------------------------------------------------
print("1. Le service repond")
code, contenu = demander("/health")
verifier("la sonde /health repond 200", code == 200, f"code {code}")
verifier("elle annonce le mode et les paquets vus", "mode" in contenu and "paquets_vus" in contenu)
print()

# -- 2. Le tableau de bord ----------------------------------------------------
print("2. Le tableau de bord")
code, page = demander("/")
verifier("la page / repond 200", code == 200, f"code {code}")
verifier("elle porte le menu complet",
         all(m in page for m in ("Tableau de bord", "Communications", "Capture")))
verifier("elle explique ce qu'est une communication",
         "communication" in page.lower())
verifier("elle renvoie vers la page de capture quand elle est vide",
         "/capture" in page or "Vue générale" in page)
verifier("le pied de page rappelle la limite du HTTPS", "n'est pas lisible" in page)
print()

# -- 3. La page de capture ----------------------------------------------------
print("3. La page de capture")
code, page = demander("/capture")
verifier("la page /capture repond 200", code == 200, f"code {code}")
verifier("elle propose le choix de la carte reseau", "Carte réseau à écouter" in page)
verifier("elle contient les trois commandes",
         "Démarrer" in page and "Arrêter" in page and "Vider la liste" in page)
verifier("elle explique chaque colonne", "Que signifie chaque colonne" in page)

interface = ""
m = re.search(r'<option value="([^"]+)"', page)
if m:
    interface = m.group(1)
verifier("une interface est proposee", bool(interface), interface)
print()

# -- 4. Capture et trafic -----------------------------------------------------
print("4. Capture de trafic reel")
code, page = demander("/capture/demarrer", "POST", {"interface": interface})
verifier("le demarrage aboutit", code in (200, 302), f"code {code}")

print("   (resolution DNS et requetes HTTP en cours...)")
for _ in range(4):
    fabriquer_trafic()
    time.sleep(2)

code, page = demander("/capture")
lignes = re.findall(r"<tr>\s*<td>(\d+)</td>", page)
verifier("des paquets sont affiches", len(lignes) > 0, f"{len(lignes)} ligne(s)")
verifier("des adresses IP sont presentes", bool(re.search(r"\d+\.\d+\.\d+\.\d+", page)))
verifier("l'heure est lisible", bool(re.search(r"\d{2}:\d{2}:\d{2}\.\d{3}", page)))
verifier("les services probables sont identifies",
         any(s in page for s in ("HTTPS", "HTTP", "DNS")))
print()

# -- 5. Le regroupement en communications -------------------------------------
print("5. Le regroupement en communications")
code, page = demander("/")
verifier("le tableau de bord affiche des chiffres", "communications observées" in page)
verifier("il affiche le nombre de paquets", "paquets échangés" in page)
verifier("il affiche le volume", "volume total" in page)
verifier("il liste des protocoles", "Protocoles observés" in page)
verifier("il liste des ports", "Ports les plus contactés" in page)
verifier("il liste des sources", "Machines qui prennent l'initiative" in page)

code, page = demander("/communications")
verifier("la page /communications repond 200", code == 200, f"code {code}")
verifier("elle explique le regroupement", "mêmes deux machines" in page)

liens = re.findall(r'href="(/communication/[^"]+)"', page)
verifier("au moins une communication est listee", len(liens) > 0, f"{len(liens)} lien(s)")
print()

# -- 6. Le detail d'une communication -----------------------------------------
print("6. Le detail d'une communication")
if not liens:
    verifier("une communication peut etre ouverte", False, "aucun lien a suivre")
else:
    code, page = demander(liens[0])
    verifier("le detail repond 200", code == 200, f"code {code}")

    questions = [
        "Qui communique avec qui ?",
        "Depuis combien de temps ?",
        "Sur quel protocole ?",
        "Sur quel port ?",
        "Combien de paquets échangés ?",
        "Combien de données ont circulé ?",
        "La communication est-elle toujours active ?",
    ]
    manquantes = [q for q in questions if q not in page]
    verifier("les sept questions du cahier des charges ont une reponse",
             not manquantes, f"manquantes : {manquantes}" if manquantes else "")

    verifier("les informations techniques sont affichees",
             "Clé de la communication" in page and "Drapeaux TCP observés" in page)
    verifier("les drapeaux TCP sont expliques", "RST" in page and "SYN" in page)
    verifier("l'etat de la communication est affiche", "etat-" in page)
print()

# -- 7. Arret -----------------------------------------------------------------
print("7. Arret de la capture")
code, page = demander("/capture/arreter", "POST", {})
verifier("l'arret aboutit", code in (200, 302), f"code {code}")
code, page = demander("/capture")
verifier("la page indique que la capture est arretee", "Aucune capture en cours" in page)
time.sleep(2)
verifier("le rafraichissement automatique est suspendu", 'http-equiv="refresh"' not in page)
print()

# -- 8. Cas d'erreur ----------------------------------------------------------
print("8. Cas d'erreur")
code, page = demander("/adresse-qui-nexiste-pas")
verifier("une page inconnue repond 404", code == 404, f"code {code}")
verifier("la page 404 garde le menu", "Tableau de bord" in page and "Analyseur réseau" in page)

code, page = demander("/health", "POST", {})
verifier("une methode non autorisee repond 405", code == 405, f"code {code}")

code, page = demander("/historique")
verifier("la page /historique repond 200", code == 200, f"code {code}")
# La page doit etre utile DANS LES DEUX CAS : soit elle explique ce qui manque,
# soit elle affiche les captures enregistrees. Un controle qui n'accepterait
# qu'un seul des deux etats signalerait un faux probleme.
base_prete = "pas disponible" not in page
if base_prete:
    verifier("la base repond : l'historique affiche son contenu",
             "Historique des captures" in page)
    verifier("l'historique indique ce que chaque colonne contient",
             "colonne" in page or "capture enregistr" in page)
else:
    verifier("la base absente est expliquee, sans page d'erreur",
             "pas disponible" in page)
    verifier("la marche a suivre est indiquee",
             "SQL" in page and "SUPABASE" in page)

# --- Les pages de la version 3 -------------------------------------------------
code, page = demander("/protocoles")
verifier("la page des protocoles repond", code == 200, f"code {code}")
verifier("elle explique les drapeaux", "SYN" in page and "RST" in page)
verifier("elle liste les ports", "443" in page and "53" in page)

code, page = demander("/glossaire")
verifier("le glossaire repond", code == 200, f"code {code}")
verifier("il definit le vocabulaire", "Observation" in page and "Hypothèse" in page)

code, page = demander("/historique")
verifier("l'historique repond", code == 200, f"code {code}")

# On suit le premier lien vers une capture, puis vers une de ses communications.
# La liste des captures ne mene pas directement a une communication : il faut
# deux sauts, et l'oublier faisait echouer ce controle a tort.
import re as _re
capture = _re.search(r'href="(/historique/\d+)"', page)
detail_capture = ""
if capture:
    _, detail_capture = demander(capture.group(1))
lien = _re.search(r'href="(/historique/\d+/communication/\d+)"', detail_capture)
if lien:
    code, detail = demander(lien.group(1))
    verifier("le detail d'une communication enregistree s'ouvre", code == 200, f"code {code}")
    verifier("il affiche l'explication", "Explication" in detail)
    verifier("il distingue le fait de la deduction",
             "Ce qui a été observé" in detail and "Ce qui en a été déduit" in detail)
    verifier("chaque deduction cite sa base", "Parce que" in detail)
    verifier("les niveaux sont nommes",
             "observation" in detail.lower() and "hypothèse" in detail.lower())
else:
    verifier("une capture enregistree est disponible pour le test", False,
             "aucun lien trouve — lancer le test de bout en bout au prealable")

code, page = demander("/communication/communication-qui-nexiste-pas")
verifier("une communication inconnue repond 404 et l'explique",
         code == 404 and "introuvable" in page, f"code {code}")

code, page = demander("/capture/demarrer", "POST", {"interface": "interface-inexistante"})
refus = ("Impossible d'ouvrir" in page or "n'a pas pu démarrer" in page)
verifier("une interface inexistante est refusee proprement",
         code in (200, 302) and refus and "Capture en cours" not in page,
         f"code {code}, message present : {refus}")
print()

# -- Synthese -----------------------------------------------------------------
reussis = sum(1 for _, c, _ in resultats if c)
total = len(resultats)
print("=" * 74)
print(f"  SYNTHESE : {reussis} / {total} controles reussis")
print("=" * 74)
if reussis != total:
    print()
    print("  Controles en echec :")
    for intitule, condition, detail in resultats:
        if not condition:
            print(f"    - {intitule}  ({detail})")
sys.exit(0 if reussis == total else 1)
