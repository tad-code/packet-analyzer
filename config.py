

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

    def base_configuree(self):

        return bool(self.supabase_url and self.supabase_cle_secrete)

    def resume(self):

        return {
            "mode": "local" if self.capture_locale else "en ligne",
            "capture_possible": self.capture_locale,
            "base_configuree": self.base_configuree(),
        }

config = Config()
