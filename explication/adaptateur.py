

def _lisible(horodatage):

    if not horodatage:
        return None
    texte = str(horodatage)
    if "T" not in texte:
        return texte[:19]
    date, reste = texte.split("T", 1)
    heure = reste[:8]
    return f"{date} {heure}"

def _extremite(ip, port):

    if not ip:
        return None
    extremite = {"ip": ip}
    if port is not None:
        extremite["port"] = port
    return extremite

def depuis_ligne_enregistree(ligne):

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

        "active": ligne.get("etat") == "en cours",

        "sens_a_vers_b": ligne.get("sens_a_vers_b"),
        "sens_b_vers_a": ligne.get("sens_b_vers_a"),
    }
