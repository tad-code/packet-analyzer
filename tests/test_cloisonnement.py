

import time
from pathlib import Path

import pytest

from app import app as application
from authentification import service
from authentification import session as session_utilisateur
from config import config
from stockage import supabase
from webapp import routes as routes_module

RACINE = Path(__file__).resolve().parent.parent

COMPTE_A = {"identifiant": "11111111-1111-1111-1111-111111111111",
            "courriel": "compte-a@example.com", "jeton": "jeton-a"}

COMPTE_B = {"identifiant": "22222222-2222-2222-2222-222222222222",
            "courriel": "compte-b@example.com", "jeton": "jeton-b"}

PAGES_DE_DONNEES = [
    "/historique",
    "/historique/17",
    "/historique/17/communication/476",
    "/communications",
    "/communication/une-cle",
    "/alertes",
    "/protocoles",
    "/capture",
]

class ReponseFactice:

    def __init__(self, statut, corps=None, texte=""):
        self.status_code = statut
        self._corps = corps
        self.text = texte or (str(corps) if corps else "")
        self.content = b"corps"

    def json(self):
        if self._corps is None:
            raise ValueError("pas de JSON")
        return self._corps

@pytest.fixture
def client():

    application.config["TESTING"] = True
    with application.test_client() as c:
        yield c

@pytest.fixture
def base_prete(monkeypatch):

    monkeypatch.setattr(config, "supabase_url", "https://exemple.supabase.co")
    monkeypatch.setattr(config, "supabase_cle_publique", "cle-publique")
    monkeypatch.setattr(config, "supabase_cle_secrete", "cle-secrete")
    monkeypatch.setattr(config, "compte_local_courriel", "")
    monkeypatch.setattr(config, "compte_local_mot_de_passe", "")

def ouvrir(client, compte, expire_dans=3600):

    with client.session_transaction() as session_flask:
        session_flask["analyseur_compte"] = {
            "identifiant": compte["identifiant"],
            "courriel": compte["courriel"],
            "jeton": compte["jeton"],
            "jeton_rafraichissement": "jeton-de-rafraichissement",
            "expire_a": time.time() + expire_dans,
        }

def test_les_pages_de_donnees_refusent_un_visiteur_sans_compte(client, base_prete, monkeypatch):

    for chemin in PAGES_DE_DONNEES:
        reponse = client.get(chemin)
        assert reponse.status_code == 302, chemin
        assert "/connexion" in reponse.headers["Location"], chemin

def test_le_glossaire_et_l_etat_restent_publics(client, base_prete):

    assert client.get("/glossaire").status_code == 200
    assert client.get("/health").status_code == 200

def test_le_mode_d_emploi_d_installation_est_public_et_complet(client, base_prete):

    reponse = client.get("/installation")

    assert reponse.status_code == 200
    page = reponse.get_data(as_text=True)
    for repere in ["Exemple complet d'environnement", "Npcap",
                   "ANALYSEUR_COMPTE_COURRIEL", "demarrer-analyseur.bat",
                   "verifier_prerequis.py", "127.0.0.1"]:
        assert repere in page, repere

def test_le_mode_d_emploi_ne_lit_aucune_donnee(client, base_prete, monkeypatch):

    monkeypatch.setattr(routes_module.supabase, "lire",
                        lambda *a, **k: pytest.fail("lecture de la base sans compte connecté"))

    assert client.get("/installation").status_code == 200

def test_la_page_capture_affiche_le_mode_d_emploi_complet(client, base_prete, monkeypatch):

    ouvrir(client, COMPTE_A)
    monkeypatch.setattr(config, "capture_locale", False)
    monkeypatch.setattr(routes_module.supabase, "lire", lambda *a, **k: [])

    reponse = client.get("/capture")

    assert reponse.status_code == 200
    page = reponse.get_data(as_text=True)
    for repere in ["Capture impossible depuis ce serveur",
                   "Exemple complet d'environnement",
                   "Le mode d'emploi, étape par étape",
                   "ANALYSEUR_COMPTE_COURRIEL",
                   "verifier_prerequis.py",
                   "Ce qui bloque le plus souvent"]:
        assert repere in page, repere

