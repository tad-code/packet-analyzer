"""
Verification de l'ecriture reelle dans Supabase.

Ce script fait ce qu'aucun test unitaire ne peut faire : il parle vraiment a la
base distante. Il deroule un aller-retour complet, et verifie le resultat.

    1. La base est-elle utilisable ?
    2. Ecriture d'une analyse
    3. Ecriture de communications rattachees
    4. Relecture, et comparaison champ par champ
    5. Suppression, et verification de l'effacement en cascade

Les donnees de test sont SUPPRIMEES a la fin : l'historique de l'utilisateur ne
doit pas contenir de trace d'essai, surtout le jour d'une soutenance.

Aucune cle n'est affichee.
"""

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from stockage import supabase  # noqa: E402


def titre(texte):
    print()
    print("=" * 74)
    print(f"  {texte}")
    print("=" * 74)


titre("1. LA BASE EST-ELLE UTILISABLE ?")

disponible, raison = supabase.disponible()
print(f"  disponible : {disponible}")
if not disponible:
    print(f"  raison     : {raison}")
    print()
    print("  La cle a privileges eleves n'est pas encore en place.")
    raise SystemExit(1)

# On montre a quoi ressemble la cle, sans jamais la reveler.
cle = supabase._cle()
genre = "moderne « sb_secret_... »" if cle.startswith("sb_secret") else \
        ("historique « service_role »" if cle.startswith("eyJ") else "non reconnue")
print(f"  cle        : {len(cle)} caracteres, de type {genre}")


# ---------------------------------------------------------------------------
titre("2. ECRITURE D'UNE ANALYSE")

essai = {
    "interface": "Verification",
    "etat": "terminee",
    "nb_paquets": 158,
    "nb_communications": 2,
    "octets": 24680,
    "note": "Trace de verification technique — supprimee automatiquement.",
}

try:
    ecrites = supabase.inserer("reseau_analyses", essai)
except supabase.ErreurBase as e:
    print(f"  ECHEC [{e.kind}] {e.message}")
    print(f"  detail : {(e.detail or '')[:200]}")
    print()
    print("  Piste la plus probable : le script SQL n'a pas encore ete execute")
    print("  dans l'editeur SQL de Supabase (les tables n'existent pas).")
    raise SystemExit(1)

if not ecrites:
    print("  ECHEC : la base n'a rien renvoye.")
    raise SystemExit(1)

analyse_id = ecrites[0]["id"]
print(f"  analyse ecrite, identifiant recu : {analyse_id}")
print(f"  le champ « debut » a ete rempli par la base : {ecrites[0].get('debut')}")


# ---------------------------------------------------------------------------
titre("3. ECRITURE DES COMMUNICATIONS")

communications = [
    {
        "analyse_id": analyse_id,
        "cle": "192.168.1.6:443|93.184.216.34:51234|TCP",
        "ip_premiere": "192.168.1.6", "port_premiere": 51234,
        "ip_seconde": "93.184.216.34", "port_seconde": 443,
        "initiateur": "192.168.1.6",
        "protocole": "TCP", "port_service": 443,
        "service_probable": "HTTPS",
        "nb_paquets": 87, "octets": 21340,
        "etat": "terminee", "drapeaux_vus": "SYN,ACK,PSH,FIN",
        "resume": "Communication chiffree vers un serveur distant.",
    },
    {
        "analyse_id": analyse_id,
        "cle": "192.168.1.6:53|8.8.8.8:49152|UDP",
        "ip_premiere": "192.168.1.6", "port_premiere": 49152,
        "ip_seconde": "8.8.8.8", "port_seconde": 53,
        "initiateur": "192.168.1.6",
        "protocole": "UDP", "port_service": 53,
        "service_probable": "DNS",
        "nb_paquets": 8, "octets": 640,
        "etat": "terminee", "drapeaux_vus": "",
        "resume": "Resolution de nom de domaine.",
    },
]

try:
    ecrites_com = supabase.inserer("reseau_communications", communications)
