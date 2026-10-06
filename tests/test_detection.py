"""
Tests des regles de detection.

Ce qui compte ici n'est pas seulement qu'une regle se declenche : c'est qu'elle
NE se declenche PAS a tort. Un outil qui alerte sur du trafic ordinaire sera
ignore, et n'aura servi a rien.
"""

from detection import ATTENTION, INFORMATION, analyser
from detection.regles import (
    regle_connexions_repetees,
    regle_destinations_multiples,
    regle_refus_repetes,
    regle_service_en_clair,
    regle_service_non_identifie,
    regle_volume_important,
)


def communication(**champs):
    """Une communication minimale, completee par ce que le test veut verifier."""
    base = {
        "ip_premiere": "192.168.1.6", "port_premiere": 51000,
        "ip_seconde": "93.184.216.34", "port_seconde": 443,
        "protocole": "TCP", "port_service": 443, "service_probable": "HTTPS",
        "nb_paquets": 20, "octets": 5000, "etat": "terminee", "drapeaux_vus": "AF",
    }
    base.update(champs)
    return base


# ---------------------------------------------------------------------------
# Aucune alerte ne doit dependre de donnees absentes
# ---------------------------------------------------------------------------

def test_aucune_alerte_sur_une_liste_vide():
    assert analyser([]) == []
    assert analyser(None) == []


def test_une_communication_ordinaire_ne_declenche_rien():
    """Le controle le plus important : le silence quand tout va bien."""
    ordinaire = communication()
    assert analyser([ordinaire], {}) == []


def test_chaque_alerte_cite_sa_base():
    """
    Une alerte sans fondement observable n'est pas verifiable — et une alerte
    invérifiable n'a aucune valeur.
    """
    communications = [communication(port_service=23, service_probable="Telnet", octets=9000)]
    for alerte in analyser(communications, {}):
        assert alerte["base"], "une alerte sans base observee"
        assert alerte["titre"] and alerte["explication"]
        assert alerte["gravite"] in ("information", "attention", "vigilance")


def test_une_regle_defaillante_n_empeche_pas_les_autres(monkeypatch):
    """
    Sur des donnees inattendues, une regle peut lever. Les autres doivent
    continuer : une alerte manquante est facheuse, un plantage qui masque tout
    l'est davantage.
    """
    import detection.regles as r

    def casse(communications, contexte):
        raise ValueError("regle volontairement cassee")

    monkeypatch.setattr(r, "REGLES", [("casse", casse)] + r.REGLES)
    resultat = analyser([communication(port_service=23, octets=9000)], {})
    assert any(a["regle"] == "service-en-clair" for a in resultat)


# ---------------------------------------------------------------------------
# Chaque regle : se declenche quand il faut, se taire sinon
# ---------------------------------------------------------------------------

def test_service_en_clair_se_declenche_sur_telnet():
    alertes = regle_service_en_clair([communication(port_service=23, octets=9000)], {})
    assert len(alertes) == 1
    assert alertes[0]["gravite"] == ATTENTION


def test_service_en_clair_ne_se_declenche_pas_sur_https():
    assert regle_service_en_clair([communication(port_service=443, octets=90000)], {}) == []


def test_service_en_clair_ignore_les_echanges_tres_courts():
    """Un paquet isole sur le port 80 n'est pas un echange qu'on peut juger."""
    assert regle_service_en_clair([communication(port_service=80, octets=100)], {}) == []


def test_refus_repetes_se_declenche_a_partir_de_trois():
    deux = [communication(etat="refusee") for _ in range(2)]
    trois = [communication(etat="refusee") for _ in range(3)]
    assert regle_refus_repetes(deux, {}) == []
    assert len(regle_refus_repetes(trois, {})) == 1


def test_connexions_repetees_se_declenche_sur_des_echanges_brefs_et_nombreux():
    lot = [communication(nb_paquets=6, port_premiere=52000 + i) for i in range(10)]
    alertes = regle_connexions_repetees(lot, {})
    assert len(alertes) == 1
    assert "93.184.216.34" in alertes[0]["titre"]


def test_connexions_repetees_ignore_les_echanges_longs():
    """Dix telechargements vers le meme serveur ne sont pas un canal de commande."""
    lot = [communication(nb_paquets=400, port_premiere=52000 + i) for i in range(10)]
    assert regle_connexions_repetees(lot, {}) == []


def test_destinations_multiples_se_declenche_au_dela_du_seuil():
    contexte = {
        "principales_sources": [("192.168.1.6", 40)],
        "principales_destinations": [(f"93.184.{i}.1", 2) for i in range(30)],
    }
    alertes = regle_destinations_multiples([communication()], contexte)
    assert len(alertes) == 1
    assert alertes[0]["gravite"] == INFORMATION


def test_destinations_multiples_se_tait_sous_le_seuil():
    contexte = {
        "principales_sources": [("192.168.1.6", 40)],
        "principales_destinations": [(f"93.184.{i}.1", 2) for i in range(5)],
    }
    assert regle_destinations_multiples([communication()], contexte) == []


def test_volume_important_se_declenche_quand_une_communication_domine():
    lot = [
        communication(octets=8_000_000),
        communication(octets=1000, port_premiere=52001),
        communication(octets=1000, port_premiere=52002),
    ]
    alertes = regle_volume_important(lot, {})
    assert len(alertes) == 1
    # 8 000 000 sur 8 002 000 : le titre ne doit PAS annoncer « 100 % », qui
    # laisserait croire que tout le volume est passe par cette communication.
    assert "100 %" not in alertes[0]["titre"]
    assert "plus de 99 %" in alertes[0]["titre"]


def test_volume_important_ignore_un_trafic_reparti():
    lot = [communication(octets=400_000, port_premiere=52000 + i) for i in range(4)]
    assert regle_volume_important(lot, {}) == []


def test_service_non_identifie_se_declenche_sur_un_port_inconnu_actif():
    alertes = regle_service_non_identifie(
        [communication(port_service=48999, service_probable=None, nb_paquets=80)], {})
    assert len(alertes) == 1


def test_service_non_identifie_ignore_un_port_connu():
    assert regle_service_non_identifie(
        [communication(port_service=443, service_probable="HTTPS", nb_paquets=80)], {}) == []


# ---------------------------------------------------------------------------
# Ordonnancement
# ---------------------------------------------------------------------------

def test_les_alertes_les_plus_graves_viennent_en_premier():
    from detection import VIGILANCE, ordonner

    alertes = [
        {"gravite": INFORMATION, "nb_communications": 1, "regle": "a"},
        {"gravite": VIGILANCE, "nb_communications": 1, "regle": "b"},
        {"gravite": ATTENTION, "nb_communications": 1, "regle": "c"},
    ]
    assert [a["regle"] for a in ordonner(alertes)] == ["b", "c", "a"]
