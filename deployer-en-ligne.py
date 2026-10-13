import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

DOMAINE = "analyseur-reseau.vercel.app"
PROJET = "packet-analyzer"


def lancer(commande):
    resultat = subprocess.run(commande, capture_output=True, text=True, shell=True)
    return (resultat.stdout or "") + (resultat.stderr or "")


def adresse_du_deploiement(sortie):
    bloc = sortie[sortie.find('"deployment"'):] if '"deployment"' in sortie else ""
    correspondance = re.search(r'"url"\s*:\s*"(https://[^"]+)"', bloc)
    if correspondance:
        return correspondance.group(1)
    toutes = re.findall(r"https://%s-[a-z0-9]+-[a-z0-9-]+\.vercel\.app" % PROJET, sortie)
    return toutes[-1] if toutes else None


print()
print("  Deploiement de l'analyseur en ligne")
print("  -----------------------------------")
print()
print("  Envoi en production, cela prend une vingtaine de secondes...")
sortie = lancer("vercel --prod --yes")

adresse = adresse_du_deploiement(sortie)
if not adresse:
    print("  ECHEC : le deploiement n'a pas pu etre identifie.")
    print("  Dernieres lignes recues :")
    print("  " + sortie[-600:].replace("\n", "\n  "))
    sys.exit(1)

print("  Nouvelle version :", adresse)
print()
print("  Pointage de l'adresse publique", DOMAINE, "...")
reponse = lancer('vercel alias set %s %s' % (adresse, DOMAINE))

if "Success" in reponse:
    print("  Fait : %s sert maintenant la nouvelle version." % DOMAINE)
else:
    print("  Reponse inattendue de Vercel :")
    print("  " + reponse[-600:].replace("\n", "\n  "))
    sys.exit(1)

print()
print("  Verification de l'adresse publique...")
try:
    requete = urllib.request.Request(
        "https://%s/" % DOMAINE,
        headers={"User-Agent": "verification-de-deploiement"},
    )
    with urllib.request.urlopen(requete, timeout=30) as r:
        print("  HTTP %s : l'adresse repond." % r.status)
except urllib.error.HTTPError as e:
    print("  HTTP %s : reponse inattendue." % e.code)
except Exception as e:
    print("  L'adresse ne repond pas encore :", str(e)[:80])
    print("  Attendez une minute : Vercel propage parfois le changement.")

print()
