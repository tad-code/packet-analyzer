

INFORMATION = "information"
ATTENTION = "attention"
VIGILANCE = "vigilance"

GRAVITES = {
    INFORMATION: "À savoir, sans urgence.",
    ATTENTION: "Mérite un coup d'œil.",
    VIGILANCE: "À examiner sérieusement.",
}

def _alerte(regle, gravite, titre, explication, base, communications, conseil=None):

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

def regle_service_en_clair(communications, contexte):

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

def regle_refus_repetes(communications, contexte):

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

def regle_destinations_multiples(communications, contexte):

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

def regle_connexions_repetees(communications, contexte):

    SEUIL = 8

    par_destination = {}
    for c in communications:

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

def regle_volume_important(communications, contexte):

    total = sum((c.get("octets") or 0) for c in communications)
    if total < 1_000_000 or not communications:
        return []

    plus_grosse = max(communications, key=lambda c: c.get("octets") or 0)
    part = (plus_grosse.get("octets") or 0) / total

    if part < 0.5:
        return []

    volume = plus_grosse.get("octets") or 0

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

def regle_service_non_identifie(communications, contexte):

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

REGLES = [
    ("refus-repetes", regle_refus_repetes),
    ("service-en-clair", regle_service_en_clair),
    ("connexions-repetees", regle_connexions_repetees),
    ("destinations-multiples", regle_destinations_multiples),
    ("volume-concentre", regle_volume_important),
    ("service-non-identifie", regle_service_non_identifie),
]

def ordonner(alertes):

    rang = {VIGILANCE: 0, ATTENTION: 1, INFORMATION: 2}
    return sorted(alertes, key=lambda a: (rang.get(a["gravite"], 3), -a["nb_communications"]))

def analyser(communications, contexte=None):

    alertes = []
    for nom, regle in REGLES:
        try:
            resultat = regle(communications or [], contexte or {})
        except Exception as e:
            print(f"  (regle « {nom} » ignoree : {type(e).__name__} — {e})")
            continue
        alertes.extend(resultat or [])
    return ordonner(alertes)
