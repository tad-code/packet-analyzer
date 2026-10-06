

from datetime import datetime
from analyse.adresses import adresse_complete

from analyse.paquet import service_probable

DELAI_INACTIVITE = 60.0

DRAPEAUX_OUVERTURE = "S"
DRAPEAUX_FERMETURE = "F"
DRAPEAUX_REFUS = "R"

def cle_communication(paquet):

    protocole = paquet.get("protocole_transport") or paquet.get("protocole_ip") or "?"
    extremite_source = (str(paquet.get("source") or "?"), paquet.get("port_source"))
    extremite_destination = (str(paquet.get("destination") or "?"), paquet.get("port_destination"))

    if extremite_source <= extremite_destination:
        premier, second = extremite_source, extremite_destination
    else:
        premier, second = extremite_destination, extremite_source

    return f"{protocole}|{premier[0]}:{premier[1]}|{second[0]}:{second[1]}"

def port_du_service(port_a, port_b):

    if port_a is None and port_b is None:
        return None
    if port_a is None:
        return port_b
    if port_b is None:
        return port_a

    connu_a = service_probable(port_a) is not None
    connu_b = service_probable(port_b) is not None
    if connu_a and not connu_b:
        return port_a
    if connu_b and not connu_a:
        return port_b

    return min(port_a, port_b)

def etat_communication(drapeaux_vus, active):

    if DRAPEAUX_REFUS in drapeaux_vus:
        return "refusee"
    if DRAPEAUX_FERMETURE in drapeaux_vus:
        return "terminee"
    if not active:
        return "inactive"
    if DRAPEAUX_OUVERTURE in drapeaux_vus:

        return "en cours"
    return "en cours"

def _heure_lisible(horodatage):

    if not horodatage:
        return None
    try:
        return datetime.fromtimestamp(horodatage).strftime("%H:%M:%S")
    except Exception:
        return None

def regrouper(paquets, delai_inactivite=DELAI_INACTIVITE, maintenant=None):

    communications = {}

    for paquet in paquets:
        try:
            cle = cle_communication(paquet)
        except Exception:

            continue

        if cle not in communications:

            protocole = paquet.get("protocole_transport") or paquet.get("protocole_ip") or "inconnu"
            port_a = paquet.get("port_source")
            port_b = paquet.get("port_destination")

            communications[cle] = {
                "cle": cle,
                "protocole": protocole,
                "premiere_extremite": {
                    "ip": paquet.get("source"),
                    "port": port_a,
                },
                "seconde_extremite": {
                    "ip": paquet.get("destination"),
                    "port": port_b,
                },

                "initiateur": paquet.get("source"),
                "port_service": port_du_service(port_a, port_b),
                "nb_paquets": 0,
                "octets": 0,
                "debut": None,
                "fin": None,
                "etaient_des_drapeaux": set(),
                "sens_a_vers_b": 0,
                "sens_b_vers_a": 0,
            }

        communication = communications[cle]

        communication["nb_paquets"] += 1
        if paquet.get("taille"):
            communication["octets"] += paquet["taille"]

        horodatage = paquet.get("horodatage")
        if horodatage:
            if communication["debut"] is None or horodatage < communication["debut"]:
                communication["debut"] = horodatage
            if communication["fin"] is None or horodatage > communication["fin"]:
                communication["fin"] = horodatage

        drapeaux = paquet.get("drapeaux")
        if drapeaux:
            for lettre in str(drapeaux):
                communication["etaient_des_drapeaux"].add(lettre)

        if paquet.get("source") == communication["premiere_extremite"]["ip"]:
            communication["sens_a_vers_b"] += 1
        else:
            communication["sens_b_vers_a"] += 1

    instant_reference = maintenant
    if instant_reference is None:
        instants = [c["fin"] for c in communications.values() if c["fin"]]
        instant_reference = max(instants) if instants else None

    resultat = []
    for communication in communications.values():
        debut = communication["debut"]
        fin = communication["fin"]
        duree = (fin - debut) if (debut and fin) else 0.0

        drapeaux_vus = communication["etaient_des_drapeaux"]

        fermee = (DRAPEAUX_FERMETURE in drapeaux_vus) or (DRAPEAUX_REFUS in drapeaux_vus)

        active = not fermee
        if active and instant_reference and fin:
            active = (instant_reference - fin) <= delai_inactivite
        communication["etat"] = etat_communication(drapeaux_vus, active)
        communication["active"] = active
        communication["drapeaux_vus"] = "".join(sorted(drapeaux_vus)) or None
        communication["duree"] = round(duree, 3)
        communication["debut_lisible"] = _heure_lisible(debut)
        communication["fin_lisible"] = _heure_lisible(fin)
        communication["service_probable"] = service_probable(communication["port_service"])
        communication["etaient_des_drapeaux"] = None

        resultat.append(communication)

    resultat.sort(key=lambda c: c["fin"] or 0, reverse=True)
    return resultat

