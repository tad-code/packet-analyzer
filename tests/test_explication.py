
from communications.regroupement import regrouper
from explication.faits import faits_observes, resume_chiffre
from explication.phrases import (
    HYPOTHESE,
    INTERPRETATION,
    OBSERVATION,
    _est_locale,
    expliquer,
    interpreter,
    resumer,
)
from tests.conftest import paquet

def communication_de(paquets, **options):
    return regrouper(paquets, maintenant=options.pop("maintenant", 1000.0))[0]

def test_les_champs_absents_sont_signales_comme_indisponibles():
    communication = {
        "premiere_extremite": {"ip": None, "port": None},
        "seconde_extremite": {"ip": None, "port": None},
        "protocole": None,
        "port_service": None,
        "nb_paquets": None,
        "octets": None,
        "duree": None,
        "drapeaux_vus": None,
        "etat": None,
    }
    faits = faits_observes(communication)

    assert faits, "les faits doivent etre listes meme quand tout manque"
    for fait in faits:
        assert fait["valeur"] == "non disponible", (
            f"le champ {fait['champ']} devrait etre signale comme indisponible, "
            f"or il affiche {fait['valeur']!r}"
        )
        assert fait["disponible"] is False

def test_un_fait_disponible_est_marque_comme_tel():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 443)]
    faits = faits_observes(communication_de(paquets))
    par_champ = {f["champ"]: f for f in faits}

    assert par_champ["premiere_extremite"]["disponible"] is True
    assert par_champ["premiere_extremite"]["valeur"] == "192.168.1.10:51000"
    assert par_champ["port_service"]["valeur"] == "443"

def test_le_resume_chiffre_ne_contient_que_des_donnees_observees():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 443, taille=500)]
    resume = resume_chiffre(communication_de(paquets))

    assert "192.168.1.10" in resume
    assert "443" in resume
    assert "TCP" in resume

def test_le_resume_chiffre_signale_l_absence_de_donnee():
    resume = resume_chiffre({})
    assert "Aucune donnée" in resume

def test_chaque_constat_cite_le_fait_observe_qui_le_fonde():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 443, drapeaux="S")]
    constats = interpreter(communication_de(paquets))

    assert constats, "le port 443 doit produire au moins un constat"
    for constat in constats:
        assert constat.get("base"), f"constat sans base : {constat}"
        assert constat.get("niveau") in (OBSERVATION, INTERPRETATION, HYPOTHESE)
        assert constat.get("texte")

def test_une_regle_qui_ne_s_applique_pas_ne_produit_rien():
    constats = interpreter({"port_service": None, "drapeaux_vus": None})
    textes = [c["texte"] for c in constats]
    assert not any("port" in t.lower() and "généralement" in t for t in textes)

def test_le_port_connu_produit_une_interpretation_prudente():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 443)]
    constats = interpreter(communication_de(paquets))

    service = [c for c in constats if "généralement" in c["texte"]]
    assert service, "le port 443 doit produire une lecture prudente"
    assert service[0]["niveau"] == INTERPRETATION

def test_un_port_inconnu_produit_une_hypothese_et_non_une_affirmation():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 45678)]
    constats = interpreter(communication_de(paquets))

    inconnu = [c for c in constats if "pas pu être identifié" in c["texte"]]
    assert inconnu, "un port inconnu doit etre signale comme tel"
    assert inconnu[0]["niveau"] == HYPOTHESE

def test_un_refus_produit_une_interpretation_qui_n_accuse_personne():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 81, drapeaux="R")]
    constats = interpreter(communication_de(paquets))

    refus = [c for c in constats if "brutalement" in c["texte"]]
    assert refus
    assert "normal" in refus[0]["texte"], (
        "le texte doit rappeler qu'un refus peut etre parfaitement normal"
    )

