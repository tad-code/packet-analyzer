"""
Outils communs aux tests.

Les tests ne capturent aucun paquet et ne touchent a aucun reseau : ils
fabriquent des paquets a la main, sous forme de dictionnaires. C'est possible
parce que le regroupement est une fonction pure — elle ne connait que des
donnees. Consequence : les tests s'executent partout, en une fraction de
seconde, et donnent toujours le meme resultat.
"""

import pytest


def paquet(source, destination, port_source, port_destination,
           protocole="TCP", taille=100, horodatage=1000.0, drapeaux=None):
    """
    Fabrique un paquet deja analyse, tel que le produirait analyse.paquet.

    Les valeurs par defaut decrivent un paquet TCP ordinaire ; chaque test ne
    precise que ce qui l'interesse.
    """
    return {
        "rang": 1,
        "horodatage": horodatage,
        "heure_lisible": None,
        "taille": taille,
        "source": source,
        "destination": destination,
        "protocole_ip": "TCP" if protocole == "TCP" else "UDP",
        "protocole_transport": protocole,
        "protocole_applicatif": None,
        "port_source": port_source,
        "port_destination": port_destination,
        "drapeaux": drapeaux,
        "ttl": 64,
        "numero_sequence": None,
        "domaine_demande": None,
        "resume": "",
        "service_probable": None,
    }


@pytest.fixture
def fabrique():
    """Rend la fabrique de paquets aux tests qui la demandent."""
    return paquet
