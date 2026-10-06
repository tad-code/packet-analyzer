"""
Tests de l'enrichissement.

Aucun de ces tests ne contacte le reseau : la source est fournie par le test.
Une suite qui depend d'un service externe echoue le jour ou le reseau est coupe,
pour une raison qui n'a rien a voir avec le code.
"""

import pytest

from enrichissement import adresses


# ---------------------------------------------------------------------------
# Quelles adresses meritent d'etre interrogees ?
# ---------------------------------------------------------------------------

def test_les_adresses_privees_ne_sont_pas_interrogees():
    """
    Interroger un service externe sur une adresse 192.168.x.x revelerait la
    structure du reseau local sans rien apprendre : une adresse privee
    n'appartient a aucun pays.
    """
    for privee in ["192.168.1.6", "10.0.0.1", "172.16.0.5", "172.31.255.254",
                   "127.0.0.1", "169.254.1.1", "fe80::1", "::1", "fc00::1", "fd12::3"]:
        assert adresses.est_publique(privee) is False, privee


def test_les_adresses_publiques_sont_interrogees():
    for publique in ["93.184.216.34", "8.8.8.8", "18.233.182.23",
                     "2001:4860:4847:400::", "2606:4700::1111"]:
        assert adresses.est_publique(publique) is True, publique


def test_les_adresses_de_multidiffusion_ne_sont_pas_interrogees():
    """
    Defaut constate sur une vraie capture : 239.255.255.250, utilisee par la
    decouverte de services sur le reseau local, partait a l'API. Le service
    repondait « reserved range » — aucun pays, mais un quota consomme.
    """
    for multicast in ["239.255.255.250", "224.0.0.1", "224.0.0.251",
                      "255.255.255.255", "ff02::fb", "ff02::1"]:
        assert adresses.est_publique(multicast) is False, multicast


def test_un_champ_vide_n_est_pas_interroge():
    assert adresses.est_publique("") is False
    assert adresses.est_publique(None) is False


# ---------------------------------------------------------------------------
# L'interrogation
# ---------------------------------------------------------------------------

def test_seules_les_adresses_publiques_partent_a_l_api():
    demandees = []

    def fausse(adresses_a_interroger):
        demandees.extend(adresses_a_interroger)
        return {ip: {"pays": "France"} for ip in adresses_a_interroger}

    resultat = adresses.enrichir(
        ["192.168.1.6", "93.184.216.34", "10.0.0.1", "18.233.182.23"],
        interroger=fausse, cache={})

    assert demandees == ["93.184.216.34", "18.233.182.23"]
    assert "192.168.1.6" not in resultat


def test_une_adresse_deja_connue_ne_reinterroge_pas_l_api():
    """Le cache existe pour ne pas reposer la meme question a chaque analyse."""
    demandees = []

    def fausse(adresses_a_interroger):
        demandees.extend(adresses_a_interroger)
        return {ip: {"pays": "France"} for ip in adresses_a_interroger}

    cache = {"93.184.216.34": {"pays": "États-Unis"}}
    resultat = adresses.enrichir(["93.184.216.34"], interroger=fausse, cache=cache)

    assert demandees == [], "l'API a ete interrogee pour une adresse deja connue"
    assert resultat["93.184.216.34"]["pays"] == "États-Unis"


def test_l_api_est_interrogee_une_seule_fois_par_adresse():
    demandees = []

    def fausse(adresses_a_interroger):
        demandees.extend(adresses_a_interroger)
        return {}

    adresses.enrichir(["93.184.216.34", "93.184.216.34", "8.8.8.8"],
                      interroger=fausse, cache={})
    assert sorted(demandees) == ["8.8.8.8", "93.184.216.34"]


# ---------------------------------------------------------------------------
# La panne ne doit rien casser
# ---------------------------------------------------------------------------

def test_une_panne_reseau_ne_fait_pas_echouer_l_enrichissement():
    """
    L'enrichissement est un confort. Une panne doit donner moins d'information,
    jamais une erreur : l'analyse doit rester consultable.
    """
    def cassee(adresses_a_interroger):
        raise ConnectionError("reseau injoignable")

    resultat = adresses.enrichir(["93.184.216.34"], interroger=cassee, cache={})
    assert resultat == {}


def test_une_adresse_sans_reponse_est_dite_non_identifiee():
    """L'API a repondu, mais sans resultat : on le retient, sans inventer."""
    def vide(adresses_a_interroger):
        return {ip: {"erreur": "adresse non attribuée"} for ip in adresses_a_interroger}

    resultat = adresses.enrichir(["93.184.216.34"], interroger=vide, cache={})
    assert "non attribuée" in resultat["93.184.216.34"]["erreur"]


# ---------------------------------------------------------------------------
# Mise en phrase
# ---------------------------------------------------------------------------

def test_le_resume_emploie_ce_qui_est_present():
    assert adresses.resume({"organisation": "OVH SAS", "ville": "Roubaix",
                            "pays": "France"}) == "OVH SAS — Roubaix, France"


def test_le_resume_ne_comble_pas_ce_qui_manque():
    assert adresses.resume({"pays": "Allemagne"}) == "Allemagne"
    assert adresses.resume({}) is None
    assert adresses.resume(None) is None


def test_le_resume_d_une_erreur_est_explicite():
    assert "non identifiée" in adresses.resume({"erreur": "quota dépassé"})


def test_un_cache_illisible_ne_fait_pas_planter(monkeypatch, tmp_path):
    """Un cache corrompu ne doit pas empecher l'application de fonctionner."""
    monkeypatch.setattr(adresses, "CACHE", tmp_path / "absent.json")
    assert adresses.lire_cache() == {}

    casse = tmp_path / "casse.json"
    casse.write_text("{ceci n'est pas du json", encoding="utf-8")
    monkeypatch.setattr(adresses, "CACHE", casse)
    assert adresses.lire_cache() == {}
