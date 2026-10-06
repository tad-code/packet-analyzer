

from analyse.protocoles import nom_du_port

INDISPONIBLE = "non disponible"

def _valeur(valeur, unite="", manquant=INDISPONIBLE):

    if valeur is None or valeur == "":
        return manquant
    if unite:
        return f"{valeur} {unite}"
    return str(valeur)

from analyse.adresses import adresse_complete

def _extremite(extremite):

    if not extremite:
        return None
    return adresse_complete(extremite.get("ip"), extremite.get("port"))

def _volume(octets):

    if octets is None:
        return None
    if octets >= 1024 * 1024:
        return f"{octets / (1024 * 1024):.2f} Mo"
    if octets >= 1024:
        return f"{octets / 1024:.1f} Ko"
    return f"{octets} octets"

def _duree(secondes):

    if secondes is None:
        return None
    if secondes >= 60:
        return f"{secondes / 60:.1f} min"
    return f"{secondes:.1f} s"

def faits_observes(communication):

    faits = []

    def ajouter(champ, libelle, valeur):
        faits.append({
            "champ": champ,
            "libelle": libelle,
            "valeur": _valeur(valeur),
            "disponible": valeur is not None and valeur != "",
        })

    ajouter("premiere_extremite", "Première extrémité", _extremite(communication.get("premiere_extremite")))
    ajouter("seconde_extremite", "Seconde extrémité", _extremite(communication.get("seconde_extremite")))
    ajouter("initiateur", "Machine à l'origine", communication.get("initiateur"))
    ajouter("protocole", "Protocole", communication.get("protocole"))

    port_service = communication.get("port_service")
    ajouter("port_service", "Port du service", port_service)

    nom_port = nom_du_port(port_service) if port_service is not None else None
    ajouter("service_probable", "Service habituellement associé à ce port", nom_port)

    ajouter("nb_paquets", "Nombre de paquets échangés", communication.get("nb_paquets"))
    ajouter("octets", "Volume échangé", _volume(communication.get("octets")))
    ajouter("duree", "Durée de la communication", _duree(communication.get("duree")))
    ajouter("debut_lisible", "Premier paquet observé", communication.get("debut_lisible"))
    ajouter("fin_lisible", "Dernier paquet observé", communication.get("fin_lisible"))
    ajouter("drapeaux_vus", "Drapeaux TCP observés", communication.get("drapeaux_vus"))
    ajouter("sens_a_vers_b", "Paquets de la première vers la seconde extrémité",
            communication.get("sens_a_vers_b"))
    ajouter("sens_b_vers_a", "Paquets de la seconde vers la première extrémité",
            communication.get("sens_b_vers_a"))
    ajouter("etat", "État déduit des drapeaux", communication.get("etat"))

    return faits

def faits_disponibles(communication):
        return sum(1 for f in faits_observes(communication) if f["disponible"])

def resume_chiffre(communication):

    parties = []

    premiere = communication.get("premiere_extremite") or {}
    seconde = communication.get("seconde_extremite") or {}
    if premiere.get("ip") and seconde.get("ip"):
        parties.append(
            f"Communication de {_extremite(premiere)} vers {_extremite(seconde)}"
        )

    if communication.get("protocole"):
        parties.append(f"protocole {communication['protocole']}")

    if communication.get("port_service") is not None:
        nom = nom_du_port(communication["port_service"])
        if nom:
            parties.append(f"port {communication['port_service']} ({nom})")
        else:
            parties.append(f"port {communication['port_service']}")

    if communication.get("nb_paquets") is not None:
        parties.append(f"{communication['nb_paquets']} paquets")

    if communication.get("octets") is not None:
        parties.append(_volume(communication["octets"]))

    if communication.get("duree") is not None:
        parties.append(f"sur {_duree(communication['duree'])}")

    if not parties:
        return "Aucune donnée exploitable n'a été observée pour cette communication."

    return " · ".join(parties) + "."
