

PROTOCOLES = {
    "TCP": {
        "nom": "TCP — Transmission Control Protocol",
        "categorie": "transport",
        "role": (
            "TCP établit une connexion avant d'échanger des données, puis vérifie que "
            "tout arrive dans le bon ordre. Il ouvre la connexion par un échange en "
            "trois temps, et la ferme proprement à la fin."
        ),
        "ce_qu_on_observe": (
            "Un premier paquet portant le drapeau SYN, une réponse SYN-ACK, puis des "
            "paquets numérotés portant un accusé de réception. La fermeture se fait par "
            "un drapeau FIN, ou brutalement par un RST."
        ),
        "ce_que_ca_signifie": (
            "Les deux machines se sont mises d'accord avant d'échanger. Si l'on voit un "
            "SYN sans réponse, la tentative de connexion n'a pas abouti."
        ),
    },
    "UDP": {
        "nom": "UDP — User Datagram Protocol",
        "categorie": "transport",
        "role": (
            "UDP envoie des données sans établir de connexion et sans vérifier qu'elles "
            "sont arrivées. C'est plus rapide, mais rien ne garantit la livraison."
        ),
        "ce_qu_on_observe": (
            "Des paquets isolés, sans échange préalable d'ouverture, et sans drapeau de "
            "connexion. Aucun accusé de réception n'est attendu."
        ),
        "ce_que_ca_signifie": (
            "La communication est sans état : on ne peut pas dire quand elle a « commencé » "
            "ni quand elle s'est « terminée ». Seule l'absence de paquets pendant un "
            "certain temps permet de conclure qu'elle est finie."
        ),
    },
    "ICMP": {
        "nom": "ICMP — Internet Control Message Protocol",
        "categorie": "controle",
        "role": (
            "ICMP transporte des messages de contrôle du réseau : « je suis joignable », "
            "« cet hôte est injoignable », « cette route a changé »."
        ),
        "ce_qu_on_observe": (
            "Des paquets sans notion de port, portant un type et un code de message."
        ),
        "ce_que_ca_signifie": (
            "La plupart du temps, il s'agit d'un test de disponibilité — ce que fait la "
            "commande ping. ICMP ne transporte pas de données d'application."
        ),
    },
    "DNS": {
        "nom": "DNS — Domain Name System",
        "categorie": "applicatif",
        "role": (
            "DNS traduit un nom lisible par un humain (« exemple.com ») en une adresse "
            "numérique utilisable par les machines."
        ),
        "ce_qu_on_observe": (
            "Une question portant un nom de domaine, envoyée en UDP vers le port 53."
        ),
        "ce_que_ca_signifie": (
            "La machine demande où se trouve un service. C'est presque toujours le premier "
            "échange précédant une communication web : avant de contacter un serveur, il "
            "faut connaître son adresse."
        ),
    },
    "HTTP": {
        "nom": "HTTP — HyperText Transfer Protocol",
        "categorie": "applicatif",
        "role": (
            "HTTP transporte les échanges du web : une demande de page, envoyée par le "
            "navigateur, à laquelle un serveur répond."
        ),
        "ce_qu_on_observe": (
            "Sur le port 80 : la requête elle-même est lisible dans le paquet — on y voit "
            "la méthode (GET, POST) et l'adresse demandée."
        ),
        "ce_que_ca_signifie": (
            "La communication n'est pas chiffrée : son contenu circule en clair sur le "
            "réseau, et n'importe qui peut le lire sur le chemin."
        ),
    },
    "HTTPS": {
        "nom": "HTTPS — HTTP sécurisé",
        "categorie": "applicatif",
        "role": (
            "HTTPS est du HTTP placé dans un tunnel chiffré. Le contenu est protégé : "
            "seuls les deux interlocuteurs peuvent le lire."
        ),
        "ce_qu_on_observe": (
            "Sur le port 443 : uniquement les métadonnées — les adresses, le port, la "
            "taille et le rythme des paquets. Le contenu, lui, n'est pas lisible."
        ),
        "ce_que_ca_signifie": (
            "L'analyseur peut dire qui parle à qui, pendant combien de temps et avec quel "
            "volume, mais jamais ce qui est dit. Ce n'est pas une limite de l'outil : "
            "c'est le but même du chiffrement."
        ),
    },
    "SSDP": {
        "nom": "SSDP — découverte de services sur le réseau local",
        "categorie": "applicatif",
        "role": (
            "SSDP permet aux appareils d'un même réseau local de se trouver : "
            "imprimantes, télévisions connectées, enceintes."
        ),
        "ce_qu_on_observe": (
            "Des messages en diffusion, envoyés en UDP vers le port 1900."
        ),
        "ce_que_ca_signifie": (
            "Une machine annonce sa présence ou cherche des appareils autour d'elle. "
            "Ce trafic reste normalement interne au réseau local."
        ),
    },
    "MDNS": {
        "nom": "mDNS — résolution de noms locale",
        "categorie": "applicatif",
        "role": (
            "mDNS est la version locale du DNS : il résout les noms des appareils du "
            "réseau local sans passer par un serveur."
        ),
        "ce_qu_on_observe": ("Des questions et réponses en diffusion, sur le port 5353."),
        "ce_que_ca_signifie": (
            "Un appareil cherche à joindre un autre appareil du même réseau par son nom. "
            "Trafic de voisinage, généralement sans conséquence."
        ),
    },
}

