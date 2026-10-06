"""
Extraction des faits observes.

Ce module repond a une seule question :

    « Qu'est-ce que l'analyseur a REELLEMENT vu ? »

Aucune deduction, aucune supposition, aucune phrase d'interpretation. Un fait est
une valeur extraite d'un paquet, avec le nom du champ dont elle vient.

La regle qui gouverne tout ce fichier : un champ absent donne « non disponible ».
On n'invente jamais une valeur, et on ne met jamais un tiret muet : l'utilisateur
doit savoir que l'information manque, et non croire qu'elle est vide.

C'est la securite principale contre le risque d'inventer une conclusion. Elle est
structurelle, et non une simple recommandation : l'interpretation, elle, vit dans
phrases.py et ne peut lire que ce que ce module a produit.
"""

from analyse.protocoles import nom_du_port

# Ce qu'on affiche quand une information n'a pas ete observee.
INDISPONIBLE = "non disponible"


def _valeur(valeur, unite="", manquant=INDISPONIBLE):
    """Presente une valeur, ou dit clairement qu'elle manque."""
    if valeur is None or valeur == "":
        return manquant
    if unite:
        return f"{valeur} {unite}"
    return str(valeur)


# Le formatage des adresses vit dans « analyse » : le regroupement en a
# besoin aussi, et il ne doit pas dependre de l'etage des phrases.
from analyse.adresses import adresse_complete  # noqa: F401


def _extremite(extremite):
    """
    Presente une extremite « adresse:port », ou None si elle est inconnue.

    On rend None et non la chaine « non disponible » : c'est le role de _valeur()
    de decider comment afficher une absence. Rendre ici une chaine deja formatee
    faisait passer le fait pour disponible, alors que sa valeur disait le
    contraire — le test l'a attrape.
    """
    if not extremite:
        return None
    return adresse_complete(extremite.get("ip"), extremite.get("port"))


def _volume(octets):
    """Presente un volume dans une unite lisible, ou None s'il est inconnu."""
    if octets is None:
        return None
    if octets >= 1024 * 1024:
        return f"{octets / (1024 * 1024):.2f} Mo"
    if octets >= 1024:
        return f"{octets / 1024:.1f} Ko"
    return f"{octets} octets"


def _duree(secondes):
    """Presente une duree dans une unite lisible, ou None si elle est inconnue."""
    if secondes is None:
        return None
    if secondes >= 60:
        return f"{secondes / 60:.1f} min"
    return f"{secondes:.1f} s"


def faits_observes(communication):
    """
    Rend la liste des faits observes pour une communication.

    Chaque fait porte trois elements :

        champ   : le nom du champ d'origine — c'est la traçabilite, on peut
                  remonter jusqu'au paquet ;
        libelle : ce que l'on a regarde ;
        valeur  : ce que l'on a trouve, ou « non disponible ».
    """
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
    """Nombre de faits réellement observes, et non « non disponible »."""
    return sum(1 for f in faits_observes(communication) if f["disponible"])


def resume_chiffre(communication):
    """
    Resume chiffre : ce qui a ete observe, sans aucune interpretation.

    Sert de phrase d'ouverture, et de point de depart a l'utilisateur qui veut
    verifier par lui-meme.
    """
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
