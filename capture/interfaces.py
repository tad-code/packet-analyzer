

from scapy.all import conf

def _texte(valeur):

    if valeur is None:
        return None
    texte = str(valeur).strip()
    return texte if texte else None

def est_virtuelle(nom, description):

    morceaux = f"{nom} {description}".lower()
    indices = ("vmware", "virtual", "vmnet", "hyper-v", "vethernet", "loopback",
               "direct", "vbox", "tap", "tun", "bluetooth")
    return any(i in morceaux for i in indices)

def lister_interfaces():

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

            continue

    resultat.sort(key=lambda i: (i["bouclage"], i["virtuelle"], not i["adresse_ip"], i["nom"]))
    return resultat

def proposer_interface(interfaces, nom_souhaite=None):

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
