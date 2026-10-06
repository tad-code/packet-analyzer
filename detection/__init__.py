"""
Etage 5 du projet : reperer ce qui merite l'attention.

Les regles vivent dans `regles.py`. Ce module expose le point d'entree.

Terme employe avec soin : une ALERTE n'est pas un verdict. Chaque regle dit ce
qu'elle a observe, ce qu'elle en deduit, et propose une verification — jamais une
conclusion a la place de l'utilisateur.
"""

from detection.regles import (  # noqa: F401
    ATTENTION,
    GRAVITES,
    INFORMATION,
    REGLES,
    VIGILANCE,
    analyser,
    ordonner,
)

__all__ = ["analyser", "ordonner", "REGLES", "GRAVITES",
           "INFORMATION", "ATTENTION", "VIGILANCE"]
