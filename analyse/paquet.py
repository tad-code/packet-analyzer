"""
Analyse d'un paquet.

Ce module fait une seule chose : prendre un paquet brut fourni par Scapy et le
transformer en dictionnaire de champs nommes, faciles a lire et a afficher.

C'est la frontiere importante du projet. En amont, on manipule des objets Scapy,
que seuls les specialistes savent lire. En aval, tout le reste du programme ne
manipule plus que des dictionnaires : des cles en francais, des valeurs simples.

Une regle s'applique partout dans ce fichier : quand une information n'existe pas
dans le paquet, on met None et on le dit. On n'invente jamais une valeur, et on ne
met jamais une chaine vide qui laisserait croire que l'information a ete lue.
"""

from datetime import datetime

from scapy.all import ARP, DNS, ICMP, IP, IPv6, TCP, UDP, Raw

# Les protocoles de transport que nous savons reconnaitre, par leur numero tel
# qu'il apparait dans l'en-tete IP.
NOMS_PROTOCOLES_IP = {
    1: "ICMP",
    6: "TCP",
    17: "UDP",
}

# Ports dont le role est bien connu. Sert uniquement a proposer une lecture, pas
# a affirmer ce que transporte reellement la communication : le contenu peut etre
# chiffre, et un service peut tres bien ecouter ailleurs.
PORTS_CONNUS = {
    20: "FTP (donnees)",
    21: "FTP (commandes)",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    445: "Partage de fichiers Windows",
    3306: "MySQL",
    3389: "Bureau a distance Windows",
    5432: "PostgreSQL",
    8080: "HTTP alternatif",
}


def protocole_ip(paquet):
    """Nom du protocole de la couche reseau, ou son numero s'il est inconnu."""
    if IPv6 in paquet:
        # IPv6 utilise le champ « next header », au role equivalent.
        numero = paquet[IPv6].nh
        nom = NOMS_PROTOCOLES_IP.get(numero, f"Protocole {numero}")
        return f"IPv6 / {nom}"
    if IP in paquet:
        numero = paquet[IP].proto
        return NOMS_PROTOCOLES_IP.get(numero, f"Protocole IP {numero}")
    return None


def protocole_transport(paquet):
    """TCP, UDP, ICMP ou None."""
    if TCP in paquet:
        return "TCP"
    if UDP in paquet:
        return "UDP"
    if ICMP in paquet:
        return "ICMP"
    return None


def protocole_applicatif(paquet):
    """
    Essaie de deviner le service au-dessus du transport.

    On reste prudent : quand on ne peut pas savoir, on rend None plutot que de
    supposer. Un port 443 ne prouve pas que le contenu est du HTTPS, il indique
    seulement que c'est tres probable.
    """
    if DNS in paquet:
        return "DNS"

    if TCP in paquet and Raw in paquet:
        try:
            donnees = bytes(paquet[Raw].load)
            debit = donnees[:8].upper()
            if debit.startswith(b"GET ") or debit.startswith(b"POST") or debit.startswith(b"HEAD "):
                return "HTTP"
            if debit.startswith(b"HTTP/"):
                return "HTTP"
        except Exception:
            # Un paquet peut porter des donnees qui ne sont pas du texte : on
            # n'essaie pas de les decoder, on continue simplement.
            return None

    return None


def ports(paquet):
    """Ports source et destination, s'ils existent."""
    if TCP in paquet:
        return paquet[TCP].sport, paquet[TCP].dport
    if UDP in paquet:
        return paquet[UDP].sport, paquet[UDP].dport
    return None, None


def drapeaux_tcp(paquet):
    """
    Drapeaux de l'en-tete TCP, sous forme lisible.

    SYN   : demande d'ouverture de connexion
    SYN-ACK : accord
    ACK   : accuse de reception
    FIN   : demande de fermeture
    RST   : fermeture brutale, souvent un refus
    """
    if TCP not in paquet:
        return None
    try:
        return str(paquet[TCP].flags)
    except Exception:
        return None


def analyser(paquet, rang):
    """
    Transforme un paquet brut en dictionnaire de champs nommes.

    'rang' est le numero d'ordre du paquet dans la capture : il sert a l'afficher
    dans la liste et a le retrouver.
    """
    # Adresses source et destination.
    #
    # Trois cas a traiter, et non un seul :
    #   - IPv4, le cas le plus courant ;
    #   - IPv6, de plus en plus frequent — l'ignorer affichait « non disponible »
    #     sur une grande partie des paquets, alors que l'information etait bien
    #     presente (c'est un defaut repere en regardant une capture d'ecran) ;
    #   - ARP, qui n'a pas d'adresse IP mais des adresses de reseau local.
    adresses = {}
    if IP in paquet:
        adresses["source"] = paquet[IP].src
        adresses["destination"] = paquet[IP].dst
    elif IPv6 in paquet:
        adresses["source"] = paquet[IPv6].src
        adresses["destination"] = paquet[IPv6].dst

    if ARP in paquet:
        # Les paquets ARP n'ont pas d'adresses IP : ils servent a associer une
        # adresse IP a une adresse materielle sur le reseau local.
        adresses["source"] = paquet[ARP].psrc
        adresses["destination"] = paquet[ARP].pdst

    port_source, port_destination = ports(paquet)

    # Lecture du nom de domaine demande, quand c'est une requete DNS.
    domaine = None
    if DNS in paquet and paquet[DNS].qd is not None:
        try:
            domaine = paquet[DNS].qd.qname.decode(errors="replace").rstrip(".")
        except Exception:
            domaine = None

    # Taille telle qu'elle circule reellement sur le reseau : on prend la
    # longueur totale du paquet, en-tetes comprises.
    try:
        taille = len(paquet)
    except Exception:
        taille = None

    # Horodatage : on garde la valeur brute (utile pour calculer des durees) et
    # on ajoute une forme lisible par un humain. Un nombre a treize chiffres
    # n'apprend rien a personne — et rendre les donnees comprenables est
    # precisement le but de ce projet.
    horodatage = float(paquet.time) if paquet.time else None
    heure_lisible = None
    if horodatage:
        try:
            heure_lisible = datetime.fromtimestamp(horodatage).strftime("%H:%M:%S.%f")[:-3]
        except Exception:
            heure_lisible = None

    return {
        "rang": rang,
        "horodatage": horodatage,
        "heure_lisible": heure_lisible,
        "taille": taille,
        "source": adresses.get("source"),
        "destination": adresses.get("destination"),
        "protocole_ip": protocole_ip(paquet),
        "protocole_transport": protocole_transport(paquet),
        "protocole_applicatif": protocole_applicatif(paquet),
        "port_source": port_source,
        "port_destination": port_destination,
        # Lecture du port : on ne dit pas ce que transporte reellement la
        # communication, seulement le service habituellement associe a ce port.
        "service_probable": service_probable(port_destination),
        "drapeaux": drapeaux_tcp(paquet),
        "ttl": paquet[IP].ttl if IP in paquet else None,
        "numero_sequence": int(paquet[TCP].seq) if TCP in paquet and paquet[TCP].seq is not None else None,
        "domaine_demande": domaine,
        "resume": paquet.summary(),
    }


def service_probable(port):
    """Nom usuel d'un port, s'il est connu. Sinon None."""
    if port is None:
        return None
    return PORTS_CONNUS.get(int(port))
