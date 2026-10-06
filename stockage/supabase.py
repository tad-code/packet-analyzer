"""
Acces a la base Supabase.

On passe par l'API REST de Supabase, et non par une bibliotheque dediee. Trois
raisons, et la troisieme est la plus importante pour la soutenance :

    1. une seule dependance legere : « requests », deja presente ;
    2. aucune surcouche a installer ni a maintenir ;
    3. tout est directement explicable : une adresse, une methode HTTP, des
       en-tetes, un corps JSON, un code de statut. C'est exactement ce qu'on
       attend d'un etudiant qui doit defendre son code.

Le principe de fonctionnement de cette API : l'adresse de la table fait partie de
l'URL. Pour ecrire dans une table nommee « reseau_analyses », on envoie une
requete POST vers :

    https://<projet>.supabase.co/rest/v1/reseau_analyses

L'en-tete « apikey » porte la cle, et « Authorization » porte le jeton.
"""

import requests

from config import config

# Delai maximal d'attente d'une reponse. Sans cette limite, une base
# injoignable ferait attendre l'utilisateur indefiniment.
DELAI = 15


class ErreurBase(Exception):
    """
    Erreur d'acces a la base, portant un motif identifiable.

    Le champ « kind » permet a l'interface de choisir le bon message et le bon
    code HTTP, sans avoir a analyser le texte de l'erreur :

        non_configuree  l'application n'a pas recu ses identifiants
        delai           la base n'a pas repondu a temps
        reseau          la base est injoignable
        table_absente   la table n'existe pas encore (schema non execute)
        droits          la base a refuse l'operation (RLS trop stricte)
        requete         la base a refuse la donnee envoyee
        http            autre erreur renvoyee par la base
        reponse         la reponse n'etait pas exploitable
    """

    def __init__(self, message, kind="http", detail=None, statut=None):
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.detail = detail
        self.statut = statut


def _cle():
    """
    Rend la cle a employer, en preferant la cle secrete.

    La cle secrete a les droits complets et contourne la securite par ligne.
    La cle publique ne suffit pas ici : la base est volontairement fermee, donc
    la cle publique ne peut ni lire ni ecrire. On la garde comme repli pour un
    projet ou la base serait restee ouverte.
    """
    return config.supabase_cle_secrete or config.supabase_cle_publique


def disponible():
    """La base est-elle utilisable ? Rend (vrai/faux, explication)."""
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
    """Construit les en-tetes attendus par l'API REST de Supabase."""
    entetes = {
        "apikey": _cle(),
        "Authorization": f"Bearer {_cle()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if representation:
        # Demande a la base de renvoyer la ligne ecrite, afin de recuperer son
        # identifiant et sa date de creation.
        entetes["Prefer"] = "return=representation"
    return entetes


def _adresse(table, filtre=""):
    """Construit l'adresse complete d'une table."""
    url = f"{config.supabase_url}/rest/v1/{table}"
    return f"{url}?{filtre}" if filtre else url


def _traduire_erreur(reponse, table):
    """Transforme une reponse en erreur parlee par l'utilisateur."""
    code = reponse.status_code
    try:
        corps = reponse.json()
    except Exception:
        corps = {}

    # La base répond parfois un objet, parfois une liste d'objets.
    if isinstance(corps, list) and corps:
        corps = corps[0]
    if not isinstance(corps, dict):
        corps = {}

    message_base = corps.get("message") or reponse.text[:200]
    code_postgres = corps.get("code")
    detail = corps.get("details") or corps.get("hint")

    # Table inexistante : le schema SQL n'a pas encore ete execute.
    if code_postgres == "PGRST205" or "Could not find the table" in str(message_base):
        return ErreurBase(
            f"La table « {table} » n'existe pas dans la base.",
            kind="table_absente",
            detail="Exécutez le bloc sql/schema.sql dans l'éditeur SQL de Supabase.",
            statut=code,
        )

    # Droits refuses : RLS active sans politique, et cle publique employee.
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
    """
    Envoie une requete a la base et rend le contenu decode.

    Toutes les erreurs possibles sont converties en ErreurBase : aucun appelant
    n'a besoin de connaitre « requests » ni les codes de statut.
    """
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

    # Une reponse vide est normale pour certaines operations.
    if not reponse.content:
        return None

    try:
        return reponse.json()
    except ValueError:
        raise ErreurBase("La réponse de la base n'était pas du JSON exploitable.",
                         kind="reponse",
                         detail=reponse.text[:200])


# ---------------------------------------------------------------------------
# Operations utiles au projet
# ---------------------------------------------------------------------------

def inserer(table, donnees):
    """Insere une ou plusieurs lignes et rend ce que la base a enregistre."""
    if isinstance(donnees, dict):
        donnees = [donnees]
    return _appeler("POST", table, donnees=donnees, representation=True)


def lire(table, filtre="", limite=None, ordre=None):
    """Lit des lignes, avec un filtre eventuel au format PostgREST."""
    morceaux = []
    if filtre:
        morceaux.append(filtre)
    if ordre:
        morceaux.append(f"order={ordre}")
    if limite:
        morceaux.append(f"limit={limite}")
    return _appeler("GET", table, filtre="&".join(morceaux)) or []


def compter(table, filtre=""):
    """Compte les lignes sans les rapatrier."""
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
    # Format : « 0-24/135 » — le nombre apres la barre est le total.
    if "/" in contenu:
        try:
            return int(contenu.split("/")[-1])
        except ValueError:
            pass
    return len(reponse.json() or [])


def supprimer(table, filtre):
    """
    Supprime les lignes qui correspondent au filtre, et renvoie celles qui l'ont
    effectivement ete.

    Le filtre est OBLIGATOIRE, et c'est une precaution deliberee : sans lui,
    PostgREST refuserait la suppression, mais mieux vaut une erreur claire ecrite
    ici qu'un refus venu d'ailleurs. Supprimer une table entiere ne doit jamais
    pouvoir se produire par inadvertance.

    Les lignes renvoyees ne sont pas un detail : elles prouvent ce qui a
    disparu. Sans elles, on saurait seulement que la requete a abouti.
    """
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


# ---------------------------------------------------------------------------
# Enregistrement d'une analyse
# ---------------------------------------------------------------------------

def enregistrer_analyse(interface, paquets, communications, resume_par_communication=None):
    """
    Enregistre une capture et ses communications.

    On ecrit UNE analyse puis PLUSIEURS communications, et non l'inverse : la
    communication a besoin de l'identifiant de l'analyse pour etre rattachee.
    L'ordre des operations est donc impose par les relations entre les tables.

    Le volume de paquets n'est pas enregistre : une capture en produit des
    milliers, et seules les communications ont un sens d'analyse. C'est un choix
    assume, justifie dans le README.
    """
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
