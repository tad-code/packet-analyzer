

import hashlib
import os
from pathlib import Path

from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parent

load_dotenv(RACINE / ".env")

def _booleen(nom, defaut="0"):

    return os.getenv(nom, defaut).strip() == "1"

class Config:

    def __init__(self):

        self.capture_locale = _booleen("CAPTURE_LOCALE", "1")

        self.hote = os.getenv("HOST", "127.0.0.1")
        self.port = int(os.getenv("PORT", "5000"))
        self.debug = _booleen("DEBUG", "0")

        self.supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self.supabase_cle_publique = os.getenv("SUPABASE_ANON_KEY", "")

        self.supabase_cle_secrete = (
            os.getenv("SUPABASE_SECRET_KEY", "")
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        )

        self.taille_tampon = int(os.getenv("TAILLE_TAMPON", "500"))

        self.interface_defaut = os.getenv("INTERFACE_DEFAUT", "")

        self.inscription_ouverte = _booleen("INSCRIPTION_OUVERTE", "1")

        self.compte_local_courriel = os.getenv("ANALYSEUR_COMPTE_COURRIEL", "").strip()
        self.compte_local_mot_de_passe = os.getenv("ANALYSEUR_COMPTE_MOT_DE_PASSE", "")

        self.cle_session = os.getenv("FLASK_SECRET_KEY", "").strip() or self._cle_session_calculee()

        self.cookie_securise = _booleen("SESSION_COOKIE_SECURE", "0" if self.capture_locale else "1")

        self.compte_demonstration_courriel = os.getenv(
            "COMPTE_DEMONSTRATION_COURRIEL", "demonstration@example.com")
        self.compte_demonstration_mot_de_passe = os.getenv(
            "COMPTE_DEMONSTRATION_MOT_DE_PASSE", "Demonstration-2026!")
        self.montrer_demonstration = _booleen("MONTRE_COMPTE_DEMONSTRATION", "1")

    def compte_demonstration(self):

        if not self.montrer_demonstration:
            return None
        if not self.compte_demonstration_courriel or not self.compte_demonstration_mot_de_passe:
            return None

        return {
            "courriel": self.compte_demonstration_courriel,
            "mot_de_passe": self.compte_demonstration_mot_de_passe,
        }

    def _cle_session_calculee(self):

        matiere = f"analyseur-reseau|{self.supabase_url}|{self.supabase_cle_secrete}"
        return hashlib.sha256(matiere.encode("utf-8")).hexdigest()

    def compte_local_configure(self):

        return bool(self.compte_local_courriel and self.compte_local_mot_de_passe)

    def authentification_prete(self):

        return bool(self.supabase_url and self.supabase_cle_publique)

    def base_configuree(self):

        return bool(self.supabase_url and self.supabase_cle_secrete)

    def resume(self):

        return {
            "mode": "local" if self.capture_locale else "en ligne",
            "capture_possible": self.capture_locale,
            "base_configuree": self.base_configuree(),
            "comptes_utilisateurs": self.authentification_prete(),
        }

config = Config()
