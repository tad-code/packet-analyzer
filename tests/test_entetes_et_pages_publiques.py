

import re
from pathlib import Path

import pytest

from app import app as application
from config import config
from webapp import routes as routes_module

RACINE = Path(__file__).resolve().parent.parent

PAGES_PUBLIQUES_SANS_COMPTE = [
    "/",
    "/connexion",
    "/inscription",
    "/glossaire",
    "/installation",
    "/confidentialite",
    "/mentions-legales",
]

ENTETES_ATTENDUS = {
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Content-Type-Options": "nosniff",
}

@pytest.fixture
def client():

    application.config["TESTING"] = True
    with application.test_client() as c:
        yield c

@pytest.fixture
def sans_compte_local(monkeypatch):

    monkeypatch.setattr(config, "compte_local_courriel", "")
    monkeypatch.setattr(config, "compte_local_mot_de_passe", "")

def test_les_deux_pages_legales_repondent_sans_compte(client, sans_compte_local, monkeypatch):

    monkeypatch.setattr(routes_module.supabase, "lire",
                        lambda *a, **k: pytest.fail("une page legale ne lit aucune donnee"))

    for chemin in ("/confidentialite", "/mentions-legales"):
        reponse = client.get(chemin)
        assert reponse.status_code == 200, chemin

def test_la_page_de_confidentialite_dit_l_essentiel(client, sans_compte_local):

    page = client.get("/confidentialite").get_data(as_text=True)

    for repere in ["Politique de confidentialité", "Vercel", "Supabase",
                   "tad-code", "suppression de votre compte", ".env",
                   "Aucun traceur publicitaire", "Dernière mise à jour"]:
        assert repere in page, repere

def test_les_mentions_legales_disent_l_essentiel(client, sans_compte_local):

    page = client.get("/mentions-legales").get_data(as_text=True)

    for repere in ["Mentions légales", "Éditeur", "Hébergement", "Propriété intellectuelle",
                   "Contact", "autorisé à observer", "tad-code"]:
        assert repere in page, repere

def test_les_deux_pages_legales_ne_nomment_ni_personne_ni_etablissement(client, sans_compte_local):

    pages = " ".join(client.get(chemin).get_data(as_text=True)
                     for chemin in ("/confidentialite", "/mentions-legales"))

    for mot in ["lycée", "lycee", "collège", "college", "université", "universite",
                "école", "ecole", "IUT", "BTS"]:
        assert mot.lower() not in pages.lower(), mot

def test_le_pied_de_page_pointe_vers_les_deux_pages_legales(client, sans_compte_local):

    page = client.get("/").get_data(as_text=True)

    assert "/confidentialite" in page
    assert "/mentions-legales" in page

def test_toutes_les_pages_publiques_repondent_sans_compte(client, sans_compte_local):

    for chemin in PAGES_PUBLIQUES_SANS_COMPTE:
        assert client.get(chemin).status_code == 200, chemin

def test_une_reponse_du_site_porte_la_politique_de_securite(client, sans_compte_local):

    entetes = client.get("/").headers

    assert "Content-Security-Policy" in entetes
    for nom, valeur in ENTETES_ATTENDUS.items():
        assert entetes.get(nom) == valeur, nom
    assert "Strict-Transport-Security" in entetes
    assert "max-age=" in entetes["Strict-Transport-Security"]
    assert "Permissions-Policy" in entetes

def test_la_csp_interdit_l_integration_dans_un_cadre(client, sans_compte_local):

    csp = client.get("/").headers["Content-Security-Policy"]

    assert "frame-ancestors 'none'" in csp
    assert "default-src 'self'" in csp
    assert "'unsafe-inline'" not in csp
    assert "'unsafe-eval'" not in csp
    assert "object-src 'none'" in csp

def test_les_entetes_sont_poses_aussi_sur_les_erreurs_et_l_etat(client, sans_compte_local):

    for chemin in ("/health", "/page-qui-n-existe-pas"):
        entetes = client.get(chemin).headers
        assert "Content-Security-Policy" in entetes, chemin
        assert entetes["X-Frame-Options"] == "DENY", chemin

def test_les_gabarits_n_ont_ni_script_ni_style_en_ligne():

    gabarits = sorted((RACINE / "templates").rglob("*.html"))
    assert gabarits

    for gabarit in gabarits:
        texte = gabarit.read_text(encoding="utf-8")
        for balise in re.findall(r"<script\b[^>]*>", texte, re.IGNORECASE):
            assert "src=" in balise, f"{gabarit.name} : script en ligne"
        assert 'style="' not in texte, f"{gabarit.name} : style en ligne"
        assert "javascript:" not in texte, f"{gabarit.name} : lien javascript:"

def test_le_rafraichissement_automatique_de_la_capture_est_conserve(client, sans_compte_local, monkeypatch):

    monkeypatch.setattr(routes_module.moteur, "en_cours", lambda: True)
    page = client.get("/glossaire").get_data(as_text=True)

    assert 'http-equiv="refresh"' in page