def test_l_accueil_public_n_expose_aucune_capture(client, base_prete, monkeypatch):

    monkeypatch.setattr(routes_module.supabase, "lire",
                        lambda *a, **k: pytest.fail("lecture de la base sans compte connecté"))
    reponse = client.get("/")

    assert reponse.status_code == 200
    assert "privées par utilisateur" in reponse.get_data(as_text=True)

def test_l_historique_ne_demande_que_les_captures_du_compte(client, base_prete, monkeypatch):

    appels = []

    def lire_factice(table, filtre="", limite=None, ordre=None, jeton=None):
        appels.append((table, filtre, jeton))
        return []

    monkeypatch.setattr(routes_module.supabase, "lire", lire_factice)
    ouvrir(client, COMPTE_A)

    assert client.get("/historique").status_code == 200
    assert appels
    for table, filtre, jeton in appels:
        assert f"proprietaire_id=eq.{COMPTE_A['identifiant']}" in filtre
        assert jeton == COMPTE_A["jeton"]

def test_aucune_lecture_de_donnees_ne_se_fait_avec_la_cle_de_service(client, base_prete, monkeypatch):

    jetons = []

    def lire_factice(table, filtre="", limite=None, ordre=None, jeton=None):
        jetons.append(jeton)
        return []

    monkeypatch.setattr(routes_module.supabase, "lire", lire_factice)
    ouvrir(client, COMPTE_B)

    client.get("/historique")
    client.get("/communications")
    client.get("/alertes")

    assert jetons
    assert all(jeton == COMPTE_B["jeton"] for jeton in jetons)

def test_l_acces_direct_a_la_capture_d_un_autre_compte_est_refuse(client, base_prete, monkeypatch):

    def lire_factice(table, filtre="", limite=None, ordre=None, jeton=None):
        if jeton:
            return []
        return [{"id": 17, "proprietaire_id": COMPTE_A["identifiant"]}]

    monkeypatch.setattr(routes_module.supabase, "lire", lire_factice)
    ouvrir(client, COMPTE_B)

    reponse = client.get("/historique/17")

    assert reponse.status_code == 403
    page = reponse.get_data(as_text=True)
    assert "Accès refusé" in page
    assert "Wi-Fi" not in page

def test_la_communication_d_un_autre_compte_est_refusee(client, base_prete, monkeypatch):

    def lire_factice(table, filtre="", limite=None, ordre=None, jeton=None):
        if jeton:
            return []
        return [{"id": 17, "proprietaire_id": COMPTE_A["identifiant"]}]

    monkeypatch.setattr(routes_module.supabase, "lire", lire_factice)
    ouvrir(client, COMPTE_B)

    reponse = client.get("/historique/17/communication/476")

    assert reponse.status_code == 403

def test_une_capture_inexistante_donne_une_page_introuvable(client, base_prete, monkeypatch):

    monkeypatch.setattr(routes_module.supabase, "lire", lambda *a, **k: [])
    ouvrir(client, COMPTE_A)

    reponse = client.get("/historique/9999")

    assert reponse.status_code == 404
    assert "introuvable" in reponse.get_data(as_text=True).lower()

def test_le_compte_voit_sa_propre_capture(client, base_prete, monkeypatch):

    def lire_factice(table, filtre="", limite=None, ordre=None, jeton=None):
        if table == "reseau_analyses":
            return [{"id": 17, "interface": "Wi-Fi", "nb_paquets": 500, "octets": 110700,
                     "nb_communications": 13, "etat": "terminee",
                     "debut": "2026-10-13T10:36:19", "proprietaire_id": COMPTE_A["identifiant"]}]
        return []

    monkeypatch.setattr(routes_module.supabase, "lire", lire_factice)
    ouvrir(client, COMPTE_A)

    reponse = client.get("/historique/17")

    assert reponse.status_code == 200
    assert "Capture n°17" in reponse.get_data(as_text=True)

