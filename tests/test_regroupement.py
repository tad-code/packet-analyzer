

from communications.regroupement import (
    cle_communication,
    port_du_service,
    regrouper,
    repondre_questions,
    statistiques,
)
from tests.conftest import paquet

def test_les_deux_sens_forment_une_seule_communication():

    aller = paquet("192.168.1.10", "93.184.216.34", 51000, 443)
    retour = paquet("93.184.216.34", "192.168.1.10", 443, 51000)

    assert cle_communication(aller) == cle_communication(retour)

def test_deux_destinations_differentes_forment_deux_communications():
    premier = paquet("192.168.1.10", "93.184.216.34", 51000, 443)
    second = paquet("192.168.1.10", "142.250.75.14", 51001, 443)

    assert cle_communication(premier) != cle_communication(second)

def test_port_connu_reconnu_meme_sil_est_le_plus_grand():

    assert port_du_service(443, 1024) == 443

def test_a_defaut_on_prend_le_plus_petit_port():

    assert port_du_service(60000, 12345) == 12345

def test_port_absent_ne_provoque_pas_d_erreur():
    assert port_du_service(None, 443) == 443
    assert port_du_service(None, None) is None

def test_comptage_des_paquets_et_des_octets():
    paquets = [
        paquet("192.168.1.10", "93.184.216.34", 51000, 443, taille=100, horodatage=1000.0),
        paquet("93.184.216.34", "192.168.1.10", 443, 51000, taille=200, horodatage=1000.5),
        paquet("192.168.1.10", "93.184.216.34", 51000, 443, taille=300, horodatage=1001.0),
    ]
    communications = regrouper(paquets)

    assert len(communications) == 1
    assert communications[0]["nb_paquets"] == 3
    assert communications[0]["octets"] == 600

def test_bornes_temporelles_et_duree():
    paquets = [
        paquet("192.168.1.10", "1.1.1.1", 51000, 53, protocole="UDP", horodatage=1010.0),
        paquet("1.1.1.1", "192.168.1.10", 53, 51000, protocole="UDP", horodatage=1000.0),
        paquet("192.168.1.10", "1.1.1.1", 51000, 53, protocole="UDP", horodatage=1005.0),
    ]
    communications = regrouper(paquets)

    assert communications[0]["debut"] == 1000.0
    assert communications[0]["fin"] == 1010.0
    assert communications[0]["duree"] == 10.0

def test_le_sens_de_circulation_est_compte():
    paquets = [
        paquet("192.168.1.10", "93.184.216.34", 51000, 443),
        paquet("192.168.1.10", "93.184.216.34", 51000, 443),
        paquet("93.184.216.34", "192.168.1.10", 443, 51000),
    ]
    communications = regrouper(paquets)

    assert communications[0]["sens_a_vers_b"] == 2
    assert communications[0]["sens_b_vers_a"] == 1

def test_plusieurs_communications_distinctes():
    paquets = [
        paquet("192.168.1.10", "93.184.216.34", 51000, 443),
        paquet("192.168.1.10", "142.250.75.14", 51001, 443),
        paquet("192.168.1.10", "1.1.1.1", 51002, 53, protocole="UDP"),
    ]
    communications = regrouper(paquets)

    assert len(communications) == 3

def test_syn_sans_fin_donne_une_communication_en_cours():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 443, drapeaux="S")]
    communications = regrouper(paquets, maintenant=1000.0)
    assert communications[0]["etat"] == "en cours"
    assert communications[0]["active"] is True

def test_fin_donne_une_communication_terminee():
    paquets = [
        paquet("192.168.1.10", "93.184.216.34", 51000, 443, drapeaux="S"),
        paquet("192.168.1.10", "93.184.216.34", 51000, 443, drapeaux="F"),
    ]
    communications = regrouper(paquets, maintenant=1000.0)
    assert communications[0]["etat"] == "terminee"

def test_rst_donne_une_communication_refusee():

    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 81, drapeaux="R")]
    communications = regrouper(paquets, maintenant=1000.0)
    assert communications[0]["etat"] == "refusee"

def test_silence_prolonge_donne_une_communication_inactive():

    paquets = [paquet("192.168.1.10", "1.1.1.1", 51000, 53, protocole="UDP", horodatage=1000.0)]

    recente = regrouper(paquets, maintenant=1030.0, delai_inactivite=60.0)
    assert recente[0]["active"] is True

    ancienne = regrouper(paquets, maintenant=1200.0, delai_inactivite=60.0)
    assert ancienne[0]["active"] is False
    assert ancienne[0]["etat"] == "inactive"

