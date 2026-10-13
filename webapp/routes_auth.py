

from flask import Blueprint, redirect, request, url_for

from authentification import service
from authentification import session as session_utilisateur
from config import config
from webapp.rendu import rendre

comptes = Blueprint("comptes", __name__)

MESSAGES = {
    "expiree": session_utilisateur.MESSAGE_SESSION_EXPIREE,
    "deconnecte": "Vous êtes déconnecté. Les données ne sont plus visibles sur ce navigateur.",
}

@comptes.route("/connexion", methods=["GET", "POST"])
def connexion():

    if request.method == "GET" and session_utilisateur.identifiant():
        return redirect(url_for("routes.accueil"))

    suite = session_utilisateur.suite_demandee()
    courriel = ""

    if request.method == "POST":

        courriel = (request.form.get("courriel") or "").strip()
        mot_de_passe = request.form.get("mot_de_passe") or ""

        try:
            ouverte = service.connecter(courriel, mot_de_passe)
        except service.ErreurCompte as e:
            return rendre("connexion.html", "connexion",
                          erreur=e.message, erreur_detail=e.detail,
                          courriel=courriel, suite=suite)

        session_utilisateur.ouvrir(ouverte)

        if suite:
            return redirect(suite)
        return redirect(url_for("routes.accueil"))

    return rendre("connexion.html", "connexion",
                  message=MESSAGES.get(request.args.get("fin")),
                  erreur=None, erreur_detail=None,
                  courriel=courriel, suite=suite)

@comptes.route("/inscription", methods=["GET", "POST"])
def inscription():

    if session_utilisateur.identifiant():
        return redirect(url_for("routes.accueil"))

    if not config.inscription_ouverte:
        return rendre("connexion.html", "connexion",
                      erreur="La création de comptes est fermée sur cette installation.",
                      erreur_detail=None, courriel="", suite="")

    courriel = ""

    if request.method == "POST":

        courriel = (request.form.get("courriel") or "").strip()
        mot_de_passe = request.form.get("mot_de_passe") or ""
        confirmation = request.form.get("confirmation") or ""

        if mot_de_passe != confirmation:
            return rendre("inscription.html", "inscription",
                          erreur="Les deux mots de passe ne correspondent pas.",
                          erreur_detail=None, courriel=courriel)

        if not courriel or "@" not in courriel:
            return rendre("inscription.html", "inscription",
                          erreur="Renseignez un courriel valide.",
                          erreur_detail=None, courriel=courriel)

        if len(mot_de_passe) < 8:
            return rendre("inscription.html", "inscription",
                          erreur="Le mot de passe doit compter au moins huit caractères.",
                          erreur_detail=None, courriel=courriel)

        try:
            service.creer_compte(courriel, mot_de_passe)
            ouverte = service.connecter(courriel, mot_de_passe)
        except service.ErreurCompte as e:
            return rendre("inscription.html", "inscription",
                          erreur=e.message, erreur_detail=e.detail, courriel=courriel)

        session_utilisateur.ouvrir(ouverte)
        return redirect(url_for("routes.accueil"))

    return rendre("inscription.html", "inscription",
                  erreur=None, erreur_detail=None, courriel=courriel)

@comptes.route("/deconnexion", methods=["POST"])
def deconnexion():

    session_utilisateur.fermer()
    return redirect(url_for("routes.accueil", fin="deconnecte"))
