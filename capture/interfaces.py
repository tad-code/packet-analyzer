"""
Inventaire des interfaces reseau.

Une interface, c'est une carte reseau : le Wi-Fi, le cable Ethernet, une carte
virtuelle, ou encore l'interface de bouclage (loopback) qui sert au trafic interne
a la machine.

Pourquoi ce module est indispensable : sur la machine de l'analyste, Scapy voit
souvent une dizaine d'interfaces, dont plusieurs ne transportent aucun trafic
reel (cartes virtuelles creees par des logiciels, adaptateurs de diffusion directe
Wi-Fi). L'utilisateur doit pouvoir les distinguer, sinon il capture sur la
mauvaise et ne voit rien.
"""

from scapy.all import conf


def _texte(valeur):
    """Rend une valeur affichable, ou None si elle est absente."""
    if valeur is None:
        return None
    texte = str(valeur).strip()
    return texte if texte else None


def est_virtuelle(nom, description):
    """
    Devine si une interface est virtuelle, d'apres son nom et sa description.

    On ne fait que signaler : l'utilisateur reste libre de capturer dessus. Mais
    un avertissement evite la confusion la plus frequente de ce genre d'outil.
    """
    morceaux = f"{nom} {description}".lower()
    indices = ("vmware", "virtual", "vmnet", "hyper-v", "vethernet", "loopback",
               "direct", "vbox", "tap", "tun", "bluetooth")
    return any(i in morceaux for i in indices)


def lister_interfaces():
    """
    Rend la liste des interfaces, sous forme de dictionnaires simples.

    On n'expose pas les objets de Scapy vers l'interface web : seuls des
    dictionnaires de chaines de caracteres traversent le programme. C'est ce qui
    permet au reste du code d'ignorer comment Scapy fonctionne.

    En cas d'echec de lecture, on rend une liste vide : l'appelant affichera
    « aucune interface detectee » plutot que de planter.
    """
    resultat = []

    try:
        interfaces_scapy = conf.ifaces.values()
    except Exception:
        return resultat

    for iface in interfaces_scapy:
        try:
            nom = _texte(getattr(iface, "name", None))
            if not nom:
                continue

            description = _texte(getattr(iface, "description", None)) or ""
            adresse_ip = _texte(getattr(iface, "ip", None))
            adresse_mac = _texte(getattr(iface, "mac", None))

            resultat.append({
                "nom": nom,
                "description": description,
                "adresse_ip": adresse_ip,
                "adresse_mac": adresse_mac,
                "virtuelle": est_virtuelle(nom, description),
                "bouclage": nom.lower().startswith("loopback") or adresse_ip == "127.0.0.1",
            })
        except Exception:
            # Une interface illisible ne doit pas empecher de lister les autres.
            continue

    # On presente d'abord les interfaces qui ont une adresse IP reelle : ce sont
    # celles qui transportent du trafic.
    resultat.sort(key=lambda i: (i["bouclage"], i["virtuelle"], not i["adresse_ip"], i["nom"]))
    return resultat


def proposer_interface(interfaces, nom_souhaite=None):
    """
    Choisit l'interface a utiliser.

    Ordre de preference : celle que l'utilisateur a demandee, puis celle qui est
    enregistree dans la configuration, puis la premiere interface a la fois
    utile et non virtuelle.
    """
    noms = {i["nom"] for i in interfaces}

    if nom_souhaite and nom_souhaite in noms:
        return nom_souhaite

    for iface in interfaces:
        if iface["adresse_ip"] and not iface["bouclage"] and not iface["virtuelle"]:
            return iface["nom"]

    for iface in interfaces:
        if iface["adresse_ip"]:
            return iface["nom"]

    return interfaces[0]["nom"] if interfaces else None
