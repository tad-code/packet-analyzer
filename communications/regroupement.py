"""
Regroupement des paquets en communications.

C'est le coeur du projet. Un paquet isole ne dit pas grand-chose ; c'est la
conversation qui a un sens. Ce module repond donc a la question :

    « Qui parle a qui, sur quoi, pendant combien de temps, et avec quel volume ? »

Trois choix de conception, et il faut pouvoir les expliquer :

1. UNE FONCTION PURE, SANS ETAT.

   `regrouper()` recoit une liste de paquets deja analyses et rend une liste de
   communications. Elle ne lit aucun fichier, n'appelle aucun reseau, ne retient
   rien entre deux appels. Consequences : elle est testable avec des paquets
   fabriques a la main, et le resultat est reproductible.

2. UNE CLE DE COMMUNICATION BIDIRECTIONNELLE.

   Le quintuplet (adresse source, port source, adresse destination, port
   destination, protocole) ne suffit pas tel quel : une reponse du serveur a un
   ordre de champs inverse, et formerait donc une seconde communication. On
   range les deux extremites dans un ordre fixe (tri alphabetique), si bien que
   les deux sens de l'echange tombent dans la meme conversation.

3. UNE DUREE D'INACTIVITE POUR CLORE.

   Une communication TCP se termine par FIN ou RST, mais une communication UDP
   ne se termine jamais explicitement. On considere donc qu'une communication
   sans nouveau paquet depuis un certain temps est terminee.
"""

from datetime import datetime
from analyse.adresses import adresse_complete

from analyse.paquet import service_probable

# Duree, en secondes, apres laquelle une communication silencieuse est
# consideree comme terminee. Une minute est un compromis raisonnable : assez
# longue pour ne pas couper une conversation qui marque une pause, assez courte
# pour que l'affichage reste juste.
DELAI_INACTIVITE = 60.0

# Drapeaux TCP et ce qu'ils indiquent sur l'etat de la connexion.
DRAPEAUX_OUVERTURE = "S"
DRAPEAUX_FERMETURE = "F"
DRAPEAUX_REFUS = "R"


def cle_communication(paquet):
    """
    Construit la cle de la communication a laquelle appartient un paquet.

    Les deux extremites sont rangees dans un ordre fixe, afin que les paquets
    allant et venant partagent la meme cle. Sans ce tri, une reponse serait vue
    comme une communication separee.
    """
    protocole = paquet.get("protocole_transport") or paquet.get("protocole_ip") or "?"
    extremite_source = (str(paquet.get("source") or "?"), paquet.get("port_source"))
    extremite_destination = (str(paquet.get("destination") or "?"), paquet.get("port_destination"))

    if extremite_source <= extremite_destination:
        premier, second = extremite_source, extremite_destination
    else:
        premier, second = extremite_destination, extremite_source

    return f"{protocole}|{premier[0]}:{premier[1]}|{second[0]}:{second[1]}"


def port_du_service(port_a, port_b):
    """
    Determine lequel des deux ports est celui du service.

    Deux regles, dans cet ordre :

        1. si l'un des ports est un port connu (443, 53, 22...), c'est lui le
           service — c'est la regle la plus fiable ;
        2. sinon, on prend le plus petit. Les clients choisissent generalement un
           port eleve au hasard, les services ecoutent sur un port bas.

    C'est une deduction, pas une certitude : elle est presentee comme telle dans
    l'interface.
    """
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
    """
    Deduit l'etat de la communication a partir des drapeaux TCP observes.

    Correspond aux etapes que le cahier des charges demande d'identifier :

        - « ouverte »  : un SYN a ete vu, sans reponse pour l'instant ;
        - « refusee »  : un RST a ete vu — le service a rejete la connexion ;
        - « terminee » : un FIN a ete vu — la connexion s'est fermee proprement ;
        - « en cours » : des echanges ont lieu, rien n'indique la fin ;
        - « inactive » : plus rien depuis longtemps, sans fermeture explicite.
    """
    if DRAPEAUX_REFUS in drapeaux_vus:
        return "refusee"
    if DRAPEAUX_FERMETURE in drapeaux_vus:
        return "terminee"
    if not active:
        return "inactive"
    if DRAPEAUX_OUVERTURE in drapeaux_vus:
        # Un SYN sans FIN et sans RST : l'echange se poursuit.
        return "en cours"
    return "en cours"


