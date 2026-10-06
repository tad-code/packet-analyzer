"""
Adaptateur entre les deux formes d'une communication.

Le projet manipule la meme realite sous deux representations :

    - la forme VIVANTE, produite par le regroupement a partir des paquets ;
      les extremites y sont des dictionnaires complets — adresse, port, nombre
      de paquets envoyes et recus, sens de l'echange ;

    - la forme ENREGISTREE, telle que la base la restitue ; les extremites y
      sont eclatees en colonnes — « ip_premiere », « port_premiere », etc.

Sans cet adaptateur, il faudrait ecrire DEUX moteurs d'explication, et les
tenir a jour tous les deux. Le jour ou une phrase change, l'historique et la
vue en direct divergeraient. C'est exactement ce que ce projet doit eviter.

Une seule regle : tout ce qui arrive a l'explication passe d'abord par ici.
"""


def _lisible(horodatage):
    """
    Rend un horodatage lisible, sans dependre d'une bibliotheque de dates.

    La base renvoie « 2026-10-06T10:39:51.123456+00:00 ». On ne garde que la
    date, l'heure et les secondes : les microsecondes et le decalage horaire
    n'apportent rien a la comprehension, et l'information complete reste dans
    la base si on en a besoin.
    """
    if not horodatage:
        return None
    texte = str(horodatage)
    if "T" not in texte:
        return texte[:19]
    date, reste = texte.split("T", 1)
    heure = reste[:8]
    return f"{date} {heure}"


def _extremite(ip, port):
    """Reconstruit une extremite sous la forme attendue par le moteur."""
    if not ip:
        return None
    extremite = {"ip": ip}
    if port is not None:
        extremite["port"] = port
    return extremite


def depuis_ligne_enregistree(ligne):
    """
    Convertit une ligne de la base en communication comprehensible par le moteur.

    Les champs absents de la base restent absents : on ne les invente pas. Le
    moteur les signalera comme « non disponible », ce qui est l'information
    juste — le sens de l'echange n'est pas conserve, et l'explication ne doit
    pas laisser croire le contraire.
    """
    if not ligne:
        return {}

    return {
        "cle": ligne.get("cle"),
        "premiere_extremite": _extremite(ligne.get("ip_premiere"), ligne.get("port_premiere")),
        "seconde_extremite": _extremite(ligne.get("ip_seconde"), ligne.get("port_seconde")),
        "initiateur": ligne.get("initiateur"),
        "protocole": ligne.get("protocole"),
        "port_service": ligne.get("port_service"),
        "service_probable": ligne.get("service_probable"),
        "nb_paquets": ligne.get("nb_paquets"),
        "octets": ligne.get("octets"),
        "duree": ligne.get("duree"),
        "debut_lisible": _lisible(ligne.get("debut")),
        "fin_lisible": _lisible(ligne.get("fin")),
        "drapeaux_vus": ligne.get("drapeaux_vus"),
        "etat": ligne.get("etat"),
        # Ces deux champs ne sont pas conserves en base. On ne les invente pas :
        # l'explication signalera leur absence, et c'est volontaire — mieux vaut
        # une lacune annoncee qu'une valeur fabriquee.
        "sens_a_vers_b": ligne.get("sens_a_vers_b"),
        "sens_b_vers_a": ligne.get("sens_b_vers_a"),
    }
