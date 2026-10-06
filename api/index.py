"""
Point d'entree pour l'hebergeur Vercel.

Un hebergeur sans serveur ne lance pas `python app.py` : il cherche un objet
`app` dans un fichier precis. Ce fichier fait le lien.

Pourquoi la ligne sys.path : l'hebergeur execute ce fichier depuis un dossier
d'execution, et non depuis la racine du projet. Sans l'ajout de la racine au
chemin de recherche, Python ne trouverait pas les modules `capture`, `analyse`,
`webapp`. C'est l'erreur classique au premier deploiement.
"""

import sys
from pathlib import Path

# La racine du projet, un niveau au-dessus de ce fichier (api/index.py).
RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from app import app  # noqa: E402  (l'import doit suivre l'ajout du chemin)

# L'hebergeur utilise directement cet objet.
application = app
