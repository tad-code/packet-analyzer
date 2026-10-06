

from flask import Blueprint, jsonify, redirect, request, url_for

from analyse.paquet import PORTS_CONNUS, analyser
from analyse.protocoles import DRAPEAUX, PORTS, PROTOCOLES, expliquer_drapeaux
from capture.interfaces import lister_interfaces, proposer_interface
from capture.moteur import ErreurCapture, MoteurCapture
from communications.regroupement import regrouper, repondre_questions, statistiques
from config import config
from detection import analyser as analyser_alertes
from enrichissement import adresses as enrichissement
from explication import expliquer
from explication.adaptateur import depuis_ligne_enregistree
from analyse.adresses import adresses_de
from explication.faits import adresse_complete
from explication.glossaire import GLOSSAIRE
from stockage import supabase
from stockage.supabase import ErreurBase
from webapp.rendu import rendre

routes = Blueprint("routes", __name__)

moteur = MoteurCapture(taille_tampon=config.taille_tampon)

MESSAGES = {
    "demarree": "La capture a démarré.",
    "arretee": "La capture a été arrêtée.",
    "videe": "La liste a été vidée.",
}

def _paquets_analyses():

    if not config.capture_locale:
        return []

    paquets = []
    for rang, brut in enumerate(moteur.paquets(), start=1):
        try:
            paquets.append(analyser(brut, rang))
        except Exception:
            continue
    return paquets

def _contexte_capture(interface_proposee=None):

    interfaces = lister_interfaces() if config.capture_locale else []

    paquets = []
    if config.capture_locale:
        for rang, brut in enumerate(moteur.paquets(), start=1):
            try:
                paquets.append(analyser(brut, rang))
            except Exception:
                continue
        paquets.reverse()

    return {
        "interfaces": interfaces,
        "interface_active": moteur.interface(),
        "interface_proposee": interface_proposee or proposer_interface(
            interfaces, config.interface_defaut
        ),
        "capture_en_cours": moteur.en_cours(),
        "total_vu": moteur.total_vu(),
        "taille_tampon": config.taille_tampon,
        "nb_conserves": len(paquets),
        "paquets": paquets,
        "erreur_capture": moteur.erreur(),
    }

def _derniere_capture():

    if not supabase.disponible()[0]:
        return None
    try:
        lignes = supabase.lire("reseau_analyses", ordre="id.desc", limite=1)
    except ErreurBase:
        return None
    return lignes[0] if lignes else None

def _communications():

    if config.capture_locale:
        return regrouper(_paquets_analyses())

    analyse = _derniere_capture()
    if not analyse:
        return []
    try:
        lignes = supabase.lire("reseau_communications",
                               f"analyse_id=eq.{analyse['id']}", limite=500)
    except ErreurBase:
        return []

    return [depuis_ligne_enregistree(l) for l in lignes]

@routes.route("/")
def accueil():

    communications = _communications()
    return rendre("tableau_bord.html", "tableau",
                  stats=statistiques(communications),
                  services_connus=PORTS_CONNUS,
                  communications=communications[:8],
                  capture_en_cours=moteur.en_cours(),
                  total_vu=moteur.total_vu(),
                  interface_active=moteur.interface())

@routes.route("/communications")
def communications():

    toutes = _communications()
    return rendre("communications.html", "communications",
                  communications=toutes,
                  capture_en_cours=moteur.en_cours())

@routes.route("/communication/<path:cle>")
def communication_detail(cle):

    for communication in _communications():
        if communication["cle"] == cle:
            return rendre("communication.html", "communications",
                          communication=communication,
                          explication=expliquer(communication),
                          cle=communication.get("cle"),
                          drapeaux_vus=communication.get("drapeaux_vus"),
                          drapeaux=expliquer_drapeaux(communication.get("drapeaux_vus")),
                          drapeaux_connus=DRAPEAUX,
                          questions=repondre_questions(communication),
                          capture_en_cours=moteur.en_cours())

    return rendre("erreur.html", "communications", code=404,
                  titre="Communication introuvable",
                  explication="Cette communication n'existe plus dans les paquets conservés.",
                  detail="Le tampon est limité aux derniers paquets : une communication "
                         "ancienne peut avoir été oubliée."), 404

