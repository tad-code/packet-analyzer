"""
Point d'entree de l'application.

Ce fichier fait quatre choses, et rien d'autre :

    1. il cree l'application web ;
    2. il y branche les routes ;
    3. il definit ce qui s'affiche quand une erreur survient ;
    4. il lance le serveur quand on execute le fichier directement.

Toute la logique est ailleurs : ici, on ne fait que rassembler les morceaux.

Pourquoi les pages d'erreur passent par le meme rendu que les autres pages : une
page d'erreur sans menu ni habillage donne l'impression que l'application est
casse. Le cahier des charges exige que l'utilisateur ne soit jamais confronte a
un message incomprehensible.
"""

from flask import Flask

from config import config
from webapp.rendu import rendre


def creer_application():
    """Construit et configure l'application web."""
    application = Flask(__name__)

    # --- Branchement des routes ---------------------------------------------
    from webapp.routes import routes
    application.register_blueprint(routes)

    # --- Pages d'erreur -------------------------------------------------------
    # Chaque cas est traite separement, avec un message en francais qui explique
    # ce qui s'est passe et ce que l'utilisateur peut faire.

    @application.errorhandler(400)
    def demande_invalide(e):
        return rendre("erreur.html", "erreur", code=400,
                      titre="Demande invalide",
                      explication="La demande envoyée n'a pas pu être comprise.",
                      detail="Vérifiez le formulaire et recommencez."), 400

    @application.errorhandler(404)
    def page_introuvable(e):
        return rendre("erreur.html", "erreur", code=404,
                      titre="Page introuvable",
                      explication="Cette adresse ne correspond à aucune page de l'application.",
                      detail="Utilisez le menu pour revenir à une page connue."), 404

    @application.errorhandler(405)
    def methode_refusee(e):
        return rendre("erreur.html", "erreur", code=405,
                      titre="Méthode non autorisée",
                      explication="Cette adresse n'accepte pas la méthode employée.",
                      detail="Les actions de capture se déclenchent depuis les boutons de la page."), 405

    @application.errorhandler(413)
    def trop_volumineux(e):
        return rendre("erreur.html", "erreur", code=413,
                      titre="Données trop volumineuses",
                      explication="La demande envoyée dépasse la taille acceptée.",
                      detail="Réduisez la taille des données transmises."), 413

    @application.errorhandler(500)
    def erreur_interne(e):
        return rendre("erreur.html", "erreur", code=500,
                      titre="Erreur interne",
                      explication="Une erreur inattendue est survenue dans l'application.",
                      detail="L'incident a été signalé. Vous pouvez poursuivre votre travail."), 500

    # Un filtre de gabarit, disponible dans toutes les pages. Sans lui, chaque
    # gabarit formaterait les adresses a sa maniere — et l'un d'eux oublierait
    # les crochets des adresses IPv6.
    from explication.faits import adresse_complete
    application.jinja_env.filters["adresse"] = adresse_complete

    # Un filtre pour les volumes : les gabarits repetent sinon le meme calcul
    # dans chaque tableau, avec le risque d'oublier un cas.
    def volume(octets):
        if octets is None:
            return "—"
        if octets >= 1024 * 1024:
            return f"{octets / (1024 * 1024):.2f} Mo"
        if octets >= 1024:
            return f"{octets / 1024:.1f} Ko"
        return f"{octets} o"

    application.jinja_env.filters["volume"] = volume

    return application


# Instance utilisee par le serveur de developpement et par l'hebergeur.
app = creer_application()


if __name__ == "__main__":
    print()
    print("  Analyseur reseau")
    print(f"  mode : {'local (capture active)' if config.capture_locale else 'en ligne (lecture seule)'}")
    print(f"  adresse : http://{config.hote}:{config.port}")
    print()
    app.run(host=config.hote, port=config.port, debug=config.debug)
