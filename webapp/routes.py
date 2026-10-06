"""
Routes de l'application.

Une route est une adresse que le navigateur peut demander. Chaque route fait
trois choses, et rien de plus :

    1. elle lit ce que l'utilisateur demande ;
    2. elle appelle le module competent ;
    3. elle rend une page.

Toute la logique vit dans les autres modules. C'est ce qui rend ce fichier
lisible : on y voit le plan de l'application, pas les details.

Organisation des pages :

    /                    tableau de bord : la vue generale
    /capture             demarrer et arreter une capture
    /communications      la liste des conversations observees
    /communication/<cle> le detail d'une conversation, avec son explication
    /protocoles          ce que le programme sait des protocoles
    /glossaire           le vocabulaire employe, defini simplement
    /historique          les captures enregistrees
    /health              etat du service, en JSON
"""

from flask import Blueprint, jsonify, redirect, request, url_for

from analyse.paquet import PORTS_CONNUS, analyser
from analyse.protocoles import DRAPEAUX, PORTS, PROTOCOLES, expliquer_drapeaux
from capture.interfaces import lister_interfaces, proposer_interface
from capture.moteur import ErreurCapture, MoteurCapture
from communications.regroupement import regrouper, repondre_questions, statistiques
from config import config
from explication import expliquer
from explication.adaptateur import depuis_ligne_enregistree
from explication.faits import adresse_complete
from explication.glossaire import GLOSSAIRE
from stockage import supabase
from stockage.supabase import ErreurBase
from webapp.rendu import rendre

routes = Blueprint("routes", __name__)

# Objet unique pour toute la duree de vie du programme.
moteur = MoteurCapture(taille_tampon=config.taille_tampon)

MESSAGES = {
    "demarree": "La capture a démarré.",
    "arretee": "La capture a été arrêtée.",
    "videe": "La liste a été vidée.",
}


def _paquets_analyses():
    """
    Traduit les paquets bruts conserves en paquets analyses.

    Un paquet illisible est ignore plutot que de faire echouer l'affichage : une
    seule donnee abimee ne doit pas rendre toute la page inutilisable.
    """
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
    """
    Rassemble tout ce dont la page de capture a besoin.

    Cette fonction existe parce qu'une regression a eu lieu : en ajoutant les
    pages de communications, la route de capture avait ete reecrite sans les
    paquets, et la liste s'affichait vide. Une seule source pour ce contexte
    evite que les deux appels (affichage normal et signalement d'erreur)
    divergent a nouveau.
    """
    interfaces = lister_interfaces() if config.capture_locale else []

    paquets = []
    if config.capture_locale:
        for rang, brut in enumerate(moteur.paquets(), start=1):
            try:
                paquets.append(analyser(brut, rang))
            except Exception:
                continue
        paquets.reverse()          # le plus recent en premier

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


def _communications():
    """
    Regroupe les paquets conserves en communications.

    Le regroupement est refait a chaque affichage, a partir du tampon. C'est
    volontaire : la fonction est pure et rapide, et il n'y a ainsi aucun etat
    intermediaire a maintenir ni a synchroniser. Avec un tampon de quelques
    centaines de paquets, le cout est negligeable.
    """
    return regrouper(_paquets_analyses())


# ---------------------------------------------------------------------------
# Le tableau de bord
# ---------------------------------------------------------------------------

@routes.route("/")
def accueil():
    """Vue generale : les chiffres essentiels et les dernieres communications."""
    communications = _communications()
    return rendre("tableau_bord.html", "tableau",
                  stats=statistiques(communications),
                  services_connus=PORTS_CONNUS,
                  communications=communications[:8],
                  capture_en_cours=moteur.en_cours(),
                  total_vu=moteur.total_vu(),
                  interface_active=moteur.interface())


# ---------------------------------------------------------------------------
# Les communications
# ---------------------------------------------------------------------------

@routes.route("/communications")
def communications():
    """Liste des conversations observees."""
    toutes = _communications()
    return rendre("communications.html", "communications",
                  communications=toutes,
                  capture_en_cours=moteur.en_cours())


@routes.route("/communication/<path:cle>")
def communication_detail(cle):
    """
    Detail d'une communication : informations techniques et reponses.

    L'identifiant contient des caracteres particuliers (barres verticales,
    deux-points) : le gabarit l'encode et Flask le decode. On ne stocke rien,
    on retrouve la communication en la recalculant.
    """
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