@routes.route("/capture")
def capture():

    return rendre("capture.html", "capture",
                  message=MESSAGES.get(request.args.get("fait")),
                  **_contexte_capture())

@routes.route("/capture/demarrer", methods=["POST"])
def demarrer():

    if not config.capture_locale:
        return redirect(url_for("routes.capture"))

    interface = (request.form.get("interface") or "").strip()

    try:
        moteur.demarrer(interface)
    except ErreurCapture as e:
        return rendre("capture.html", "capture",
                      erreur=e.message, erreur_detail=e.detail,
                      **_contexte_capture(interface_proposee=interface))

    return redirect(url_for("routes.capture", fait="demarree"))

@routes.route("/capture/arreter", methods=["POST"])
def arreter():

    moteur.arreter()
    return redirect(url_for("routes.capture", fait="arretee"))

@routes.route("/capture/vider", methods=["POST"])
def vider():

    moteur.vider()
    return redirect(url_for("routes.capture", fait="videe"))

@routes.route("/historique")
def historique():

    disponible, raison = supabase.disponible()

    if not disponible:
        return rendre("historique.html", "historique",
                      disponible=False,
                      raison=raison,
                      analyses=[],
                      erreur=None,
                      erreur_detail=None,
                      capture_en_cours=moteur.en_cours())

    analyses, erreur, detail = [], None, None
    try:
        analyses = supabase.lire("reseau_analyses", ordre="debut.desc", limite=50)

    except ErreurBase as e:
        erreur, detail = e.message, e.detail

    return rendre("historique.html", "historique",
                  disponible=True,
                  raison=None,
                  analyses=analyses,
                  erreur=erreur,
                  erreur_detail=detail,
                  capture_en_cours=moteur.en_cours())

@routes.route("/historique/<int:analyse_id>")
def historique_detail(analyse_id):

    disponible, raison = supabase.disponible()
    if not disponible:
        return rendre("historique.html", "historique",
                      disponible=False, raison=raison, analyses=[],
                      erreur=None, erreur_detail=None,
                      capture_en_cours=moteur.en_cours())

    try:
        analyses = supabase.lire("reseau_analyses", filtre=f"id=eq.{analyse_id}", limite=1)
        communications = supabase.lire(
            "reseau_communications",
            filtre=f"analyse_id=eq.{analyse_id}",
            ordre="nb_paquets.desc",
            limite=500,
        )
    except ErreurBase as e:
        return rendre("historique.html", "historique",
                      disponible=True, raison=None, analyses=[],
                      erreur=e.message, erreur_detail=e.detail,
                      capture_en_cours=moteur.en_cours())

    if not analyses:
        return rendre("erreur.html", "historique", code=404,
                      titre="Capture introuvable",
                      explication=f"Aucune capture enregistrée ne porte le numéro {analyse_id}.",
                      detail="Consultez la liste de l'historique."), 404

    expliquees = [
        {"ligne": c, "explication": expliquer(depuis_ligne_enregistree(c))}
        for c in communications
    ]

    return rendre("historique_detail.html", "historique",
                  analyse=analyses[0],
                  communications=expliquees,
                  capture_en_cours=moteur.en_cours())

