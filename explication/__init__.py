"""
Etage 6 du projet : transformer des faits observes en phrases comprehensibles.

C'est la fonctionnalite centrale du cahier des charges. Elle repose sur une
regle simple, et non negociable :

    ce qui est OBSERVE et ce qui est DEDUIT ne sont jamais melanges.

Chaque phrase produite sait de quel fait elle provient. Quand une donnee
manque, on l'annonce au lieu de la combler.

Point d'entree :

    from explication import expliquer
    explication = expliquer(communication)

    explication["resume"]           la phrase principale
    explication["faits"]            ce qui a ete vu
    explication["constats"]         ce qui en a ete deduit, et sur quoi
    explication["comptes"]          combien d'observations, combien d'hypotheses
"""

from explication.phrases import (  # noqa: F401
    HYPOTHESE,
    INTERPRETATION,
    NIVEAUX,
    OBSERVATION,
    expliquer,
    interpreter,
    resumer,
)

__all__ = [
    "expliquer",
    "interpreter",
    "resumer",
    "OBSERVATION",
    "INTERPRETATION",
    "HYPOTHESE",
    "NIVEAUX",
]