# ---------------------------------------------------------------------------
# La capture
# ---------------------------------------------------------------------------

@routes.route("/capture")
def capture():
    """Page de capture : choisir une carte reseau, demarrer, arreter."""
    return rendre("capture.html", "capture",
                  message=MESSAGES.get(request.args.get("fait")),
                  **_contexte_capture())


@routes.route("/capture/demarrer", methods=["POST"])
def demarrer():
    """Demarre la capture sur l'interface choisie."""
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
    """Arrete la capture en cours."""
    moteur.arreter()
    return redirect(url_for("routes.capture", fait="arretee"))


@routes.route("/capture/vider", methods=["POST"])
def vider():
    """Vide la liste des paquets conserves."""
    moteur.vider()
    return redirect(url_for("routes.capture", fait="videe"))


# ---------------------------------------------------------------------------
# L'historique
# ---------------------------------------------------------------------------

@routes.route("/historique")
def historique():
    """
    Liste des captures enregistrees dans la base.

    Cette page ne doit jamais faire tomber l'application : si la base est
    injoignable, ou si les tables n'existent pas encore, on affiche une
    explication et une marche a suivre. C'est l'un des cas d'erreur exiges par
    le cahier des charges.
    """
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
        # Pour chaque analyse, on compte ses communications : le chiffre est
        # deja enregistre, on evite une requete supplementaire.
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
    """Detail d'une capture enregistree : ses communications."""
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

    # Les communications viennent de la base : on les remet sous la forme que le
    # moteur attend, afin qu'une seule et meme explication serve aux deux vues.
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
    """
    Enregistre la capture en cours dans la base.

    En cas d'echec, les paquets restent en memoire et l'utilisateur peut
    reessayer : c'est le point important — une erreur d'enregistrement ne doit
    pas faire disparaitre le travail d'analyse.
    """
    disponible, raison = supabase.disponible()
    communications = _communications()
    paquets = _paquets_analyses()

    if not disponible:
        return rendre("capture.html", "capture",
                      message=None, erreur="Enregistrement impossible.",
                      erreur_detail=raison,
                      **_contexte_capture())

    # On enregistre l'explication produite AU MOMENT de la capture. Sans cela,
    # l'historique changerait d'aspect a chaque evolution des regles, et l'on ne
    # pourrait plus comparer une analyse ancienne avec une nouvelle.
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

    return redirect(url_for("routes.historique_detail", analyse_id=identifiant))


@routes.route("/historique/<int:analyse_id>/communication/<int:communication_id>")
def historique_communication(analyse_id, communication_id):
    """
    Detail d'une communication enregistree, avec la meme explication qu'en direct.

    Le resume affiche est celui CONSERVE au moment de la capture, et non celui que
    les regles produiraient aujourd'hui : l'historique doit montrer ce qui a ete
    constate ce jour-la. Le detail, lui, est recalcule depuis les champs conserves,
    qui n'ont pas bouge.
    """
    disponible, raison = supabase.disponible()
    if not disponible:
        return rendre("historique.html", "historique",
                      disponible=False, raison=raison, analyses=[],
                      erreur=None, erreur_detail=None,
                      capture_en_cours=moteur.en_cours())

    try:
        lignes = supabase.lire("reseau_communications",
                               # PostgREST separe les conditions par « & » : ecrit
                               # avec « and », tout part dans la meme valeur et la
                               # base repond « invalid input syntax for type bigint ».
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


@routes.route("/protocoles")
def protocoles():
    """
    Ce que le programme sait des protocoles et des ports.

    Cette page existe pour une raison precise : rien dans l'application ne doit
    reposer sur une connaissance cachee. Ce que le programme affirme sur un port,
    l'utilisateur peut le lire ici — et le contester.
    """
    return rendre("protocoles.html", "protocoles",
                  protocoles=list(PROTOCOLES.values()),
                  ports=list(PORTS.items()))


@routes.route("/glossaire")
def glossaire():
    """Le vocabulaire employe, defini en francais simple."""
    return rendre("glossaire.html", "glossaire",
                  entrees=GLOSSAIRE,
                  capture_en_cours=moteur.en_cours())


@routes.route("/health")
def health():
    """Etat du service, en JSON."""
    return jsonify({
        "etat": "ok",
        "version": "3.0",
        **config.resume(),
        "capture_en_cours": moteur.en_cours(),
        "interface": moteur.interface(),
        "paquets_vus": moteur.total_vu(),
        "base_configuree": config.base_configuree(),
    })