def statistiques(communications):

    from collections import Counter

    total_paquets = sum(c["nb_paquets"] for c in communications)
    total_octets = sum(c["octets"] for c in communications)

    protocoles = Counter(c["protocole"] for c in communications)
    services = Counter(c["service_probable"] for c in communications if c["service_probable"])

    sources = Counter()
    destinations = Counter()
    ports = Counter()

    for c in communications:
        if c["initiateur"]:

            sources[c["initiateur"]] += c["nb_paquets"]

            for extremite in (c["premiere_extremite"], c["seconde_extremite"]):
                if extremite["ip"] and extremite["ip"] != c["initiateur"]:
                    destinations[extremite["ip"]] += c["nb_paquets"]

        if c["port_service"] is not None:
            ports[c["port_service"]] += 1

    return {
        "nb_communications": len(communications),
        "nb_paquets": total_paquets,
        "octets": total_octets,
        "protocoles": protocoles.most_common(),
        "services": services.most_common(10),
        "principales_sources": sources.most_common(8),
        "principales_destinations": destinations.most_common(8),
        "ports_frequents": ports.most_common(10),
        "communications_actives": sum(1 for c in communications if c["active"]),
        "communications_terminees": sum(1 for c in communications if c["etat"] in ("terminee", "inactive")),
        "communications_refusees": sum(1 for c in communications if c["etat"] == "refusee"),
    }

def repondre_questions(communication):

    a = communication["premiere_extremite"]
    b = communication["seconde_extremite"]

    def afficher(extremite):

        rendu = adresse_complete(extremite["ip"], extremite["port"])
        return rendu if rendu else "adresse non disponible"

    duree = communication["duree"]
    if duree >= 60:
        duree_texte = f"{duree / 60:.1f} min"
    else:
        duree_texte = f"{duree:.1f} s"

    volume = communication["octets"]
    if volume >= 1024 * 1024:
        volume_texte = f"{volume / (1024 * 1024):.2f} Mo"
    elif volume >= 1024:
        volume_texte = f"{volume / 1024:.1f} Ko"
    else:
        volume_texte = f"{volume} octets"

    return [
        ("Qui communique avec qui ?", f"{afficher(a)}  ⇄  {afficher(b)}"),
        ("Depuis combien de temps ?", f"{duree_texte} (de {communication['debut_lisible'] or '?'} "
                                      f"à {communication['fin_lisible'] or '?'})"),
        ("Sur quel protocole ?", communication["protocole"]),
        ("Sur quel port ?", f"{communication['port_service']}"
                            + (f" ({communication['service_probable']})"
                               if communication["service_probable"] else " (service non identifié)")),
        ("Combien de paquets échangés ?", str(communication["nb_paquets"])),
        ("Combien de données ont circulé ?", volume_texte),
        ("La communication est-elle toujours active ?",
         "oui" if communication["active"] else "non"),
    ]
