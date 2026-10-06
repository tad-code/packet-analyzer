"""
Tests de l'acces a la base.

Ces tests n'ouvrent aucune connexion : ils verifient la logique de decision —
quand la base est-elle utilisable, et comment une erreur est-elle traduite en
message comprehensible.

C'est exactement ce que le cahier des charges demande au titre de la gestion des
erreurs : « l'utilisateur ne doit pas etre confronte a des erreurs
incomprehensibles ». Encore faut-il que la traduction soit testee.
"""

import pytest

from stockage import supabase


class ReponseFactice:
    """Imite une reponse HTTP, sans ouvrir de connexion."""

    def __init__(self, statut, corps=None, texte=""):
        self.status_code = statut
        self._corps = corps
        self.text = texte or (str(corps) if corps else "")

    def json(self):
        if self._corps is None:
            raise ValueError("pas de JSON")
        return self._corps


# ---------------------------------------------------------------------------
# La base est-elle utilisable ?
# ---------------------------------------------------------------------------

def test_base_non_configuree_est_signalee(monkeypatch):
    monkeypatch.setattr(supabase.config, "supabase_url", "")
    disponible, raison = supabase.disponible()

    assert disponible is False
    assert "adresse" in raison.lower()


def test_cle_publique_seule_est_insuffisante(monkeypatch):
    """
    La base etant fermee, la cle publique ne peut rien faire.

    Ce message doit etre explicite : sans lui, l'utilisateur verrait une
    historique vide et croirait l'application cassee, alors qu'il manque
    simplement la cle secrete.
    """
    monkeypatch.setattr(supabase.config, "supabase_url", "https://exemple.supabase.co")
    monkeypatch.setattr(supabase.config, "supabase_cle_publique", "cle-publique")
    monkeypatch.setattr(supabase.config, "supabase_cle_secrete", "")

    disponible, raison = supabase.disponible()
    assert disponible is False
    assert "SUPABASE_SECRET_KEY" in raison


def test_base_completement_configuree(monkeypatch):
    monkeypatch.setattr(supabase.config, "supabase_url", "https://exemple.supabase.co")
    monkeypatch.setattr(supabase.config, "supabase_cle_secrete", "cle-secrete")

    disponible, raison = supabase.disponible()
    assert disponible is True


def test_la_cle_secrete_est_preferee(monkeypatch):
    monkeypatch.setattr(supabase.config, "supabase_cle_publique", "publique")
    monkeypatch.setattr(supabase.config, "supabase_cle_secrete", "secrete")

    assert supabase._cle() == "secrete"


def test_la_cle_publique_sert_de_repli(monkeypatch):
    monkeypatch.setattr(supabase.config, "supabase_cle_publique", "publique")
    monkeypatch.setattr(supabase.config, "supabase_cle_secrete", "")

    assert supabase._cle() == "publique"


# ---------------------------------------------------------------------------
# Construction des adresses
# ---------------------------------------------------------------------------

def test_adresse_de_table(monkeypatch):
    monkeypatch.setattr(supabase.config, "supabase_url", "https://exemple.supabase.co")
    assert supabase._adresse("reseau_analyses") == \
        "https://exemple.supabase.co/rest/v1/reseau_analyses"


def test_adresse_avec_filtre(monkeypatch):
    monkeypatch.setattr(supabase.config, "supabase_url", "https://exemple.supabase.co")
    assert supabase._adresse("reseau_communications", "analyse_id=eq.3") == \
        "https://exemple.supabase.co/rest/v1/reseau_communications?analyse_id=eq.3"


def test_les_entetes_portent_la_cle(monkeypatch):
    monkeypatch.setattr(supabase.config, "supabase_cle_secrete", "secrete")
    entetes = supabase._entetes()

    assert entetes["apikey"] == "secrete"
    assert entetes["Authorization"] == "Bearer secrete"


def test_l_insertion_demande_la_ligne_ecrite(monkeypatch):
    """Sans cette preference, la base ne renvoie rien et l'on perd l'identifiant."""
    monkeypatch.setattr(supabase.config, "supabase_cle_secrete", "secrete")
    assert supabase._entetes(representation=True).get("Prefer") == "return=representation"


# ---------------------------------------------------------------------------
# Traduction des erreurs
# ---------------------------------------------------------------------------

def test_table_absente_donne_un_message_qui_indique_la_solution():
    reponse = ReponseFactice(404, {"code": "PGRST205",
                                   "message": "Could not find the table 'public.reseau_analyses'"})
    erreur = supabase._traduire_erreur(reponse, "reseau_analyses")

    assert erreur.kind == "table_absente"
    assert "schema.sql" in erreur.detail


def test_acces_refuse_parle_de_la_cle_secrete():
    """Cas le plus probable en pratique : la RLS est fermee, la cle manque."""
    reponse = ReponseFactice(401, {"message": "permission denied"})
    erreur = supabase._traduire_erreur(reponse, "reseau_analyses")

    assert erreur.kind == "droits"
    assert "SECRET_KEY" in erreur.detail


def test_donnee_refusee_est_distinguee_des_droits():
    reponse = ReponseFactice(400, {"message": "invalid input syntax"})
    erreur = supabase._traduire_erreur(reponse, "reseau_analyses")

    assert erreur.kind == "requete"
    assert "refusé la donnée" in erreur.message


def test_erreur_inconnue_reste_comprehensible():
    reponse = ReponseFactice(500, {"message": "internal error"})
    erreur = supabase._traduire_erreur(reponse, "reseau_analyses")

    assert erreur.kind == "http"
    assert erreur.message  # jamais un message vide


def test_reponse_sans_json_ne_fait_pas_planter_la_traduction():
    reponse = ReponseFactice(500, None, texte="<html>erreur</html>")
    erreur = supabase._traduire_erreur(reponse, "reseau_analyses")
    assert erreur.kind == "http"


# ---------------------------------------------------------------------------
# Enregistrement sans base
# ---------------------------------------------------------------------------

def test_enregistrer_sans_base_leve_une_erreur_claire(monkeypatch):
    monkeypatch.setattr(supabase.config, "supabase_url", "")

    with pytest.raises(supabase.ErreurBase) as capture:
        supabase.inserer("reseau_analyses", {"interface": "Wi-Fi"})

    assert capture.value.kind == "non_configuree"