def test_le_contenu_chiffre_est_annonce_comme_probable():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 443)]
    constats = interpreter(communication_de(paquets))

    chiffre = [c for c in constats if "probablement chiffré" in c["texte"]]
    assert chiffre, "le port 443 doit produire un constat sur le chiffrement"
    assert chiffre[0]["niveau"] == HYPOTHESE

def test_le_resume_distingue_le_reseau_local_du_distant():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 443)]
    resume = resumer(communication_de(paquets))

    assert "réseau local" in resume
    assert "serveur distant" in resume
    assert "généralement associé" in resume

def test_le_resume_s_adapte_quand_les_adresses_manquent():
    resume = resumer({"premiere_extremite": {"ip": None}, "seconde_extremite": {"ip": None}})
    assert "n'ont pas pu être lues" in resume

def test_le_resume_ne_contient_aucune_affirmation_absolue():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 443)]
    resume = resumer(communication_de(paquets))
    assert "est du HTTPS" not in resume
    assert "certainement" not in resume.lower()

def test_reconnaissance_des_adresses_privees():
    assert _est_locale("192.168.1.10") is True
    assert _est_locale("10.0.0.5") is True
    assert _est_locale("172.16.0.1") is True
    assert _est_locale("172.31.255.254") is True
    assert _est_locale("172.32.0.1") is False
    assert _est_locale("127.0.0.1") is True
    assert _est_locale("93.184.216.34") is False
    assert _est_locale("2001:42d8::1") is False
    assert _est_locale("fe80::1") is True
    assert _est_locale(None) is False

def test_explication_complete_sur_une_communication_reelle():
    paquets = [
        paquet("192.168.1.10", "93.184.216.34", 51000, 443, taille=200, drapeaux="S",
               horodatage=1000.0),
        paquet("93.184.216.34", "192.168.1.10", 443, 51000, taille=1400, drapeaux="A",
               horodatage=1000.2),
        paquet("192.168.1.10", "93.184.216.34", 51000, 443, taille=100, drapeaux="F",
               horodatage=1001.0),
    ]
    resultat = expliquer(communication_de(paquets, maintenant=1001.0))

    assert resultat["resume"]
    assert resultat["resume_chiffre"]
    assert resultat["faits"]
    assert resultat["constats"]
    assert resultat["comptes"]["faits_observes"] > 5
    assert resultat["comptes"]["interpretations"] >= 1

def test_l_explication_ne_plante_pas_sur_une_communication_vide():
    resultat = expliquer({"premiere_extremite": {}, "seconde_extremite": {}})
    assert resultat["resume"]
    assert isinstance(resultat["constats"], list)

def test_une_adresse_ipv4_se_lit_normalement():
    from explication.faits import adresse_complete
    assert adresse_complete("192.168.1.6", 443) == "192.168.1.6:443"

def test_une_adresse_ipv6_est_encadree_de_crochets():
    from explication.faits import adresse_complete
    assert adresse_complete("2001:4860:4847:400::", 443) == "[2001:4860:4847:400::]:443"

def test_une_adresse_ipv6_sans_port_est_encadree():
    from explication.faits import adresse_complete
    assert adresse_complete("2001:db8::1") == "[2001:db8::1]"

def test_les_deux_formes_d_une_communication_donnent_leurs_adresses():
    from analyse.adresses import adresses_de

    vivante = {"premiere_extremite": {"ip": "192.168.1.6", "port": 51000},
               "seconde_extremite": {"ip": "93.184.216.34", "port": 443}}
    enregistree = {"ip_premiere": "192.168.1.6", "ip_seconde": "93.184.216.34"}

    assert adresses_de(vivante) == ["192.168.1.6", "93.184.216.34"]
    assert adresses_de(enregistree) == ["192.168.1.6", "93.184.216.34"]
    assert adresses_de({}) == []
    assert adresses_de(None) == []

def test_une_adresse_inconnue_ne_donne_pas_de_texte_trompeur():
    from explication.faits import adresse_complete
    assert adresse_complete("") is None
    assert adresse_complete(None, 443) is None

