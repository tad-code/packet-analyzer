"""
Enrichissement des adresses par une API externe.

Une adresse comme « 18.233.182.23 » ne dit rien a personne. L'enrichissement
repond a la question : a qui appartient cette adresse, et dans quel pays se
trouve-t-elle ?

Trois choix, et ils meritent d'etre justifies.

    - On interroge ip-api.com, qui ne demande AUCUNE cle. Un projet etudiant
      n'a pas a dependre d'un compte payant pour illustrer une fonctionnalite.

    - On interroge en lot : jusqu'a cent adresses par requete. Le service
      autorise quarante-cinq requetes par minute ; une requete par adresse
      epuiserait ce quota en quelques secondes sur une capture reelle.

    - On ne met en cache QUE ce qui a ete obtenu. Une adresse inconnue n'est
      pas enregistree comme telle : sinon une panne passagere serait figee dans
      le fichier, et l'adresse resterait sans reponse pour toujours.

L'enrichissement est un CONFORT. S'il echoue, l'analyse reste complete : les
adresses s'affichent, simplement sans pays ni operateur. Rien ne depend de lui.
"""

import json
import time
from pathlib import Path

# Le fichier de cache vit dans le projet, mais n'est pas versionne : il contient
# des adresses observees chez l'utilisateur.
CACHE = Path(__file__).resolve().parent.parent / "donnees" / "cache_enrichissement.json"

ADRESSE_API = "http://ip-api.com/batch"
CHAMPS = "status,message,query,country,countryCode,city,isp,org,as"
DELAI = 12.0
LOT_MAX = 100


def est_publique(adresse):
    """
    Indique si une adresse est routable sur Internet.

    On n'interroge pas l'API pour une adresse privee : la question n'a pas de
    sens pour elle — une adresse 192.168.x.x n'appartient a aucun pays — et
    l'envoyer a un service externe revelerait la structure du reseau local de
    l'utilisateur sans rien lui apprendre en retour.
    """
    if not adresse:
        return False

    adresse = str(adresse)
    if adresse.startswith(("127.", "169.254.", "0.", "255.")):
        return False

    # Adresses de multidiffusion et plages reservees. Elles n'appartiennent a
    # aucun pays : le service repond « reserved range », ce qui n'apprend rien
    # et consomme un quota. Rencontre sur une vraie capture, avec 239.255.255.250.
    if adresse.startswith("ff"):                  # multidiffusion IPv6
        return False
    if adresse.startswith(("22", "23", "24", "25")):   # 224.0.0.0 a 255.x.x.x
        premier = adresse.split(".")[0]
        if premier.isdigit() and 224 <= int(premier) <= 255:
            return False
    if adresse.startswith(("10.", "192.168.")):
        return False
    if adresse.startswith("172."):
        try:
            if 16 <= int(adresse.split(".")[1]) <= 31:
                return False
        except (IndexError, ValueError):
            return False
    if adresse.startswith("fe80") or adresse in ("::1",):
        return False
    if adresse.startswith(("fc", "fd")):          # adresses locales IPv6
        return False
    return True


# ---------------------------------------------------------------------------
#  Le cache
# ---------------------------------------------------------------------------

def lire_cache():
    """Rend le cache, ou un cache vide s'il est absent ou illisible."""
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        # Un cache corrompu ne doit pas empecher l'application de fonctionner :
        # on repart de zero plutot que d'echouer.
        return {}


def ecrire_cache(cache):
    """Enregistre le cache, sans jamais faire echouer l'appelant."""
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass          # un cache qu'on ne peut pas ecrire n'est pas une raison d'arreter


# ---------------------------------------------------------------------------
#  L'interrogation
# ---------------------------------------------------------------------------

def interroger_api(adresses):
    """
    Interroge l'API en lots, et rend un dictionnaire adresse -> informations.

    Leve en cas d'echec reseau : c'est a l'appelant de decider quoi faire. Ici,
    on ne decide rien — on rapporte fidelement.
    """
    import requests

    resultats = {}
    for debut in range(0, len(adresses), LOT_MAX):
        lot = adresses[debut:debut + LOT_MAX]
        reponse = requests.post(
            f"{ADRESSE_API}?fields={CHAMPS}",
            json=[{"query": ip} for ip in lot],
            timeout=DELAI,
        )
        reponse.raise_for_status()

        for info in reponse.json():
            adresse = info.get("query")
            if not adresse:
                continue
            if info.get("status") == "success":
                resultats[adresse] = {
                    "pays": info.get("country"),
                    "code_pays": info.get("countryCode"),
                    "ville": info.get("city"),
                    "fournisseur": info.get("isp"),
                    "organisation": info.get("org"),
                    "reseau": info.get("as"),
                }
            else:
                # L'API a repondu, mais sans resultat : on le retient, sinon on
                # reposerait la meme question a chaque analyse.
                resultats[adresse] = {"erreur": info.get("message") or "réponse sans résultat"}

        # On respecte la limite annoncee par le service (45 requetes par minute).
        if debut + LOT_MAX < len(adresses):
            time.sleep(1.5)

    return resultats


def enrichir(adresses, interroger=None, cache=None):
    """
    Enrichit une liste d'adresses, en n'interrogeant l'API que pour les nouvelles.

    'interroger' permet de fournir une autre source dans les tests : sans cela,
    la suite de tests dependrait d'un service externe, et echouerait le jour ou
    le reseau est coupe — pour une raison qui n'a rien a voir avec le code.

    Rend un dictionnaire adresse -> informations, et ne leve jamais : un
    enrichissement impossible n'est pas une erreur, c'est une absence.
    """
    interroger = interroger or interroger_api
    cache = lire_cache() if cache is None else cache

    a_interroger, resultats = [], []
    for adresse in adresses:
        if not est_publique(adresse):
            continue
        if adresse in cache:
            resultats.append((adresse, cache[adresse]))
        elif adresse not in a_interroger:
            a_interroger.append(adresse)

    if a_interroger:
        try:
            obtenus = interroger(a_interroger)
        except Exception as e:                        # noqa: BLE001
            # Panne reseau, service indisponible, quota depasse : on continue
            # sans enrichissement. L'analyse reste complete.
            print(f"  (enrichissement indisponible : {type(e).__name__} — {str(e)[:80]})")
            obtenus = {}

        for adresse, info in (obtenus or {}).items():
            cache[adresse] = info
            resultats.append((adresse, info))
        ecrire_cache(cache)

    return dict(resultats)


def resume(info):
    """
    Met une information d'enrichissement en une phrase courte.

    On n'ecrit que ce que l'on sait. Si le pays manque, on ne l'invente pas :
    on affiche ce qui est present, et rien d'autre.
    """
    if not info:
        return None
    if info.get("erreur"):
        return f"non identifiée ({info['erreur']})"

    morceaux = []
    if info.get("organisation") or info.get("fournisseur"):
        morceaux.append(info.get("organisation") or info.get("fournisseur"))
    if info.get("ville") and info.get("pays"):
        morceaux.append(f"{info['ville']}, {info['pays']}")
    elif info.get("pays"):
        morceaux.append(info["pays"])
    return " — ".join(morceaux) if morceaux else None