def test_le_proprietaire_est_ecrit_avec_la_capture(monkeypatch):

    ecrites = {}

    def inserer_factice(table, donnees, jeton=None):
        ecrites[table] = donnees if isinstance(donnees, list) else [donnees]
        return [{"id": 42}]

    monkeypatch.setattr(supabase, "inserer", inserer_factice)

    identifiant, nombre = supabase.enregistrer_analyse(
        interface="Wi-Fi", paquets=12, communications=[], proprietaire=COMPTE_A["identifiant"])

    assert identifiant == 42
    assert ecrites["reseau_analyses"][0]["proprietaire_id"] == COMPTE_A["identifiant"]

def test_l_enregistrement_sans_proprietaire_reste_possible(monkeypatch):

    ecrites = {}

    def inserer_factice(table, donnees, jeton=None):
        ecrites[table] = donnees if isinstance(donnees, list) else [donnees]
        return [{"id": 1}]

    monkeypatch.setattr(supabase, "inserer", inserer_factice)

    supabase.enregistrer_analyse(interface="Wi-Fi", paquets=1, communications=[])

    assert ecrites["reseau_analyses"][0]["proprietaire_id"] is None

def test_les_entetes_avec_jeton_utilisent_la_cle_publique(monkeypatch):

    monkeypatch.setattr(supabase.config, "supabase_cle_publique", "publique")
    monkeypatch.setattr(supabase.config, "supabase_cle_secrete", "secrete")

    entetes = supabase._entetes(jeton="jeton-du-compte")

    assert entetes["apikey"] == "publique"
    assert entetes["Authorization"] == "Bearer jeton-du-compte"

def test_les_entetes_sans_jeton_utilisent_la_cle_secrete(monkeypatch):

    monkeypatch.setattr(supabase.config, "supabase_cle_publique", "publique")
    monkeypatch.setattr(supabase.config, "supabase_cle_secrete", "secrete")

    entetes = supabase._entetes()

    assert entetes["apikey"] == "secrete"
    assert entetes["Authorization"] == "Bearer secrete"

def test_la_lecture_avec_jeton_refuse_la_cle_de_service(monkeypatch):

    monkeypatch.setattr(supabase.config, "supabase_url", "https://exemple.supabase.co")
    monkeypatch.setattr(supabase.config, "supabase_cle_publique", "publique")
    monkeypatch.setattr(supabase.config, "supabase_cle_secrete", "secrete")
    vues = {}

    def requete_factice(methode, adresse, headers=None, json=None, timeout=None):
        vues.update(headers)
        return ReponseFactice(200, [])

    monkeypatch.setattr(supabase.requests, "request", requete_factice)

    supabase.lire("reseau_analyses", jeton="jeton-du-compte")

    assert vues["Authorization"] == "Bearer jeton-du-compte"
    assert vues["apikey"] == "publique"

def test_le_jeton_est_rafraichi_quand_il_expire(monkeypatch):

    monkeypatch.setattr(service, "rafraichir", lambda jeton: {
        "identifiant": COMPTE_A["identifiant"], "courriel": COMPTE_A["courriel"],
        "jeton": "jeton-rafraichi", "jeton_rafraichissement": "r2",
        "expire_a": time.time() + 3600})

    with application.test_request_context("/"):
        ouvrir_direct = {"identifiant": COMPTE_A["identifiant"], "courriel": COMPTE_A["courriel"],
                         "jeton": "jeton-perime", "jeton_rafraichissement": "r1",
                         "expire_a": time.time() - 10}
        session_utilisateur.ouvrir(ouvrir_direct)

        assert session_utilisateur.jeton() == "jeton-rafraichi"
        assert session_utilisateur.utilisateur()["jeton"] == "jeton-rafraichi"

