

from datetime import datetime

from scapy.all import ARP, DNS, ICMP, IP, IPv6, TCP, UDP, Raw

NOMS_PROTOCOLES_IP = {
    1: "ICMP",
    6: "TCP",
    17: "UDP",
}

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

    if IPv6 in paquet:

        numero = paquet[IPv6].nh
        nom = NOMS_PROTOCOLES_IP.get(numero, f"Protocole {numero}")
        return f"IPv6 / {nom}"
    if IP in paquet:
        numero = paquet[IP].proto
        return NOMS_PROTOCOLES_IP.get(numero, f"Protocole IP {numero}")
    return None

def protocole_transport(paquet):

    if TCP in paquet:
        return "TCP"
    if UDP in paquet:
        return "UDP"
    if ICMP in paquet:
        return "ICMP"
    return None

def protocole_applicatif(paquet):

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

            return None

    return None

def ports(paquet):

    if TCP in paquet:
        return paquet[TCP].sport, paquet[TCP].dport
    if UDP in paquet:
        return paquet[UDP].sport, paquet[UDP].dport
    return None, None

def drapeaux_tcp(paquet):

    if TCP not in paquet:
        return None
    try:
        return str(paquet[TCP].flags)
    except Exception:
        return None

def analyser(paquet, rang):

    adresses = {}
    if IP in paquet:
        adresses["source"] = paquet[IP].src
        adresses["destination"] = paquet[IP].dst
    elif IPv6 in paquet:
        adresses["source"] = paquet[IPv6].src
        adresses["destination"] = paquet[IPv6].dst

    if ARP in paquet:

        adresses["source"] = paquet[ARP].psrc
        adresses["destination"] = paquet[ARP].pdst

    port_source, port_destination = ports(paquet)

    domaine = None
    if DNS in paquet and paquet[DNS].qd is not None:
        try:
            domaine = paquet[DNS].qd.qname.decode(errors="replace").rstrip(".")
        except Exception:
            domaine = None

    try:
        taille = len(paquet)
    except Exception:
        taille = None

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

        "service_probable": service_probable(port_destination),
        "drapeaux": drapeaux_tcp(paquet),
        "ttl": paquet[IP].ttl if IP in paquet else None,
        "numero_sequence": int(paquet[TCP].seq) if TCP in paquet and paquet[TCP].seq is not None else None,
        "domaine_demande": domaine,
        "resume": paquet.summary(),
    }

def service_probable(port):

    if port is None:
        return None
    return PORTS_CONNUS.get(int(port))