def test_le_resume_chiffre_encadre_bien_ipv6():
    from explication.faits import resume_chiffre

    communication = {
        "premiere_extremite": {"ip": "2001:4860:4847:400::", "port": 443},
        "seconde_extremite": {"ip": "2001:42d8::1", "port": 50106},
        "protocole": "TCP",
        "port_service": 443,
    }
    texte = resume_chiffre(communication)

    assert "[2001:4860:4847:400::]:443" in texte
    assert ":::" not in texte, "trois deux-points = adresse et port confondus"

def test_une_connexion_sans_fermeture_n_est_pas_dite_active():
    from explication.phrases import resumer

    communication = {
        "premiere_extremite": {"ip": "192.168.1.6", "port": 51000},
        "seconde_extremite": {"ip": "93.184.216.34", "port": 443},
        "protocole": "TCP",
        "port_service": 443,
        "etat": "en cours",
    }
    texte = resumer(communication)

    assert "toujours active" not in texte.lower()
    assert "aucun drapeau de fermeture" in texte.lower()

def test_une_connexion_fermee_est_dite_terminee():
    from explication.phrases import resumer

    communication = {
        "premiere_extremite": {"ip": "192.168.1.6", "port": 51000},
        "seconde_extremite": {"ip": "93.184.216.34", "port": 443},
        "protocole": "TCP",
        "port_service": 443,
        "etat": "terminee",
    }
    assert "terminée normalement" in resumer(communication)

def test_les_drapeaux_compacts_sont_traduits():
    from analyse.protocoles import lire_drapeaux
    assert lire_drapeaux("AFPR") == ["ACK", "FIN", "PSH", "RST"]

def test_la_forme_separee_par_virgules_est_acceptee():
    from analyse.protocoles import lire_drapeaux
    assert lire_drapeaux("SYN,ACK,PSH,FIN") == ["SYN", "ACK", "PSH", "FIN"]

def test_une_lettre_inconnue_est_montree_telle_quelle():
    from analyse.protocoles import lire_drapeaux
    assert lire_drapeaux("AFXZ") == ["ACK", "FIN", "X", "Z"]

def test_aucun_drapeau_ne_donne_aucune_explication():
    from analyse.protocoles import lire_drapeaux, expliquer_drapeaux
    assert lire_drapeaux(None) == []
    assert lire_drapeaux("") == []
    assert expliquer_drapeaux("") == []

def test_seuls_les_drapeaux_vus_sont_expliques():
    from analyse.protocoles import expliquer_drapeaux
    noms = [nom for nom, _ in expliquer_drapeaux("SA")]
    assert noms == ["SYN", "ACK"]
    assert "FIN" not in noms

def test_fin_et_rst_ensemble_ne_donnent_pas_deux_affirmations_contraires():
    from explication.phrases import expliquer

    communication = {
        "premiere_extremite": {"ip": "192.168.1.6", "port": 51000},
        "seconde_extremite": {"ip": "93.184.216.34", "port": 443},
        "protocole": "TCP", "port_service": 443,
        "drapeaux_vus": "AFPR",
        "etat": "terminee",
    }
    textes = " ".join(k["texte"] for k in expliquer(communication)["constats"])

    assert "fermée proprement" not in textes
    assert "interrompue brutalement" not in textes
    assert "des deux manières" in textes

def test_fin_seul_donne_bien_une_fermeture_propre():
    from explication.phrases import expliquer

    communication = {
        "premiere_extremite": {"ip": "192.168.1.6", "port": 51000},
        "seconde_extremite": {"ip": "93.184.216.34", "port": 443},
        "protocole": "TCP", "port_service": 443,
        "drapeaux_vus": "AF", "etat": "terminee",
    }
    textes = " ".join(k["texte"] for k in expliquer(communication)["constats"])
    assert "fermée proprement" in textes

