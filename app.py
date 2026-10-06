

from flask import Flask

from config import config
from webapp.rendu import rendre

def creer_application():

    application = Flask(__name__)

    from webapp.routes import routes
    application.register_blueprint(routes)

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

    from explication.faits import adresse_complete
    application.jinja_env.filters["adresse"] = adresse_complete

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

app = creer_application()

if __name__ == "__main__":
    print()
    print("  Analyseur reseau")
    print(f"  mode : {'local (capture active)' if config.capture_locale else 'en ligne (lecture seule)'}")
    print(f"  adresse : http://{config.hote}:{config.port}")
    print()
    app.run(host=config.hote, port=config.port, debug=config.debug)