def test_liste_vide_ne_provoque_pas_d_erreur():
    assert regrouper([]) == []

def test_paquet_incomplet_est_ignore_sans_casser_le_regroupement():

    incomplet = paquet(None, None, None, None)
    valide = paquet("192.168.1.10", "93.184.216.34", 51000, 443)

    communications = regrouper([incomplet, valide])

    assert len(communications) == 2

def test_les_sept_questions_ont_une_reponse():
    paquets = [
        paquet("192.168.1.10", "93.184.216.34", 51000, 443, taille=500, horodatage=1000.0),
        paquet("93.184.216.34", "192.168.1.10", 443, 51000, taille=1500, horodatage=1002.0),
    ]
    communication = regrouper(paquets, maintenant=1002.0)[0]
    questions = repondre_questions(communication)

    assert len(questions) == 7
    for intitule, reponse in questions:
        assert intitule
        assert reponse and reponse != "None"

    reponses = dict(questions)
    assert "192.168.1.10:51000" in reponses["Qui communique avec qui ?"]
    assert reponses["Sur quel protocole ?"] == "TCP"
    assert reponses["Combien de paquets échangés ?"] == "2"
    assert "HTTPS" in reponses["Sur quel port ?"]

def test_le_volume_est_affiche_dans_une_unite_lisible():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 443, taille=2048)]
    communication = regrouper(paquets, maintenant=1000.0)[0]
    reponses = dict(repondre_questions(communication))
    assert "Ko" in reponses["Combien de données ont circulé ?"]

def test_statistiques_comptent_les_communications_et_les_protocoles():
    paquets = [
        paquet("192.168.1.10", "93.184.216.34", 51000, 443, taille=100),
        paquet("192.168.1.10", "142.250.75.14", 51001, 443, taille=200),
        paquet("192.168.1.10", "1.1.1.1", 51002, 53, protocole="UDP", taille=50),
    ]
    stats = statistiques(regrouper(paquets, maintenant=1000.0))

    assert stats["nb_communications"] == 3
    assert stats["nb_paquets"] == 3
    assert stats["octets"] == 350
    protocoles = dict(stats["protocoles"])
    assert protocoles["TCP"] == 2
    assert protocoles["UDP"] == 1
    assert ("HTTPS", 2) in stats["services"]

def test_statistiques_sur_liste_vide():
    stats = statistiques([])
    assert stats["nb_communications"] == 0
    assert stats["nb_paquets"] == 0
    assert stats["protocoles"] == []

def test_une_communication_fermee_n_est_pas_active():

    paquets = [
        paquet("192.168.1.10", "93.184.216.34", 51000, 443, drapeaux="S", horodatage=1000.0),
        paquet("192.168.1.10", "93.184.216.34", 51000, 443, drapeaux="F", horodatage=1000.5),
    ]
    communication = regrouper(paquets, maintenant=1000.5)[0]

    assert communication["etat"] == "terminee"
    assert communication["active"] is False

def test_une_communication_refusee_n_est_pas_active():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 81, drapeaux="R", horodatage=1000.0)]
    communication = regrouper(paquets, maintenant=1000.0)[0]

    assert communication["etat"] == "refusee"
    assert communication["active"] is False

def test_une_communication_ouverte_reste_active():
    paquets = [paquet("192.168.1.10", "93.184.216.34", 51000, 443, drapeaux="S", horodatage=1000.0)]
    communication = regrouper(paquets, maintenant=1000.0)[0]

    assert communication["active"] is True

def test_les_destinations_excluent_la_machine_qui_a_pris_l_initiative():

    paquets = [
        paquet("192.168.1.10", "93.184.216.34", 51000, 443, taille=100),
        paquet("192.168.1.10", "142.250.75.14", 51001, 443, taille=100),
    ]
    stats = statistiques(regrouper(paquets, maintenant=1000.0))

    sources = dict(stats["principales_sources"])
    destinations = dict(stats["principales_destinations"])

    assert "192.168.1.10" in sources
    assert "192.168.1.10" not in destinations
    assert "93.184.216.34" in destinations

def test_un_service_connu_est_nomme_sur_le_tableau_de_bord():

    paquets = [paquet("192.168.1.10", "192.168.1.1", 55000, 8080, taille=100)]
    stats = statistiques(regrouper(paquets, maintenant=1000.0))

    ports = dict(stats["ports_frequents"])
    assert 8080 in ports
    assert stats["services"] == [("HTTP alternatif", 1)]