def test_une_ligne_enregistree_devient_comprehensible_par_le_moteur():
    from explication.adaptateur import depuis_ligne_enregistree

    ligne = {
        "ip_premiere": "192.168.1.6", "port_premiere": 51000,
        "ip_seconde": "93.184.216.34", "port_seconde": 443,
        "protocole": "TCP", "port_service": 443, "service_probable": "HTTPS",
        "nb_paquets": 42, "octets": 8192, "duree": 2.5,
        "debut": "2026-10-06T10:39:51.123456+00:00",
        "fin": "2026-10-06T10:39:53.623456+00:00",
        "drapeaux_vus": "AF", "etat": "terminee",
    }
    c = depuis_ligne_enregistree(ligne)

    assert c["premiere_extremite"] == {"ip": "192.168.1.6", "port": 51000}
    assert c["seconde_extremite"] == {"ip": "93.184.216.34", "port": 443}
    assert c["debut_lisible"] == "2026-10-06 10:39:51"
    assert c["fin_lisible"] == "2026-10-06 10:39:53"

def test_un_champ_absent_de_la_base_reste_absent():
    from explication.adaptateur import depuis_ligne_enregistree
    c = depuis_ligne_enregistree({"ip_premiere": "192.168.1.6", "protocole": "TCP"})

    assert c["sens_a_vers_b"] is None
    assert c["sens_b_vers_a"] is None

def test_la_meme_explication_sert_aux_deux_vues():
    from explication import expliquer
    from explication.adaptateur import depuis_ligne_enregistree

    vivante = {
        "premiere_extremite": {"ip": "192.168.1.6", "port": 51000},
        "seconde_extremite": {"ip": "93.184.216.34", "port": 443},
        "protocole": "TCP", "port_service": 443, "nb_paquets": 42,
        "octets": 8192, "duree": 2.5, "drapeaux_vus": "AF", "etat": "terminee",
    }
    enregistree = depuis_ligne_enregistree({
        "ip_premiere": "192.168.1.6", "port_premiere": 51000,
        "ip_seconde": "93.184.216.34", "port_seconde": 443,
        "protocole": "TCP", "port_service": 443, "nb_paquets": 42,
        "octets": 8192, "duree": 2.5, "drapeaux_vus": "AF", "etat": "terminee",
    })

    assert expliquer(vivante)["resume"] == expliquer(enregistree)["resume"]

def test_la_somme_des_constats_est_complete():
    from explication.phrases import expliquer

    communication = {
        "premiere_extremite": {"ip": "192.168.1.6", "port": 51000},
        "seconde_extremite": {"ip": "93.184.216.34", "port": 443},
        "protocole": "TCP", "port_service": 443,
        "nb_paquets": 76, "octets": 64757, "duree": 1.1,
        "drapeaux_vus": "AFPR", "etat": "terminee",
    }
    e = expliquer(communication)
    comptes = e["comptes"]

    somme = comptes["observations"] + comptes["interpretations"] + comptes["hypotheses"]
    assert somme == len(e["constats"]), (
        f"les comptes annoncent {somme} constats, la table en contient {len(e['constats'])}")

def test_chaque_constat_est_compte_dans_une_categorie():
    from explication.phrases import expliquer, OBSERVATION, INTERPRETATION, HYPOTHESE

    communication = {
        "premiere_extremite": {"ip": "192.168.1.6", "port": 51000},
        "seconde_extremite": {"ip": "93.184.216.34", "port": 443},
        "protocole": "TCP", "port_service": 443,
        "nb_paquets": 76, "octets": 64757, "duree": 1.1,
        "drapeaux_vus": "AFPR", "etat": "terminee",
    }
    connus = {OBSERVATION, INTERPRETATION, HYPOTHESE}
    for constat in expliquer(communication)["constats"]:
        assert constat["niveau"] in connus, f"niveau inconnu : {constat['niveau']}"
