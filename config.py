"""
Configuration de l'application.

Ce module est le seul endroit du projet qui lit les variables d'environnement.
Tout le reste demande ses reglages ici. Cela evite qu'un secret se retrouve
disperse dans le code, et cela rend le changement de mode evident.

Deux modes :

    - mode LOCAL  (CAPTURE_LOCALE=1) : l'application tourne sur la machine de
      l'analyste. Elle peut capturer les paquets de la carte reseau.

    - mode EN LIGNE : l'application tourne sur un serveur distant. Elle ne
      capture rien — un serveur n'a acces a aucune carte reseau — et se contente
      de lire les resultats enregistres dans Supabase.

Pourquoi cette distinction des le depart : le module de capture a besoin du pilote
Npcap et des droits administrateur. Sur un serveur, ces deux choses n'existent pas.
Sans cette precaution, l'application refuserait purement et simplement de demarrer.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Le dossier qui contient ce fichier : la racine du projet.
RACINE = Path(__file__).resolve().parent

# Lecture du fichier .env s'il existe. Ce fichier n'est jamais versionne : il
# contient les secrets et reste sur la machine.
load_dotenv(RACINE / ".env")


def _booleen(nom, defaut="0"):
    """Lit une variable d'environnement qui vaut 1 ou 0."""
    return os.getenv(nom, defaut).strip() == "1"


class Config:
    """Reglages de l'application, lus une seule fois au demarrage."""

    def __init__(self):
        # --- Mode de fonctionnement -----------------------------------------
        # Par defaut, on est en local : c'est le cas normal sur la machine de
        # l'analyste. Sur l'hebergeur, CAPTURE_LOCALE vaudra 0.
        self.capture_locale = _booleen("CAPTURE_LOCALE", "1")

        # --- Serveur web ------------------------------------------------------
        self.hote = os.getenv("HOST", "127.0.0.1")
        self.port = int(os.getenv("PORT", "5000"))
        self.debug = _booleen("DEBUG", "0")

        # --- Base de donnees Supabase ----------------------------------------
        # L'URL et la cle publique ne sont pas des secrets : elles peuvent
        # apparaitre dans un navigateur. La cle secrete, elle, ne doit JAMAIS
        # quitter le serveur.
        self.supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.supabase_cle_publique = os.getenv("SUPABASE_ANON_KEY", "")

        # La cle a privileges eleves. Deux noms possibles, et c'est volontaire :
        #
        #   - SUPABASE_SECRET_KEY      : la cle moderne, « sb_secret_... » ;
        #   - SUPABASE_SERVICE_ROLE_KEY : la cle historique, encore valable.
        #
        # Supabase n'a pas supprime les anciennes cles : les deux systemes
        # fonctionnent en parallele. Accepter les deux evite de bloquer
        # l'utilisateur sur un detail de nommage — d'autant que la cle moderne
        # ne s'affiche qu'une fois, alors que l'ancienne reste consultable.
        self.supabase_cle_secrete = (
            os.getenv("SUPABASE_SECRET_KEY", "")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        )

        # --- Capture ----------------------------------------------------------
        # Nombre de paquets conserves en memoire pour l'affichage. Au-dela, les
        # plus anciens sont oublies : sans cette limite, une capture longue
        # finirait par saturer la memoire de la machine.
        self.taille_tampon = int(os.getenv("TAILLE_TAMPON", "500"))

        # Interface ecoutee si l'utilisateur n'en choisit pas.
        self.interface_defaut = os.getenv("INTERFACE_DEFAUT", "")

    # --- Aides ---------------------------------------------------------------

    def base_configuree(self):
        """
        La base est-elle REELLEMENT utilisable ?

        On exige la cle secrete, et non simplement une cle quelconque. La
        securite par ligne est fermee sur les tables du projet : la cle publique
        ne peut donc ni lire ni ecrire. Repondre « oui » parce qu'une cle
        publique est presente faisait annoncer a la sonde /health que la base
        etait prete alors qu'aucune operation n'aurait abouti — exactement le
        genre de mensonge qu'un outil d'analyse ne doit pas se permettre.
        """
        return bool(self.supabase_url and self.supabase_cle_secrete)

    def resume(self):
        """Petit dictionnaire affiche en pied de page et sur la page /health."""
        return {
            "mode": "local" if self.capture_locale else "en ligne",
            "capture_possible": self.capture_locale,
            "base_configuree": self.base_configuree(),
        }


# Instance unique, importee par les autres modules.
config = Config()
