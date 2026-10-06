"""
Etage 8 du projet : identifier les adresses distantes.

Une adresse IP ne dit rien a personne. Ce module demande a un service externe
a qui elle appartient et ou elle se trouve.

Regle de conception : l'enrichissement est un CONFORT, jamais une dependance.
S'il echoue — reseau coupe, quota depasse, service indisponible — l'analyse
reste complete. Les adresses s'affichent, simplement sans pays ni operateur.
"""

from enrichissement.adresses import (  # noqa: F401
    enrichir,
    est_publique,
    lire_cache,
    resume,
)

__all__ = ["enrichir", "est_publique", "resume", "lire_cache"]