def test_une_session_impossible_a_rafraichir_ramene_a_la_connexion(monkeypatch):

    def rafraichir_impossible(jeton):
        raise service.ErreurCompte("La session a expiré : reconnectez-vous.")

    monkeypatch.setattr(service, "rafraichir", rafraichir_impossible)

    with application.test_request_context("/"):
        session_utilisateur.ouvrir({"identifiant": COMPTE_A["identifiant"],
                                    "courriel": COMPTE_A["courriel"],
                                    "jeton": "jeton-perime",
                                    "jeton_rafraichissement": "r1",
                                    "expire_a": time.time() - 10})

        assert session_utilisateur.jeton() is None
        assert session_utilisateur.identifiant() is None

def test_la_connexion_renvoie_la_session_du_compte(monkeypatch):

    monkeypatch.setattr(service.config, "supabase_url", "https://exemple.supabase.co")
    monkeypatch.setattr(service.config, "supabase_cle_publique", "publique")
    monkeypatch.setattr(service.requests, "request", lambda *a, **k: ReponseFactice(200, {
        "access_token": "jeton", "refresh_token": "rafraichissement", "expires_in": 3600,
        "user": {"id": COMPTE_A["identifiant"], "email": COMPTE_A["courriel"]}}))

    connexion = service.connecter(COMPTE_A["courriel"], "mot-de-passe")

    assert connexion["identifiant"] == COMPTE_A["identifiant"]
    assert connexion["jeton"] == "jeton"
    assert connexion["expire_a"] > time.time()

def test_un_mot_de_passe_refuse_est_dit_en_francais(monkeypatch):

    monkeypatch.setattr(service.config, "supabase_url", "https://exemple.supabase.co")
    monkeypatch.setattr(service.config, "supabase_cle_publique", "publique")
    monkeypatch.setattr(service.requests, "request",
                        lambda *a, **k: ReponseFactice(400, {"error_code": "invalid_credentials",
                                                             "msg": "Invalid login credentials"}))

    with pytest.raises(service.ErreurCompte) as capture:
        service.connecter(COMPTE_A["courriel"], "mauvais")

    assert capture.value.message == "Courriel ou mot de passe incorrect."

def test_un_mot_de_passe_trop_court_est_refuse_avant_le_reseau(monkeypatch):

    monkeypatch.setattr(service.requests, "request",
                        lambda *a, **k: pytest.fail("aucun appel réseau ne doit partir"))

    with pytest.raises(service.ErreurCompte) as capture:
        service.creer_compte("nouveau@example.com", "court")

    assert "huit caractères" in capture.value.message

def test_la_creation_de_compte_passe_par_la_cle_de_service(monkeypatch):

    monkeypatch.setattr(service.config, "supabase_url", "https://exemple.supabase.co")
    monkeypatch.setattr(service.config, "supabase_cle_publique", "publique")
    monkeypatch.setattr(service.config, "supabase_cle_secrete", "secrete")
    vus = {}

    def requete_factice(methode, adresse, headers=None, json=None, timeout=None):
        vus.update({"adresse": adresse, "headers": headers, "json": json})
        return ReponseFactice(200, {"id": COMPTE_B["identifiant"], "email": COMPTE_B["courriel"]})

    monkeypatch.setattr(service.requests, "request", requete_factice)

    compte = service.creer_compte("nouveau@example.com", "mot-de-passe-solide")

    assert compte["identifiant"] == COMPTE_B["identifiant"]
    assert vus["adresse"].endswith("/auth/v1/admin/users")
    assert vus["headers"]["Authorization"] == "Bearer secrete"
    assert vus["json"]["email_confirm"] is True