def _heure_lisible(horodatage):
    """Rend un horodatage sous une forme lisible, ou None."""
    if not horodatage:
        return None
    try:
        return datetime.fromtimestamp(horodatage).strftime("%H:%M:%S")
    except Exception:
        return None


def regrouper(paquets, delai_inactivite=DELAI_INACTIVITE, maintenant=None):
    """
    Regroupe une liste de paquets analyses en communications.

    'paquets'           : liste de dictionnaires produits par analyse.paquet
    'delai_inactivite'  : duree de silence au-dela de laquelle une communication
                          est consideree comme terminee
    'maintenant'        : instant de reference, pour que le resultat soit
                          reproductible dans les tests. Par defaut, on prend le
                          dernier paquet vu.
    """
    communications = {}

    for paquet in paquets:
        try:
            cle = cle_communication(paquet)
        except Exception:
            # Un paquet inexploitable ne doit pas faire echouer tout le
            # regroupement : on l'ignore.
            continue

        if cle not in communications:
            # Premiere rencontre : on cree la communication.
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
                # Qui a parle en premier : utile pour savoir qui a pris
                # l'initiative de la communication.
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

        # --- Comptage ------------------------------------------------------
        communication["nb_paquets"] += 1
        if paquet.get("taille"):
            communication["octets"] += paquet["taille"]

        # --- Bornes temporelles --------------------------------------------
        horodatage = paquet.get("horodatage")
        if horodatage:
            if communication["debut"] is None or horodatage < communication["debut"]:
                communication["debut"] = horodatage
            if communication["fin"] is None or horodatage > communication["fin"]:
                communication["fin"] = horodatage

        # --- Drapeaux observes ---------------------------------------------
        drapeaux = paquet.get("drapeaux")
        if drapeaux:
            for lettre in str(drapeaux):
                communication["etaient_des_drapeaux"].add(lettre)

        # --- Sens de circulation -------------------------------------------
        if paquet.get("source") == communication["premiere_extremite"]["ip"]:
            communication["sens_a_vers_b"] += 1
        else:
            communication["sens_b_vers_a"] += 1

    # --- Mise en forme finale ------------------------------------------------
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

        # La communication est-elle encore active ?
        #
        # Deux conditions, et non une seule. Se fier uniquement au temps donnait
        # un resultat faux : une communication fermee par FIN ou rejetee par RST
        # etait comptee comme « encore active » tant qu'elle etait recente. Or
        # elle est bel et bien terminee — c'est meme ce que disent ses drapeaux.
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
        communication["etaient_des_drapeaux"] = None  # non serialisable, on l'oublie

        resultat.append(communication)

    # Les communications les plus recentes d'abord.
    resultat.sort(key=lambda c: c["fin"] or 0, reverse=True)
    return resultat


def statistiques(communications):
    """
    Calcule les chiffres du tableau de bord a partir des communications.

    Tout est compte a partir des communications, et non des paquets : c'est la
    communication qui porte le sens, et cela evite de compter deux fois le meme
    echange.
    """
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
            # La machine qui a ouvert la communication.
            sources[c["initiateur"]] += c["nb_paquets"]

            # La destination est l'AUTRE extremite, celle qui n'a pas pris
            # l'initiative. Compter les deux extremaitait la meme machine dans
            # les sources et dans les destinations : le tableau de bord
            # presentait alors une adresse locale comme une destination.
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
    """
    Repond aux sept questions que le cahier des charges demande de pouvoir
    traiter pour une communication.

    On rend des couples « question / reponse » deja formates : l'interface les
    affiche tels quels, et il n'y a pas de phrase a reconstruire ailleurs.
    """
    a = communication["premiere_extremite"]
    b = communication["seconde_extremite"]

    def afficher(extremite):
        # On passe par le formateur commun : c'est lui qui sait encadrer les
        # adresses IPv6, dont les deux-points se confondraient avec le separateur
        # du port.
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