PORTS = {
    20: ("FTP (données)", "Transfert de fichiers, canal de données."),
    21: ("FTP (commandes)", "Transfert de fichiers, canal de commandes — non chiffré."),
    22: ("SSH", "Accès à distance chiffré à une machine."),
    23: ("Telnet", "Accès à distance NON chiffré : le mot de passe circule en clair."),
    25: ("SMTP", "Envoi de courrier électronique."),
    53: ("DNS", "Traduction d'un nom de domaine en adresse."),
    67: ("DHCP", "Attribution automatique d'une adresse réseau."),
    80: ("HTTP", "Web non chiffré."),
    110: ("POP3", "Relevé de courrier, non chiffré dans sa version d'origine."),
    123: ("NTP", "Mise à l'heure des machines."),
    143: ("IMAP", "Consultation de courrier."),
    161: ("SNMP", "Supervision d'équipements réseau."),
    389: ("LDAP", "Annuaire d'utilisateurs."),
    443: ("HTTPS", "Web chiffré."),
    445: ("Partage de fichiers Windows", "Partage de fichiers et d'imprimantes."),
    1900: ("SSDP", "Découverte d'appareils sur le réseau local."),
    3306: ("MySQL", "Base de données."),
    3389: ("Bureau à distance Windows", "Prise en main graphique d'une machine."),
    5432: ("PostgreSQL", "Base de données."),
    5353: ("mDNS", "Résolution de noms sur le réseau local."),
    8080: ("HTTP alternatif", "Web non chiffré sur un port secondaire, souvent un serveur de test."),
    8443: ("HTTPS alternatif", "Web chiffré sur un port secondaire."),
}

def fiche_protocole(nom):

    if not nom:
        return None
    return PROTOCOLES.get(str(nom).upper())

def fiche_port(port):

    if port is None:
        return None, None
    return PORTS.get(int(port), (None, None))

def nom_du_port(port):

    return fiche_port(port)[0]

DRAPEAUX = {
    "SYN": "Demande d'ouverture : une machine propose de commencer a dialoguer.",
    "ACK": "Accusé de réception : la machine confirme qu'elle a bien reçu.",
    "PSH": "Envoi de données : le paquet transporte du contenu, et non une simple confirmation.",
    "FIN": "Fermeture propre : la machine annonce qu'elle a terminé et range la connexion.",
    "RST": "Refus ou interruption brutale : la connexion est coupée sans ménagement. "
           "Signale souvent qu'un service ne répond pas, ou qu'une demande est rejetée.",
    "URG": "Donnée urgente, à traiter en priorité (rarement employé).",
}

LETTRES_DRAPEAUX = {
    "S": "SYN", "A": "ACK", "F": "FIN", "R": "RST",
    "P": "PSH", "U": "URG", "E": "ECE", "C": "CWR", "N": "NS",
}

def lire_drapeaux(drapeaux_vus):

    if not drapeaux_vus:
        return []
    texte = str(drapeaux_vus).strip()
    if not texte:
        return []

    if "," in texte or ";" in texte or "-" in texte:
        morceaux = [m.strip().upper() for m in texte.replace(";", ",").replace("-", ",").split(",")]
        return [m for m in morceaux if m]

    noms = []
    for lettre in texte.upper():
        nom = LETTRES_DRAPEAUX.get(lettre, lettre)
        if nom not in noms:
            noms.append(nom)
    return noms

def expliquer_drapeaux(drapeaux_vus):

    expliques = []
    for nom in lire_drapeaux(drapeaux_vus):
        sens = DRAPEAUX.get(nom, "Signification non documentee : le programme ne l'invente pas.")
        expliques.append((nom, sens))
    return expliques
