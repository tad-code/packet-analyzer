
import time

import requests

from config import config

DELAI = 15

MESSAGES = {
    "invalid_credentials": "Courriel ou mot de passe incorrect.",
    "email_not_confirmed": "Ce compte n'a pas encore été confirmé.",
    "user_already_exists": "Un compte existe déjà avec ce courriel.",
    "email_exists": "Un compte existe déjà avec ce courriel.",
    "weak_password": "Mot de passe trop court : huit caractères au minimum.",
    "email_address_invalid": "Le courriel saisi n'a pas un format valide.",
    "validation_failed": "Le courriel ou le mot de passe n'a pas un format accepté.",
    "over_email_send_rate_limit": "Trop de demandes coup sur coup : réessayez dans une minute.",
    "over_request_rate_limit": "Trop de tentatives : patientez un instant avant de réessayer.",
    "signup_disabled": "La création de comptes est fermée sur cette installation.",
    "user_not_found": "Aucun compte ne porte ce courriel.",
    "session_not_found": "La session a expiré : reconnectez-vous.",
    "refresh_token_not_found": "La session a expiré : reconnectez-vous.",
    "refresh_token_already_used": "La session a expiré : reconnectez-vous.",
    "email_not_provided": "Le courriel est obligatoire.",
    "password_too_short": "Mot de passe trop court : huit caractères au minimum.",
}

class ErreurCompte(Exception):

    def __init__(self, message, detail=None, statut=None):
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.statut = statut

def _adresse(chemin):

    return f"{config.supabase_url}/auth/v1/{chemin}"

def configuration_prete():

    return bool(config.supabase_url and config.supabase_cle_publique)

def _entetes(privileges=False):

    cle = config.supabase_cle_secrete if privileges else config.supabase_cle_publique
    cle = cle or config.supabase_cle_secrete

    entetes = {
        "apikey": cle,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if privileges:
        entetes["Authorization"] = f"Bearer {cle}"
    return entetes

def _corps(reponse):

    try:
        return reponse.json()
    except ValueError:
        return {}

def _traduire(reponse, defaut):

    corps = _corps(reponse)
    if isinstance(corps, list) and corps:
        corps = corps[0]
    if not isinstance(corps, dict):
        corps = {}

    code = corps.get("error_code") or corps.get("code") or ""
    brut = corps.get("msg") or corps.get("message") or ""
    message = MESSAGES.get(code) or MESSAGES.get(brut) or defaut

    return ErreurCompte(message, detail=brut or None, statut=reponse.status_code)

def _appeler(methode, chemin, donnees=None, privileges=False, defaut="L'opération a échoué."):

    if not configuration_prete():
        raise ErreurCompte(
            "L'authentification n'est pas configurée.",
            detail="SUPABASE_URL et SUPABASE_ANON_KEY doivent être renseignées.",
        )

    try:
        reponse = requests.request(
            methode,
            _adresse(chemin),
            headers=_entetes(privileges),
            json=donnees,
            timeout=DELAI,
        )
    except requests.exceptions.Timeout:
        raise ErreurCompte("Le service de comptes n'a pas répondu dans le délai imparti.",
                           detail=f"Délai dépassé : {DELAI} secondes.")
    except requests.exceptions.RequestException as e:
        raise ErreurCompte("Le service de comptes est injoignable.",
                           detail=f"{type(e).__name__} : {e}")

    if reponse.status_code >= 400:
        raise _traduire(reponse, defaut)

    return _corps(reponse)

def _connexion(corps):

    utilisateur = corps.get("user") or {}
    expire_dans = int(corps.get("expires_in") or 3600)

    return {
        "identifiant": utilisateur.get("id"),
        "courriel": utilisateur.get("email"),
        "jeton": corps.get("access_token"),
        "jeton_rafraichissement": corps.get("refresh_token"),
        "expire_a": time.time() + expire_dans,
    }

def connecter(courriel, mot_de_passe):

    courriel = (courriel or "").strip().lower()
    mot_de_passe = mot_de_passe or ""

    if not courriel or not mot_de_passe:
        raise ErreurCompte("Renseignez le courriel et le mot de passe.")

    corps = _appeler("POST", "token?grant_type=password",
                     {"email": courriel, "password": mot_de_passe},
                     defaut="La connexion a échoué.")

    connexion = _connexion(corps)
    if not connexion["identifiant"] or not connexion["jeton"]:
        raise ErreurCompte("La connexion a échoué.",
                           detail="Le service n'a pas renvoyé de session complète.")

    return connexion

def rafraichir(jeton_rafraichissement):

    if not jeton_rafraichissement:
        raise ErreurCompte("La session a expiré : reconnectez-vous.")

    corps = _appeler("POST", "token?grant_type=refresh_token",
                     {"refresh_token": jeton_rafraichissement},
                     defaut="La session a expiré : reconnectez-vous.")

    connexion = _connexion(corps)
    if not connexion["jeton"]:
        raise ErreurCompte("La session a expiré : reconnectez-vous.")
    if not connexion.get("jeton_rafraichissement"):
        connexion["jeton_rafraichissement"] = jeton_rafraichissement
    return connexion

def creer_compte(courriel, mot_de_passe):

    courriel = (courriel or "").strip().lower()
    mot_de_passe = mot_de_passe or ""

    if not courriel or "@" not in courriel:
        raise ErreurCompte("Renseignez un courriel valide.")
    if len(mot_de_passe) < 8:
        raise ErreurCompte("Le mot de passe doit compter au moins huit caractères.")

    corps = _appeler("POST", "admin/users",
                     {"email": courriel, "password": mot_de_passe, "email_confirm": True},
                     privileges=True,
                     defaut="Le compte n'a pas pu être créé.")

    utilisateur = corps if isinstance(corps, dict) else {}
    utilisateur = utilisateur.get("user") or utilisateur
    if not utilisateur.get("id"):
        raise ErreurCompte("La création du compte n'a rien renvoyé d'exploitable.")

    return {"identifiant": utilisateur.get("id"), "courriel": utilisateur.get("email")}

def rechercher(courriel):

    courriel = (courriel or "").strip().lower()

    corps = _appeler("GET", f"admin/users?page=1&per_page=200", privileges=True,
                     defaut="La liste des comptes est indisponible.")

    utilisateurs = corps.get("users") if isinstance(corps, dict) else corps
    for utilisateur in utilisateurs or []:
        if (utilisateur.get("email") or "").lower() == courriel:
            return {"identifiant": utilisateur.get("id"), "courriel": utilisateur.get("email")}
    return None

def utilisateurs():

    corps = _appeler("GET", "admin/users?page=1&per_page=200", privileges=True,
                     defaut="La liste des comptes est indisponible.")

    utilisateurs = corps.get("users") if isinstance(corps, dict) else corps
    return [
        {"identifiant": u.get("id"), "courriel": u.get("email"),
         "cree_le": u.get("created_at")}
        for u in utilisateurs or []
    ]

def creer_ou_retrouver(courriel, mot_de_passe):

    existant = rechercher(courriel)
    if existant:
        return existant, False
    return creer_compte(courriel, mot_de_passe), True

def verifier(courriel, mot_de_passe):

    try:
        connecter(courriel, mot_de_passe)
        return True, "Connexion réussie."
    except ErreurCompte as e:
        return False, e.message