except supabase.ErreurBase as e:
    print(f"  ECHEC [{e.kind}] {e.message}")
    print(f"  detail : {(e.detail or '')[:200]}")
    raise SystemExit(1)

print(f"  {len(ecrites_com)} communications ecrites")


# ---------------------------------------------------------------------------
titre("4. RELECTURE")

lues_a = supabase.lire("reseau_analyses", "id=eq." + str(analyse_id))
print(f"  analyses retrouvees   : {len(lues_a)}")

if lues_a:
    a = lues_a[0]
    controles = [
        ("interface", a.get("interface"), "Verification"),
        ("nb_paquets", a.get("nb_paquets"), 158),
        ("octets", a.get("octets"), 24680),
        ("etat", a.get("etat"), "terminee"),
    ]
    for nom, obtenu, attendu in controles:
        ok = obtenu == attendu
        print(f"    {nom:14s} : {obtenu!r:28s} {'OK' if ok else 'DIFFERENT de ' + repr(attendu)}")

lues_c = supabase.lire("reseau_communications", "analyse_id=eq." + str(analyse_id))
print(f"  communications lues   : {len(lues_c)}")
for c in lues_c:
    print(f"    {c.get('protocole')} {c.get('ip_premiere')}:{c.get('port_premiere')} -> "
          f"{c.get('ip_seconde')}:{c.get('port_seconde')}  ({c.get('service_probable')})")

# Le tri par port : la base doit savoir repondre a cette question.
tri = supabase.lire("reseau_communications",
                    "analyse_id=eq." + str(analyse_id),
                    ordre="port_service.asc")
print(f"  tri par port croissant : {[c.get('port_service') for c in tri]}")


# ---------------------------------------------------------------------------
titre("5. SUPPRESSION ET EFFACEMENT EN CASCADE")

supprimees = supabase.supprimer("reseau_analyses", "id=eq." + str(analyse_id))
print(f"  analyses supprimees   : {len(supprimees)}")

restantes = supabase.lire("reseau_communications", "analyse_id=eq." + str(analyse_id))
print(f"  communications restantes : {len(restantes)} "
      f"{'— cascade OK' if not restantes else '— PROBLEME : elles auraient du disparaitre'}")

reste_a = supabase.lire("reseau_analyses", "id=eq." + str(analyse_id))
print(f"  analyses restantes    : {len(reste_a)}")

# ---------------------------------------------------------------------------
# Controle de l'ENSEMBLE de la table, et non de la seule ligne de ce script.
# Un essai precedent avait laisse une ligne derriere lui ; ce script avait
# conclu « rien d'autre en base » sans l'avoir verifie. On mesure, on ne
# suppose pas.
# ---------------------------------------------------------------------------
total_a = supabase.compter("reseau_analyses")
total_c = supabase.compter("reseau_communications")
print()
print("  Contenu total de la base :")
print(f"    analyses       : {total_a}")
print(f"    communications : {total_c}")

if total_a:
    print("    Detail (lignes qui ne viennent pas de ce script) :")
    for a in supabase.lire("reseau_analyses", ordre="id.asc"):
        print(f"      id={a.get('id')}  interface={a.get('interface')!r}  "
              f"note={str(a.get('note'))[:50]!r}")

print()
print("=" * 74)
if lues_a and lues_c and not restantes and not reste_a and total_a == 0 and total_c == 0:
    print("  RESULTAT : ECRITURE, LECTURE ET SUPPRESSION VERIFIEES")
    print("  La base ne contient plus aucune donnee d'essai.")
elif lues_a and lues_c and not restantes and not reste_a:
    print("  RESULTAT : ECRITURE, LECTURE ET SUPPRESSION VERIFIEES")
    print(f"  Attention : la base contient {total_a} analyse(s) qui ne viennent pas")
    print("  de ce script — soit une capture reelle, soit une trace d'un essai anterieur.")
else:
    print("  RESULTAT : DES ANOMALIES SUBSISTENT — voir ci-dessus")
print("=" * 74)