@routes.route("/capture/enregistrer", methods=["POST"])
def enregistrer():

    disponible, raison = supabase.disponible()
    communications = _communications()
    paquets = _paquets_analyses()

    if not disponible:
        return rendre("capture.html", "capture",
                      message=None, erreur="Enregistrement impossible.",
                      erreur_detail=raison,
                      **_contexte_capture())

    resume_par_communication = {
        c.get("cle"): expliquer(c)["resume"] for c in communications if c.get("cle")
    }

    try:
        identifiant, nombre = supabase.enregistrer_analyse(
            interface=moteur.interface() or "inconnue",
            paquets=len(paquets),
            communications=communications,
            resume_par_communication=resume_par_communication,
        )
    except ErreurBase as e:
        return rendre("capture.html", "capture",
                      message=None,
                      erreur=f"Analyse effectuée, mais non enregistrée. {e.message}",
                      erreur_detail=e.detail,
                      **_contexte_capture())

    try:
        contexte = statistiques(communications)
        supabase.enregistrer_alertes(identifiant,
                                     analyser_alertes(communications, contexte))
    except Exception as e:
        print(f"  (alertes non enregistrees : {type(e).__name__} — {str(e)[:90]})")

    return redirect(url_for("routes.historique_detail", analyse_id=identifiant))

@routes.route("/historique/<int:analyse_id>/communication/<int:communication_id>")
def historique_communication(analyse_id, communication_id):

    disponible, raison = supabase.disponible()
    if not disponible:
        return rendre("historique.html", "historique",
                      disponible=False, raison=raison, analyses=[],
                      erreur=None, erreur_detail=None,
                      capture_en_cours=moteur.en_cours())

    try:
        lignes = supabase.lire("reseau_communications",

                               filtre=f"id=eq.{communication_id}&analyse_id=eq.{analyse_id}",
                               limite=1)
        analyses = supabase.lire("reseau_analyses", filtre=f"id=eq.{analyse_id}", limite=1)
    except ErreurBase as e:
        return rendre("historique.html", "historique",
                      disponible=True, raison=None, analyses=[],
                      erreur=e.message, erreur_detail=e.detail,
                      capture_en_cours=moteur.en_cours())

    if not lignes or not analyses:
        return rendre("erreur.html", "historique", code=404,
                      titre="Communication introuvable",
                      explication="Cette communication n'existe pas dans la capture demandée.",
                      detail="Revenez à la liste des captures enregistrées."), 404

    ligne = lignes[0]
    return rendre("historique_communication.html", "historique",
                  analyse=analyses[0],
                  ligne=ligne,
                  cle=ligne.get("cle"),
                  drapeaux_vus=ligne.get("drapeaux_vus"),
                  drapeaux=expliquer_drapeaux(ligne.get("drapeaux_vus")),
                  drapeaux_connus=DRAPEAUX,
                  explication=expliquer(depuis_ligne_enregistree(lignes[0])),
                  resume_enregistre=lignes[0].get("resume"),
                  capture_en_cours=moteur.en_cours())

@routes.route("/alertes")
def alertes():

    communications = _communications()
    contexte = statistiques(communications)
    trouvees = analyser_alertes(communications, contexte)

    adresses = []
    for alerte in trouvees:
        for c in alerte["communications"]:
            for ip in adresses_de(c):
                if ip not in adresses and enrichissement.est_publique(ip):
                    adresses.append(ip)
    adresses = adresses[:20]

    infos = {}
    if adresses:
        try:
            infos = enrichissement.enrichir(adresses)
        except Exception as e:
            print(f"  (enrichissement indisponible : {type(e).__name__})")

    return rendre("alertes.html", "alertes",
                  alertes=trouvees,
                  infos=infos,
                  resume_enrichissement=enrichissement.resume,
                  adresse_complete=adresse_complete,
                  capture_en_cours=moteur.en_cours(),
                  nb_communications=len(communications))

@routes.route("/protocoles")
def protocoles():

    return rendre("protocoles.html", "protocoles",
                  protocoles=list(PROTOCOLES.values()),
                  ports=list(PORTS.items()))

@routes.route("/glossaire")
def glossaire():

    return rendre("glossaire.html", "glossaire",
                  entrees=GLOSSAIRE,
                  capture_en_cours=moteur.en_cours())

@routes.route("/health")
def health():

    return jsonify({
        "etat": "ok",
        "version": "4.0",
        **config.resume(),
        "capture_en_cours": moteur.en_cours(),
        "interface": moteur.interface(),
        "paquets_vus": moteur.total_vu(),
        "base_configuree": config.base_configuree(),
    })
