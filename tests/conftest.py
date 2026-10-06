

import pytest

def paquet(source, destination, port_source, port_destination,
           protocole="TCP", taille=100, horodatage=1000.0, drapeaux=None):

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

    return paquet
