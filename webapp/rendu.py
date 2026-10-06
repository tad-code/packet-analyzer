

from flask import render_template

from config import config

VERSION = "4.0 — détecter et enrichir"

def rendre(gabarit, page, **contexte):

    communs = {
        "page": page,
        "version": VERSION,
        "mode": "local" if config.capture_locale else "en ligne",

        "lecture_seule": not config.capture_locale,
        "capture_possible": config.capture_locale,
    }
    communs.update(contexte)
    return render_template(gabarit, **communs)
