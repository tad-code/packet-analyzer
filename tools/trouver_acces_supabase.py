"""
Localiser les acces Supabase deja presents sur la machine.

Objectif : reutiliser un projet existant plutot que d'en creer un nouveau.

Regle de securite absolue : ce script n'AFFICHE JAMAIS une valeur secrete. Il indique
seulement :

    - les fichiers qui declarent des variables Supabase ;
    - le NOM de chaque variable ;
    - une forme masquee, qui permet de reconnaitre la variable sans la reveler.

On scanne les emplacements plausibles : les dossiers de projets de l'utilisateur, le
dossier de configuration de Hermes, et les variables d'environnement de la session.
"""

import os
import re
from pathlib import Path

# --- Emplacements a explorer -------------------------------------------------
RACINES = [
    # On cherche dans Documents, sans nommer de dossier d'etablissement :
    # un chemin personnel n'a rien a faire dans un depot.
    Path.home() / "Documents",
    Path.home() / "Documents" / "sprint-python-3",
    Path.home() / "Documents",
    Path(os.environ.get("LOCALAPPDATA", "")) / "hermes",
]

MOTIFS = ("SUPABASE", "supabase")

def masquer(nom: str, valeur: str) -> str:
    """Donne une forme reconnaissable sans reveler le secret."""
    valeur = valeur.strip().strip('"').strip("'")
    if not valeur:
        return "(vide)"
    if valeur.lower() in ("true", "false", "1", "0"):
        return valeur
    # Une URL se montre : elle n'est pas un secret.
    if valeur.startswith(("http://", "https://")):
        return valeur
    return f"{valeur[:4]}…{valeur[-4:]}  ({len(valeur)} caracteres)"


print("=" * 74)
print("  FICHIERS DECLARANT DES VARIABLES SUPABASE")
print("=" * 74)
print()

vus = set()
trouves = []

for racine in RACINES:
    if not racine.exists():
        continue
    # On cherche les fichiers d'environnement, a profondeur limitee.
    for chemin in list(racine.rglob(".env*"))[:400] + list(racine.rglob("*.env"))[:200]:
        if not chemin.is_file() or chemin in vus:
            continue
        # On ignore les environnements virtuels : trop de faux positifs.
        if any(p in chemin.parts for p in (".venv", "venv", "node_modules", "site-packages")):
            continue
        vus.add(chemin)

        try:
            contenu = chemin.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        variables = []
        for ligne in contenu.splitlines():
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#") or "=" not in ligne:
                continue
            nom, valeur = ligne.split("=", 1)
            nom = nom.strip()
            if any(m in nom for m in MOTIFS):
                variables.append((nom, valeur))

        if variables:
            trouves.append((chemin, variables))
            print(f"  {chemin}")
            for nom, valeur in variables:
                print(f"      {nom} = {masquer(nom, valeur)}")
            print()

if not trouves:
    print("  Aucun fichier .env ne declare de variable Supabase.")
    print()

# --- Variables de la session courante ----------------------------------------
print("=" * 74)
print("  VARIABLES D'ENVIRONNEMENT DE LA SESSION")
print("=" * 74)
print()

trouvees = {k: v for k, v in os.environ.items() if "SUPABASE" in k.upper()}
if trouvees:
    for nom, valeur in trouvees.items():
        print(f"  {nom} = {masquer(nom, valeur)}")
else:
    print("  Aucune variable Supabase dans l'environnement de cette session.")

print()
print("=" * 74)
print("  SYNTHESE")
print("=" * 74)
print()
print(f"  Fichiers exploitables : {len(trouves)}")
for chemin, variables in trouves:
    url = [v for n, v in variables if "URL" in n.upper()]
    cle_pub = [v for n, v in variables if any(x in n.upper() for x in ("ANON", "PUBLISHABLE", "PUBLIC"))]
    cle_sec = [v for n, v in variables if any(x in n.upper() for x in ("SERVICE", "SECRET", "PRIVATE"))]
    print(f"    {chemin}")
    print(f"        url projet      : {'oui' if url else 'non'}")
    print(f"        cle publique    : {'oui' if cle_pub else 'non'}")
    print(f"        cle secrete     : {'oui' if cle_sec else 'non'}")
