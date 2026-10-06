

import requests

from config import config

DELAI = 15

class ErreurBase(Exception):

    def __init__(self, message, kind="http", detail=None, statut=None):
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.detail = detail
        self.statut = statut

def _cle():

    return config.supabase_cle_secrete or config.supabase_cle_publique

def disponible():

    if not config.supabase_url:
        return False, "L'adresse du projet Supabase n'est pas renseignée."
    if not _cle():
        return False, "Aucune clé Supabase n'est renseignée."
    if not config.supabase_cle_secrete:
        return False, ("Seule la clé publique est disponible. La base étant fermée, "
                       "elle ne permet ni lecture ni écriture : renseignez "
                       "SUPABASE_SECRET_KEY (ou SUPABASE_SERVICE_ROLE_KEY).")
    return True, "Base configurée."

def _entetes(representation=False):

    entetes = {
        "apikey": _cle(),
        "Authorization": f"Bearer {_cle()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if representation:

        entetes["Prefer"] = "return=representation"
    return entetes

def _adresse(table, filtre=""):

    url = f"{config.supabase_url}/rest/v1/{table}"
    return f"{url}?{filtre}" if filtre else url

def _traduire_erreur(reponse, table):

    code = reponse.status_code
    try:
        corps = reponse.json()
    except Exception:
        corps = {}

    if isinstance(corps, list) and corps:
        corps = corps[0]
    if not isinstance(corps, dict):
        corps = {}

    message_base = corps.get("message") or reponse.text[:200]
    code_postgres = corps.get("code")
    detail = corps.get("details") or corps.get("hint")

    if code_postgres == "PGRST205" or "Could not find the table" in str(message_base):
        return ErreurBase(
            f"La table « {table} » n'existe pas dans la base.",
            kind="table_absente",
            detail="Exécutez le bloc sql/schema.sql dans l'éditeur SQL de Supabase.",
            statut=code,
        )

    if code in (401, 403):
        return ErreurBase(
            "La base a refusé l'accès.",
            kind="droits",
            detail="La sécurité par ligne est active et aucune politique n'autorise "
                   "cette opération. Vérifiez que SUPABASE_SECRET_KEY est bien renseignée : "
                   "la clé publique ne suffit pas.",
            statut=code,
        )

    if code == 404:
        return ErreurBase(
            f"La table « {table} » est introuvable.",
            kind="table_absente",
            detail="Vérifiez son nom, ou exécutez sql/schema.sql.",
            statut=code,
        )

    if code == 400 or code == 409:
        return ErreurBase(
            "La base a refusé la donnée envoyée.",
            kind="requete",
            detail=str(message_base),
            statut=code,
        )

    return ErreurBase(
        "La base a renvoyé une erreur.",
        kind="http",
        detail=f"{message_base} (détail : {detail})" if detail else str(message_base),
        statut=code,
    )

def _appeler(methode, table, donnees=None, filtre="", representation=False):

    if not config.supabase_url:
        raise ErreurBase("L'adresse Supabase n'est pas renseignée.",
                         kind="non_configuree")

    try:
        reponse = requests.request(
            methode,
            _adresse(table, filtre),
            headers=_entetes(representation),
            json=donnees,
            timeout=DELAI,
        )
    except requests.exceptions.Timeout:
        raise ErreurBase("La base n'a pas répondu dans le délai imparti.",
                         kind="delai",
                         detail=f"Délai dépassé : {DELAI} secondes.")
    except requests.exceptions.RequestException as e:
        raise ErreurBase("La base est injoignable.",
                         kind="reseau",
                         detail=f"{type(e).__name__} : {e}")

    if reponse.status_code >= 400:
        raise _traduire_erreur(reponse, table)

    if not reponse.content:
        return None

    try:
        return reponse.json()
    except ValueError:
        raise ErreurBase("La réponse de la base n'était pas du JSON exploitable.",
                         kind="reponse",
                         detail=reponse.text[:200])

def inserer(table, donnees):

    if isinstance(donnees, dict):
        donnees = [donnees]
    return _appeler("POST", table, donnees=donnees, representation=True)

def lire(table, filtre="", limite=None, ordre=None):

    morceaux = []
    if filtre:
        morceaux.append(filtre)
    if ordre:
        morceaux.append(f"order={ordre}")
    if limite:
        morceaux.append(f"limit={limite}")
    return _appeler("GET", table, filtre="&".join(morceaux)) or []

def compter(table, filtre=""):

    if not config.supabase_url:
        raise ErreurBase("L'adresse Supabase n'est pas renseignée.",
                         kind="non_configuree")
    entetes = _entetes()
    entetes["Prefer"] = "count=exact"
    entetes["Range"] = "0-0"
    try:
        reponse = requests.get(_adresse(table, filtre), headers=entetes, timeout=DELAI)
    except requests.exceptions.Timeout:
        raise ErreurBase("La base n'a pas répondu dans le délai imparti.", kind="delai")
    except requests.exceptions.RequestException as e:
        raise ErreurBase("La base est injoignable.", kind="reseau", detail=str(e))

    if reponse.status_code >= 400:
        raise _traduire_erreur(reponse, table)

    contenu = reponse.headers.get("Content-Range", "")

    if "/" in contenu:
        try:
            return int(contenu.split("/")[-1])
        except ValueError:
            pass
    return len(reponse.json() or [])

def supprimer(table, filtre):

    if not filtre:
        raise ErreurBase("La suppression exige un filtre : refus d'effacer une table entiere.",
                         kind="requete")

    if not config.supabase_url:
        raise ErreurBase("L'adresse Supabase n'est pas renseignée.",
                         kind="non_configuree")

    entetes = _entetes(representation=True)
    try:
        reponse = requests.delete(_adresse(table, filtre), headers=entetes, timeout=DELAI)
    except requests.exceptions.Timeout:
        raise ErreurBase("La base n'a pas répondu dans le délai imparti.", kind="delai")
    except requests.exceptions.RequestException as e:
        raise ErreurBase("La base est injoignable.", kind="reseau", detail=str(e))

    if reponse.status_code >= 400:
        raise _traduire_erreur(reponse, table)

    try:
        return reponse.json() or []
    except ValueError:
        return []

def enregistrer_alertes(analyse_id, alertes):

    if not alertes:
        return 0

    lignes = [{
        "analyse_id": analyse_id,
        "regle": a.get("regle"),
        "gravite": a.get("gravite"),
        "titre": a.get("titre"),
        "explication": a.get("explication"),
        "base": a.get("base"),
        "conseil": a.get("conseil"),
        "nb_communications": a.get("nb_communications", 0),
    } for a in alertes]

    ecrites = inserer("reseau_alertes", lignes)
    return len(ecrites or [])

def enregistrer_analyse(interface, paquets, communications, resume_par_communication=None):

    resume_par_communication = resume_par_communication or {}

    total_octets = sum(c.get("octets") or 0 for c in communications)

    analyse = inserer("reseau_analyses", {
        "interface": interface,
        "etat": "terminee",
        "nb_paquets": paquets,
        "nb_communications": len(communications),
        "octets": total_octets,
    })
    if not analyse:
        raise ErreurBase("La base n'a pas renvoyé l'analyse enregistrée.", kind="reponse")

    identifiant = analyse[0]["id"]

    if not communications:
        return identifiant, 0

    lignes = []
    for c in communications:
        premiere = c.get("premiere_extremite") or {}
        seconde = c.get("seconde_extremite") or {}
        lignes.append({
            "analyse_id": identifiant,
            "cle": c.get("cle"),
            "ip_premiere": premiere.get("ip"),
            "port_premiere": premiere.get("port"),
            "ip_seconde": seconde.get("ip"),
            "port_seconde": seconde.get("port"),
            "initiateur": c.get("initiateur"),
            "protocole": c.get("protocole"),
            "port_service": c.get("port_service"),
            "service_probable": c.get("service_probable"),
            "nb_paquets": c.get("nb_paquets") or 0,
            "octets": c.get("octets") or 0,
            "duree": c.get("duree"),
            "etat": c.get("etat"),
            "drapeaux_vus": c.get("drapeaux_vus"),
            "resume": resume_par_communication.get(c.get("cle")),
        })

    ecrites = inserer("reseau_communications", lignes)
    return identifiant, len(ecrites or [])