def test_sans_configuration_l_authentification_le_dit(monkeypatch):

    monkeypatch.setattr(service.config, "supabase_url", "")
    monkeypatch.setattr(service.config, "supabase_cle_publique", "")

    with pytest.raises(service.ErreurCompte) as capture:
        service.connecter("quelqu-un@example.com", "mot-de-passe")

    assert "n'est pas configurée" in capture.value.message

def test_le_script_sql_pose_les_politiques_de_cloisonnement():

    texte = (RACINE / "sql" / "cloisonnement.sql").read_text(encoding="utf-8")

    assert texte.count("create policy") == 3
    assert texte.count("proprietaire_id = auth.uid()") >= 4
    assert "reseau_analyses" in texte and "reseau_communications" in texte and "reseau_alertes" in texte

def test_le_compte_local_est_utilise_pour_attribuer_les_captures(monkeypatch):

    monkeypatch.setattr(config, "compte_local_courriel", "poste-local@example.com")
    monkeypatch.setattr(config, "compte_local_mot_de_passe", "mot-de-passe-local")
    monkeypatch.setattr(service, "connecter",
                        lambda courriel, mot_de_passe: {"identifiant": COMPTE_A["identifiant"],
                                                        "courriel": courriel, "jeton": "jeton-local",
                                                        "jeton_rafraichissement": "r",
                                                        "expire_a": time.time() + 3600})
    session_utilisateur.COMPTE_LOCAL_ESSAYE["fait"] = False

    with application.test_request_context("/"):
        assert session_utilisateur.ouvrir_compte_local() is True
        assert session_utilisateur.identifiant() == COMPTE_A["identifiant"]


def test_une_requete_de_cette_machine_ouvre_la_session_automatiquement(client, base_prete, monkeypatch):

    monkeypatch.setattr(config, "compte_local_courriel", "poste-local@example.com")
    monkeypatch.setattr(config, "compte_local_mot_de_passe", "mot-de-passe-local")
    monkeypatch.setattr(service, "connecter",
                        lambda courriel, mot_de_passe: {"identifiant": COMPTE_A["identifiant"],
                                                        "courriel": courriel, "jeton": "jeton-local",
                                                        "jeton_rafraichissement": "r",
                                                        "expire_a": time.time() + 3600})
    monkeypatch.setattr(routes_module.supabase, "lire", lambda *a, **k: [])
    session_utilisateur.COMPTE_LOCAL_ESSAYE["fait"] = False

    reponse = client.get("/historique", environ_base={"REMOTE_ADDR": "127.0.0.1"})

    assert reponse.status_code == 200
    with client.session_transaction() as session_flask:
        assert session_flask["analyseur_compte"]["identifiant"] == COMPTE_A["identifiant"]


def test_une_requete_du_reseau_n_ouvre_aucune_session_automatique(client, base_prete, monkeypatch):

    monkeypatch.setattr(config, "compte_local_courriel", "poste-local@example.com")
    monkeypatch.setattr(config, "compte_local_mot_de_passe", "mot-de-passe-local")
    connectes = []
    monkeypatch.setattr(service, "connecter",
                        lambda courriel, mot_de_passe: connectes.append(courriel) or {
                            "identifiant": COMPTE_A["identifiant"], "courriel": courriel,
                            "jeton": "jeton-local", "jeton_rafraichissement": "r",
                            "expire_a": time.time() + 3600})
    monkeypatch.setattr(routes_module.supabase, "lire",
                        lambda *a, **k: pytest.fail("aucune donnee ne doit etre lue sans compte"))
    session_utilisateur.COMPTE_LOCAL_ESSAYE["fait"] = False

    reponse = client.get("/historique", environ_base={"REMOTE_ADDR": "192.168.1.50"})

    assert reponse.status_code == 302
    assert "/connexion" in reponse.headers["Location"]
    assert connectes == []
    with client.session_transaction() as session_flask:
        assert "analyseur_compte" not in session_flask
