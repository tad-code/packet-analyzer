"""
Test de faisabilite de la capture — script jetable, pas du code de projet.

But : repondre a une seule question, avant d'ecrire la moindre ligne du projet.

    Scapy est-il capable, sur CETTE machine, de voir les interfaces reseau et de
    lire des paquets reels ?

Si la reponse est non, toute l'architecture doit etre repensee. Mieux vaut le savoir
maintenant qu'apres trois jours de developpement.

La methode : on lance une capture en arriere-plan pendant qu'on fabrique volontairement
du trafic (une resolution DNS et une requete HTTP), puis on verifie que les paquets
correspondants ont bien ete interceptes.

Le script ne modifie rien sur la machine et n'ecrit aucun fichier.
"""

import threading
import time

from scapy.all import DNS, IP, TCP, UDP, conf, get_if_list, sniff

print("=" * 74)
print("  1. INTERFACES RESEAU VISIBLES PAR SCAPY")
print("=" * 74)
print()

noms = get_if_list()
print(f"  {len(noms)} interface(s) detectee(s) :")
for nom in noms:
    print(f"    - {nom}")

print()
print("  Interface par defaut choisie par Scapy :")
print(f"    {conf.iface}")

print()
print("  Detail des interfaces :")
for iface in conf.ifaces.values():
    adresse = getattr(iface, "ip", None) or "-"
    mac = getattr(iface, "mac", None) or "-"
    description = (getattr(iface, "description", "") or "")[:45]
    print(f"    {iface.name:38s} ip={adresse:16s} {description}")

print()
print("=" * 74)
print("  2. CAPTURE REELLE")
print("=" * 74)
print()

paquets = []


def capturer():
    """Ecoute le reseau pendant 8 secondes et conserve les paquets vus."""
    try:
        captures = sniff(timeout=8, store=True)
        paquets.extend(captures)
    except Exception as e:
        print(f"  [ERREUR DE CAPTURE] {type(e).__name__} : {e}")


def fabriquer_trafic():
    """Attend un instant, puis provoque du trafic observable."""
    time.sleep(2)

    # Une resolution DNS : genere un paquet UDP vers le port 53.
    try:
        import socket

        socket.gethostbyname("example.com")
        print("  trafic : resolution DNS de example.com envoyee")
    except Exception as e:
        print(f"  trafic : echec de la resolution DNS ({e})")

    # Une requete HTTP : genere un paquet TCP vers le port 80.
    try:
        import urllib.request

        urllib.request.urlopen("http://example.com", timeout=6).read(200)
        print("  trafic : requete HTTP vers example.com envoyee")
    except Exception as e:
        print(f"  trafic : echec de la requete HTTP ({type(e).__name__})")


fil_capture = threading.Thread(target=capturer)
fil_trafic = threading.Thread(target=fabriquer_trafic)
fil_capture.start()
fil_trafic.start()
fil_capture.join()
fil_trafic.join()

print()
print(f"  Paquets interceptes : {len(paquets)}")
print()

if not paquets:
    print("  AUCUN PAQUET VU.")
    print("  -> Soit le pilote Npcap n'est pas accessible, soit l'interface choisie")
    print("     n'est pas la bonne. C'est un point bloquant a resoudre avant de coder.")
else:
    print("  Detail des premiers paquets :")
    for i, p in enumerate(paquets[:12], 1):
        resume = p.summary()
        print(f"    {i:2d}. {resume[:100]}")

    # Verifions que nous savons extraire les champs qui interessent le projet.
    print()
    print("=" * 74)
    print("  3. EXTRACTION DES CHAMPS UTILES POUR L'ANALYSE")
    print("=" * 74)
    print()

    ip_paquets = [p for p in paquets if IP in p]
    print(f"  Paquets IP          : {len(ip_paquets)}")

    tcp = [p for p in ip_paquets if TCP in p]
    udp = [p for p in ip_paquets if UDP in p]
    dns = [p for p in ip_paquets if DNS in p]
    print(f"  dont TCP            : {len(tcp)}")
    print(f"  dont UDP            : {len(udp)}")
    print(f"  dont DNS            : {len(dns)}")

    print()
    print("  Un paquet TCP, champ par champ :")
    exemple = tcp[0] if tcp else (ip_paquets[0] if ip_paquets else None)
    if exemple is not None:
        print(f"    IP source      : {exemple[IP].src}")
        print(f"    IP destination : {exemple[IP].dst}")
        print(f"    protocole IP   : {exemple[IP].proto}")
        print(f"    taille totale  : {len(exemple)} octets")
        print(f"    horodatage     : {exemple.time}")
        if TCP in exemple:
            print(f"    port source    : {exemple[TCP].sport}")
            print(f"    port dest.     : {exemple[TCP].dport}")
            print(f"    drapeaux TCP   : {exemple[TCP].flags}")
            print(f"    numero seq.    : {exemple[TCP].seq}")

    if dns:
        print()
        print("  Un paquet DNS, champ par champ :")
        d = dns[0]
        question = d[DNS].qd
        print(f"    requete        : {question.qname.decode(errors='replace') if question else '(aucune)'}")

print()
print("=" * 74)
print("  VERDICT")
print("=" * 74)
print()
if paquets:
    print("  La capture fonctionne sur cette machine.")
    print("  Scapy + Npcap lisent le trafic reel : l'architecture peut reposer dessus.")
else:
    print("  La capture NE fonctionne PAS. Point bloquant.")
