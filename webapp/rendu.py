"""
Rendu des pages.

Toutes les pages passent par la fonction `rendre`. Elle injecte les elements
communs a chaque page (le mode de fonctionnement, la page active pour le menu, la
version) et evite de les repeter dans chaque route.

Pourquoi c'est important : sans cette fonction unique, chaque page devrait
recalculer elle-meme ces valeurs, et un oubli ferait disparaitre le menu ou le
pied de page. Les pages d'erreur passent par ici aussi — sinon une erreur
afficherait une page sans habillage, ce qui est justement le genre de chose que
le cahier des charges interdit.
"""

from flask import render_template

from config import config

# Version affichee en pied de page.
VERSION = "4.0 — détecter et enrichir"


def rendre(gabarit, page, **contexte):
    """
    Produit une page HTML.

    'gabarit' : le fichier de gabarit a utiliser.
    'page'    : le nom de la page, qui sert a marquer l'onglet actif du menu.
    'contexte': les donnees propres a la page.
    """
    communs = {
        "page": page,
        "version": VERSION,
        "mode": "local" if config.capture_locale else "en ligne",
        # En ligne, aucune capture ne peut avoir lieu sur le serveur : l'interface
        # affiche ce qu'une autre machine a enregistre. Le dire evite de laisser
        # croire que l'on regarde sa propre connexion.
        "lecture_seule": not config.capture_locale,
        "capture_possible": config.capture_locale,
    }
    communs.update(contexte)
    return render_template(gabarit, **communs)
