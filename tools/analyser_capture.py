"""
Appliquer les regles de detection a une capture enregistree.

Usage :
    python tools/analyser_capture.py          (la capture la plus recente)
    python tools/analyser_capture.py 6        (la capture numero 6)

Cet outil sert a deux choses :

    - verifier que les regles se comportent correctement sur des donnees REELLES,
      et non seulement sur les cas fabriques par les tests ;
    - lire le detail des alertes sans passer par le navigateur.

Il ne modifie rien : il lit la base et affiche.
"""

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from analyse.adresses import adresse_complete  # noqa: E402
from communications.regroupement import statistiques  # noqa: E402
from detection import analyser  # noqa: E402
from explication.adaptateur import depuis_ligne_enregistree  # noqa: E402
from stockage import supabase  # noqa: E402

disponible, raison = supabase.disponible()
if not disponible:
    print(f"  Base indisponible : {raison}")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# Quelle capture analyser ?
# ---------------------------------------------------------------------------
if len(sys.argv) > 1:
    analyse_id = int(sys.argv[1])
else:
    recentes = supabase.lire("reseau_analyses", ordre="id.desc", limite=1)
    if not recentes:
        print("  Aucune capture enregistree.")
        raise SystemExit(0)
    analyse_id = recentes[0]["id"]

analyses = supabase.lire("reseau_analyses", f"id=eq.{analyse_id}", limite=1)
if not analyses:
    print(f"  La capture n°{analyse_id} n'existe pas.")
    raise SystemExit(1)

analyse = analyses[0]
lignes = supabase.lire("reseau_communications", f"analyse_id=eq.{analyse_id}", limite=500)
communications = [depuis_ligne_enregistree(l) for l in lignes]
contexte = statistiques(communications)

print()
print("=" * 78)
print(f"  DETECTION SUR LA CAPTURE N°{analyse_id}")
print("=" * 78)
print()
print(f"  interface       : {analyse.get('interface')}")
print(f"  debut           : {analyse.get('debut')}")
print(f"  paquets vus     : {analyse.get('nb_paquets')}")
print(f"  communications  : {len(communications)} lues sur {analyse.get('nb_communications')}")

# ---------------------------------------------------------------------------
# Les alertes
# ---------------------------------------------------------------------------
alertes = analyser(communications, contexte)

print()
print(f"  ALERTES : {len(alertes)}")
print()

if not alertes:
    print("  Aucune regle ne s'est declenchee. Sur une capture de navigation")
    print("  ordinaire, c'est le resultat attendu — et c'est une information en soi.")
else:
    for a in alertes:
        print(f"  [{a['gravite'].upper():11s}] {a['titre']}")
        print(f"      {a['explication']}")
        print(f"      Sur quoi : {a['base']}")
        if a.get("conseil"):
            print(f"      À faire  : {a['conseil']}")
        print(f"      Communications concernées : {a['nb_communications']}")
        for c in a["communications"][:3]:
            pre = c.get("premiere_extremite") or {}
            sec = c.get("seconde_extremite") or {}
            print(f"        · {adresse_complete(pre.get('ip'), pre.get('port'))} -> "
                  f"{adresse_complete(sec.get('ip'), sec.get('port'))}  "
                  f"({c.get('protocole')}, {c.get('nb_paquets')} paquets)")
        if a["nb_communications"] > 3:
            print(f"        · et {a['nb_communications'] - 3} autre(s)")
        print()

# ---------------------------------------------------------------------------
# Ce qui N'a PAS declenche
# ---------------------------------------------------------------------------
from detection.regles import REGLES  # noqa: E402

declenchees = {a["regle"] for a in alertes}
print("  Regles qui ne se sont pas declenchees :")
for nom, regle in REGLES:
    if nom not in declenchees:
        print(f"    · {nom}")
