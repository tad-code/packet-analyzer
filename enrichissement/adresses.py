

import json
import time
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "donnees" / "cache_enrichissement.json"

ADRESSE_API = "http://ip-api.com/batch"
CHAMPS = "status,message,query,country,countryCode,city,isp,org,as"
DELAI = 12.0
LOT_MAX = 100

def est_publique(adresse):

    if not adresse:
        return False

    adresse = str(adresse)
    if adresse.startswith(("127.", "169.254.", "0.", "255.")):
        return False

    if adresse.startswith("ff"):
        return False
    if adresse.startswith(("22", "23", "24", "25")):
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
    if adresse.startswith(("fc", "fd")):
        return False
    return True

def lire_cache():

    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):

        return {}

def ecrire_cache(cache):

    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass

def interroger_api(adresses):

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

                resultats[adresse] = {"erreur": info.get("message") or "réponse sans résultat"}

        if debut + LOT_MAX < len(adresses):
            time.sleep(1.5)

    return resultats

def enrichir(adresses, interroger=None, cache=None):

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
        except Exception as e:

            print(f"  (enrichissement indisponible : {type(e).__name__} — {str(e)[:80]})")
            obtenus = {}

        for adresse, info in (obtenus or {}).items():
            cache[adresse] = info
            resultats.append((adresse, info))
        ecrire_cache(cache)

    return dict(resultats)

def resume(info):

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
