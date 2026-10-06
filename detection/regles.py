"""
Les regles de detection.

Une alerte ne dit pas « c'est une attaque ». Elle dit : « ceci merite votre
attention, et voici pourquoi ». La nuance n'est pas de la prudence de facade :
un outil qui annonce une attaque a tort sera ignore apres le deuxieme faux
positif, et n'aura servi a rien.

Chaque regle suit la meme forme que celles de l'explication :

    - elle cite les communications qui l'ont declenchee ;
    - elle indique sur quel fait observe elle repose ;
    - elle ne se declenche jamais sur une donnee absente.

Les regles recoivent l'ensemble des communications, et non une seule : les
signaux interessants — un balayage, des refus repetes, une machine qui parle a
cinquante serveurs — ne se voient que sur l'ensemble.
"""

# Gravites, de la plus discrete a la plus forte.
INFORMATION = "information"
ATTENTION = "attention"
VIGILANCE = "vigilance"

GRAVITES = {
    INFORMATION: "À savoir, sans urgence.",
    ATTENTION: "Mérite un coup d'œil.",
    VIGILANCE: "À examiner sérieusement.",
}


def _alerte(regle, gravite, titre, explication, base, communications, conseil=None):
    """Fabrique une alerte, toujours avec sa base observee."""
    return {
        "regle": regle,
        "gravite": gravite,
        "titre": titre,
        "explication": explication,
        "base": base,
        "conseil": conseil,
        "communications": communications,
        "nb_communications": len(communications),
    }


# ---------------------------------------------------------------------------
#  1. Un service qui circule en clair
# ---------------------------------------------------------------------------

def regle_service_en_clair(communications, contexte):
    """
    Telnet, FTP, HTTP : le contenu circule sans chiffrement.

    Ce n'est pas une attaque, et c'est souvent legitime — un vieux site, un
    equipement ancien. Mais ce qui passe est lisible par quiconque est sur le
    chemin, et c'est une information utile.

    On se limite aux ports dont le defaut est connu : on ne deduit pas qu'une
    communication est en clair parce qu'elle n'est pas sur le port 443.
    """
    PORTS_EN_CLAIR = {
        21: "FTP", 23: "Telnet", 80: "HTTP",
        110: "POP3", 143: "IMAP", 25: "SMTP",
    }

    trouvees = [
        c for c in communications
        if c.get("port_service") in PORTS_EN_CLAIR
        and c.get("port_service") != 443
        and (c.get("octets") or 0) > 4096
    ]
    if not trouvees:
        return []

    services = sorted({PORTS_EN_CLAIR[c["port_service"]] for c in trouvees})
    return [_alerte(
        "service-en-clair",
        ATTENTION,
        f"Échange non chiffré ({', '.join(services)})",
        f"{len(trouvees)} communication(s) emploient un service dont le contenu circule "
        f"en clair. Ce n'est pas nécessairement un problème — de nombreux sites n'ont pas "
        f"encore adopté le chiffrement — mais ce qui passe par là est lisible sur le chemin.",
        f"le port du service observé figure parmi les ports non chiffrés connus "
        f"({', '.join(str(c['port_service']) for c in trouvees[:5])})",
        trouvees,
        "Vérifiez s'il s'agit d'un site que vous connaissez. Sur un site que vous visitez, "
        "préférez la version en HTTPS lorsqu'elle existe.",
    )]


# ---------------------------------------------------------------------------
#  2. Des refus repetes
# ---------------------------------------------------------------------------

def regle_refus_repetes(communications, contexte):
    """
    Plusieurs connexions refusees : une machine frappe, et l'autre ferme.

    C'est la signature habituelle d'un balayage de ports. C'est aussi ce que
    produit une application mal configuree qui reessaie en boucle. On signale
    dans les deux cas, sans trancher.
    """
    refusees = [c for c in communications if c.get("etat") == "refusee"]
    if len(refusees) < 3:
        return []

    destinations = {c.get("ip_seconde") or c.get("ip_premiere") for c in refusees}
    return [_alerte(
        "refus-repetes",
        ATTENTION,
        f"{len(refusees)} connexions refusées",
        f"{len(refusees)} tentatives de connexion ont été rejetées, en direction de "
        f"{len(destinations)} adresse(s) différente(s). C'est le comportement habituel d'une "
        f"recherche de services ouverts — mais aussi celui d'un logiciel qui réessaie "
        f"inlassablement après un échec.",
        f"{len(refusees)} communications portent un drapeau RST observé",
        refusees,
        "S'il s'agit de votre machine, cherchez quelle application émet ces tentatives.",
    )]


