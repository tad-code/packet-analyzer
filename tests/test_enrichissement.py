

import pytest

from enrichissement import adresses

def test_les_adresses_privees_ne_sont_pas_interrogees():

    for privee in ["192.168.1.6", "10.0.0.1", "172.16.0.5", "172.31.255.254",
                   "127.0.0.1", "169.254.1.1", "fe80::1", "::1", "fc00::1", "fd12::3"]:
        assert adresses.est_publique(privee) is False, privee

def test_les_adresses_publiques_sont_interrogees():
    for publique in ["93.184.216.34", "8.8.8.8", "18.233.182.23",
                     "2001:4860:4847:400::", "2606:4700::1111"]:
        assert adresses.est_publique(publique) is True, publique

def test_les_adresses_de_multidiffusion_ne_sont_pas_interrogees():

    for multicast in ["239.255.255.250", "224.0.0.1", "224.0.0.251",
                      "255.255.255.255", "ff02::fb", "ff02::1"]:
        assert adresses.est_publique(multicast) is False, multicast

def test_un_champ_vide_n_est_pas_interroge():
    assert adresses.est_publique("") is False
    assert adresses.est_publique(None) is False

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

def test_une_panne_reseau_ne_fait_pas_echouer_l_enrichissement():

    def cassee(adresses_a_interroger):
        raise ConnectionError("reseau injoignable")

    resultat = adresses.enrichir(["93.184.216.34"], interroger=cassee, cache={})
    assert resultat == {}

def test_une_adresse_sans_reponse_est_dite_non_identifiee():

    def vide(adresses_a_interroger):
        return {ip: {"erreur": "adresse non attribuée"} for ip in adresses_a_interroger}

    resultat = adresses.enrichir(["93.184.216.34"], interroger=vide, cache={})
    assert "non attribuée" in resultat["93.184.216.34"]["erreur"]

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

    monkeypatch.setattr(adresses, "CACHE", tmp_path / "absent.json")
    assert adresses.lire_cache() == {}

    casse = tmp_path / "casse.json"
    casse.write_text("{ceci n'est pas du json", encoding="utf-8")
    monkeypatch.setattr(adresses, "CACHE", casse)
    assert adresses.lire_cache() == {}
