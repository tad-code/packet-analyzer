
import time

from flask import redirect, request, session, url_for

from authentification import service
from config import config

CLE = "analyseur_compte"

MESSAGE_SESSION_EXPIREE = "Votre session a expiré. Reconnectez-vous pour continuer."

def utilisateur():

    enregistre = session.get(CLE)
    if not isinstance(enregistre, dict) or not enregistre.get("identifiant"):
        return None
    return enregistre

def identifiant():

    enregistre = utilisateur()
    return enregistre["identifiant"] if enregistre else None

def courriel():

    enregistre = utilisateur()
    return enregistre.get("courriel") if enregistre else None

def connecte():

    return utilisateur() is not None

def ouvrir(connexion):

    session[CLE] = {
        "identifiant": connexion.get("identifiant"),
        "courriel": connexion.get("courriel"),
        "jeton": connexion.get("jeton"),
        "jeton_rafraichissement": connexion.get("jeton_rafraichissement"),
        "expire_a": connexion.get("expire_a"),
    }
    session.permanent = True

def fermer():

    session.pop(CLE, None)

def jeton():

    enregistre = utilisateur()
    if not enregistre:
        return None

    if time.time() < float(enregistre.get("expire_a") or 0) - 60:
        return enregistre.get("jeton")

    try:
        rafraichi = service.rafraichir(enregistre.get("jeton_rafraichissement"))
    except service.ErreurCompte:
        fermer()
        return None

    ouvrir(rafraichi)
    return rafraichi.get("jeton")

def suite_demandee():

    demande = request.args.get("suite") or request.form.get("suite") or ""
    if demande.startswith("/") and not demande.startswith("//"):
        return demande
    return ""

def connexion_requise(vue):

    from functools import wraps

    @wraps(vue)
    def emballage(*args, **kwargs):

        if not identifiant():
            return redirect(url_for("comptes.connexion", suite=request.full_path.rstrip("?")))

        if not jeton():
            return redirect(url_for("comptes.connexion", fin="expiree"))

        return vue(*args, **kwargs)

    return emballage

COMPTE_LOCAL_ESSAYE = {"fait": False}

def ouvrir_compte_local():

    if identifiant() or COMPTE_LOCAL_ESSAYE["fait"]:
        return False
    if not config.compte_local_configure():
        return False

    COMPTE_LOCAL_ESSAYE["fait"] = True

    try:
        connexion = service.connecter(config.compte_local_courriel,
                                      config.compte_local_mot_de_passe)
    except service.ErreurCompte as e:
        print(f"  (compte local refuse : {e.message})")
        return False

    ouvrir(connexion)
    return True