# ---------------------------------------------------------------------------
#  3. Une meme machine interroge beaucoup de serveurs
# ---------------------------------------------------------------------------

def regle_destinations_multiples(communications, contexte):
    """
    Une seule machine locale parle a de nombreuses adresses distantes.

    Au-dela d'un certain nombre, ce n'est plus de la navigation ordinaire : cela
    ressemble a une recherche systematique, ou a un logiciel qui contacte sa
    flotte de serveurs.
    """
    SEUIL = 25

    if not contexte:
        return []
    sources = dict(contexte.get("principales_sources") or [])
    destinations = dict(contexte.get("principales_destinations") or [])

    locales = {ip for ip in sources if ip.startswith(("192.168.", "10.", "172."))}
    distantes = [ip for ip in destinations if not ip.startswith(("192.168.", "10.", "172."))]

    if len(distantes) < SEUIL or not locales:
        return []

    concernees = [
        c for c in communications
        if (c.get("ip_seconde") in distantes) or (c.get("ip_premiere") in distantes)
    ][:20]

    return [_alerte(
        "destinations-multiples",
        INFORMATION,
        f"{len(distantes)} serveurs distants contactés",
        f"Une machine de votre réseau a échangé avec au moins {len(distantes)} adresses "
        f"distantes pendant cette capture. Si c'est vous qui naviguiez, c'est normal : une "
        f"seule page web moderne contacte souvent des dizaines de serveurs. Dans le cas "
        f"contraire, cela mérite un coup d'œil.",
        f"{len(distantes)} adresses distinctes hors du réseau local ont été observées",
        concernees,
    )]


# ---------------------------------------------------------------------------
#  4. Des connexions courtes et repetees vers la meme destination
# ---------------------------------------------------------------------------

def regle_connexions_repetees(communications, contexte):
    """
    Beaucoup de connexions breves vers la même adresse.

    C'est la forme que prend un logiciel qui « telephone » regulierement a un
    serveur pour lui demander s'il a du travail : un canal de commande. C'est
    aussi un comportement parfaitement banal pour un client de messagerie.
    On signale la forme, pas la conclusion.
    """
    SEUIL = 8

    par_destination = {}
    for c in communications:
        # La destination est l'extremite distante, en choisissant l'adresse non locale.
        premiere = c.get("ip_premiere") or ""
        seconde = c.get("ip_seconde") or ""
        distante = seconde if not seconde.startswith(("192.168.", "10.", "172.")) else premiere
        if not distante:
            continue
        par_destination.setdefault(distante, []).append(c)

    suspectes = {
        adresse: lot
        for adresse, lot in par_destination.items()
        if len(lot) >= SEUIL and all((c.get("nb_paquets") or 0) <= 12 for c in lot)
    }
    if not suspectes:
        return []

    adresse = max(suspectes, key=lambda a: len(suspectes[a]))
    lot = suspectes[adresse]
    return [_alerte(
        "connexions-repetees",
        ATTENTION,
        f"{len(lot)} échanges brefs avec {adresse}",
        f"Une même destination a été contactée {len(lot)} fois par des communications "
        f"courtes, de moins de douze paquets chacune. Cette régularité est celle d'un "
        f"logiciel qui interroge périodiquement un serveur — un client de messagerie, une "
        f"mise à jour automatique, ou un canal de commande. Impossible de trancher sans "
        f"savoir quel programme est en cause.",
        f"{len(lot)} communications distinctes de moins de 12 paquets vers {adresse}",
        lot,
        "Identifier le programme concerné sur la machine qui émet.",
    )]


# ---------------------------------------------------------------------------
#  5. Un volume inhabituel
# ---------------------------------------------------------------------------

