

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from enrichissement import adresses
from stockage import supabase

disponible, raison = supabase.disponible()
if not disponible:
    print(f"  Base indisponible : {raison}")
    raise SystemExit(1)

lignes = supabase.lire("reseau_communications", ordre="id.desc", limite=200)

vues, ordre = set(), []
for l in lignes:
    for ip in (l.get("ip_seconde"), l.get("ip_premiere")):
        if ip and ip not in vues:
            vues.add(ip)
            ordre.append(ip)

publiques = [ip for ip in ordre if adresses.est_publique(ip)]

print()
print("=" * 78)
print("  ENRICHISSEMENT REEL PAR ip-api.com")
print("=" * 78)
print()
print(f"  adresses rencontrees        : {len(ordre)}")
print(f"  dont publiques (interrogees): {len(publiques)}")
print(f"  dont locales (ignorees)     : {len(ordre) - len(publiques)}")
print()

if not publiques:
    print("  Aucune adresse publique a interroger.")
    raise SystemExit(0)

echantillon = publiques[:10]
resultat = adresses.enrichir(echantillon, cache={})

print(f"  reponses obtenues : {len(resultat)} sur {len(echantillon)} demandees")
print()
for ip in echantillon:
    info = resultat.get(ip)
    if not info:
        print(f"    {ip:28s} aucune reponse")
    elif info.get("erreur"):
        print(f"    {ip:28s} {info['erreur']}")
    else:
        print(f"    {ip:28s} {adresses.resume(info)}")
        print(f"        opérateur : {info.get('fournisseur')} · "
              f"réseau : {info.get('reseau')}")