def regle_volume_important(communications, contexte):
    """
    Une seule communication concentre une part importante du volume total.

    Cela peut etre un telechargement legitime, une sauvegarde, une mise a jour.
    Cela peut aussi etre une exfiltration. Le fait observable, lui, est precis :
    une communication a transporte beaucoup plus que les autres.
    """
    total = sum((c.get("octets") or 0) for c in communications)
    if total < 1_000_000 or not communications:
        return []

    plus_grosse = max(communications, key=lambda c: c.get("octets") or 0)
    part = (plus_grosse.get("octets") or 0) / total

    if part < 0.5:
        return []

    volume = plus_grosse.get("octets") or 0

    # « 100 % » pour 99,98 % est un arrondi qui exagere : il laisse croire que
    # TOUT le volume est passe par la, alors que d'autres communications ont
    # transporte quelque chose. Au-dela de 99 %, on le dit autrement.
    pourcentage = "plus de 99 %" if part >= 0.99 else f"{part:.0%}"

    return [_alerte(
        "volume-concentre",
        INFORMATION,
        f"{pourcentage} du volume sur une seule communication",
        f"Cette communication a transporté {volume / 1024 / 1024:.1f} Mo, soit {part:.0%} "
        f"de tout ce qui a circulé pendant la capture. Un téléchargement, une mise à jour "
        f"ou une sauvegarde produisent ce profil. Une copie de données vers l'extérieur "
        f"aussi — et l'analyse ne peut pas les distinguer.",
        f"{volume} octets sur {total} observés au total",
        [plus_grosse],
        "Regardez vers quelle destination ce volume est parti.",
    )]


# ---------------------------------------------------------------------------
#  6. Un service qui n'a pas pu etre identifie
# ---------------------------------------------------------------------------

def regle_service_non_identifie(communications, contexte):
    """
    Un port inconnu, mais un echange soutenu.

    Un service non identifie qui transporte beaucoup de donnees merite d'etre
    nomme : c'est souvent un service legitime deplace sur un port inhabituel,
    mais tant qu'on ne sait pas, on le signale.
    """
    SEUIL = 40

    inconnues = [
        c for c in communications
        if not c.get("service_probable")
        and c.get("port_service") is not None
        and (c.get("nb_paquets") or 0) >= SEUIL
    ]
    if not inconnues:
        return []

    ports = sorted({c["port_service"] for c in inconnues})
    return [_alerte(
        "service-non-identifie",
        INFORMATION,
        f"Service non identifié sur le port {', '.join(str(p) for p in ports[:5])}",
        f"{len(inconnues)} communication(s) emploient un port que le programme ne sait pas "
        f"nommer, avec un échange soutenu. Un port inconnu n'est pas un port dangereux : "
        f"beaucoup d'applications choisissent un port libre. Mais tant qu'il n'est pas "
        f"identifié, on ne peut pas dire ce qui passe.",
        f"port(s) {', '.join(str(p) for p in ports[:5])} absent(s) de la table des services "
        f"connus, avec au moins {SEUIL} paquets échangés",
        inconnues,
    )]


# ---------------------------------------------------------------------------
#  L'ensemble des regles
# ---------------------------------------------------------------------------

#  L'identifiant d'une regle est le MEME que celui porte par ses alertes. Deux
#  orthographes differentes — un libelle lisible ici, un identifiant technique
#  la — faisaient qu'une regle declenchee apparaissait aussi parmi celles qui ne
#  l'avaient pas ete. Le defaut a ete constate sur une vraie capture.
REGLES = [
    ("refus-repetes", regle_refus_repetes),
    ("service-en-clair", regle_service_en_clair),
    ("connexions-repetees", regle_connexions_repetees),
    ("destinations-multiples", regle_destinations_multiples),
    ("volume-concentre", regle_volume_important),
    ("service-non-identifie", regle_service_non_identifie),
]


def ordonner(alertes):
    """De la plus grave a la plus discrete."""
    rang = {VIGILANCE: 0, ATTENTION: 1, INFORMATION: 2}
    return sorted(alertes, key=lambda a: (rang.get(a["gravite"], 3), -a["nb_communications"]))


def analyser(communications, contexte=None):
    """
    Applique toutes les regles et rend les alertes, ordonnees.

    Une regle qui echoue ne doit pas empecher les autres de s'exprimer : sur des
    donnees inattendues, on l'ignore et on continue. Une alerte manquante est
    facheuse ; un plantage qui masque tout l'est davantage.
    """
    alertes = []
    for nom, regle in REGLES:
        try:
            resultat = regle(communications or [], contexte or {})
        except Exception as e:                       # noqa: BLE001
            print(f"  (regle « {nom} » ignoree : {type(e).__name__} — {e})")
            continue
        alertes.extend(resultat or [])
    return ordonner(alertes)
