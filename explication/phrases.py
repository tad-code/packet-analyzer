

from analyse.protocoles import fiche_port, nom_du_port
from analyse.protocoles import lire_drapeaux

OBSERVATION = "observation"
INTERPRETATION = "interpretation"
HYPOTHESE = "hypothese"

NIVEAUX = {
    OBSERVATION: {
        "libelle": "Fait observé",
        "aide": "Information lue directement dans les paquets. Aucune supposition.",
    },
    INTERPRETATION: {
        "libelle": "Interprétation",
        "aide": "Lecture de ce fait, fondée sur une connaissance générale des réseaux. "
                "C'est probable, pas certain.",
    },
    HYPOTHESE: {
        "libelle": "Hypothèse",
        "aide": "Possibilité suggérée par les données. Les informations disponibles ne "
                "permettent pas de conclure.",
    },
}

PORTS_CHIFFRES = {443, 8443, 993, 995, 465, 636}

def _regle_service_connu(communication):

    port = communication.get("port_service")
    nom = nom_du_port(port) if port is not None else None
    if port is None or not nom:
        return None

    _, commentaire = fiche_port(port)
    return {
        "niveau": INTERPRETATION,
        "base": f"le port du service observé est {port}",
        "texte": f"Le port {port} est généralement associé à {nom}."
                 + (f" {commentaire}" if commentaire else ""),
    }

def _regle_service_inconnu(communication):

    port = communication.get("port_service")
    if port is None:
        return None
    if nom_du_port(port):
        return None
    return {
        "niveau": HYPOTHESE,
        "base": f"le port du service observé est {port}, qui ne figure pas parmi les "
                f"services connus",
        "texte": "Le service contacté n'a pas pu être identifié : le numéro de port seul "
                 "ne permet pas de conclure. De nombreux logiciels écoutent sur des ports "
                 "non standard.",
    }

def _regle_contenu_chiffre(communication):

    port = communication.get("port_service")
    if port not in PORTS_CHIFFRES:
        return None
    return {
        "niveau": HYPOTHESE,
        "base": f"le port du service observé est {port}",
        "texte": "Le contenu de cette communication est probablement chiffré, et n'est "
                 "donc pas lisible. L'analyse porte sur les métadonnées — qui parle, "
                 "quand, combien — et non sur ce qui est dit.",
    }

def _regle_fermeture_et_refus(communication):

    noms = lire_drapeaux(communication.get("drapeaux_vus"))
    if "FIN" not in noms or "RST" not in noms:
        return None
    return {
        "niveau": INTERPRETATION,
        "base": "des drapeaux FIN et RST ont tous deux été observés dans les paquets",
        "texte": "La fermeture s'est faite des deux manières : une extrémité a terminé "
                 "proprement (FIN) pendant que l'autre a coupé brutalement (RST). C'est "
                 "fréquent en fin de capture, ou lorsqu'un service ferme sans attendre "
                 "l'accord de son correspondant.",
    }

def _regle_fermeture_propre(communication):

    noms = lire_drapeaux(communication.get("drapeaux_vus"))
    if "FIN" not in noms:
        return None
    if "RST" in noms:

        return None
    return {
        "niveau": INTERPRETATION,
        "base": "un drapeau FIN a été observé dans les paquets",
        "texte": "La connexion a été fermée proprement : les deux machines ont terminé "
                 "l'échange en se mettant d'accord. C'est le déroulement normal.",
    }

def _regle_connexion_refusee(communication):

    noms = lire_drapeaux(communication.get("drapeaux_vus"))
    if "RST" not in noms:
        return None
    if "FIN" in noms:
        return None
    return {
        "niveau": INTERPRETATION,
        "base": "un drapeau RST a été observé dans les paquets",
        "texte": "La connexion a été interrompue brutalement. Cela se produit lorsqu'un "
                 "service refuse une connexion — port fermé, par exemple — ou lorsque la "
                 "communication est coupée. Cela peut être parfaitement normal.",
    }

def _regle_ouverture_sans_reponse(communication):

    drapeaux = communication.get("drapeaux_vus") or ""
    if "S" not in drapeaux:
        return None
    if (communication.get("sens_b_vers_a") or 0) > 0:
        return None
    return {
        "niveau": HYPOTHESE,
        "base": f"{communication.get('nb_paquets')} paquet(s) observé(s) dans un seul sens, "
                f"dont un SYN, et aucun paquet en retour",
        "texte": "La tentative d'ouverture de connexion est restée sans réponse. Le service "
                 "est peut-être indisponible, ou la réponse est filtrée par un pare-feu. "
                 "Une seule observation ne permet pas de trancher.",
    }

def _regle_echange_unidirectionnel(communication):

    drapeaux = communication.get("drapeaux_vus") or ""
    if "S" in drapeaux:
        return None
    if (communication.get("sens_a_vers_b") or 0) == 0:
        return None
    if (communication.get("sens_b_vers_a") or 0) > 0:
        return None
    return {
        "niveau": HYPOTHESE,
        "base": "tous les paquets observés vont dans le même sens",
        "texte": "Aucune réponse n'a été observée. Pour un protocole sans connexion comme "
                 "UDP, c'est habituel : le service n'est pas tenu de répondre.",
    }

def _regle_debit(communication):

    duree = communication.get("duree")
    octets = communication.get("octets")
    if not duree or duree < 0.5 or not octets:
        return None
    debit = octets / duree
    if debit >= 1024:
        texte_debit = f"{debit / 1024:.0f} Ko/s"
    else:
        texte_debit = f"{debit:.0f} o/s"
    return {
        "niveau": OBSERVATION,
        "base": f"{octets} octets échangés en {duree:.1f} seconde(s)",
        "texte": f"Débit moyen calculé sur la durée observée : environ {texte_debit}.",
    }

def _regle_communication_longue(communication):

    duree = communication.get("duree")
    paquets = communication.get("nb_paquets")
    if not duree or duree < 30 or not paquets:
        return None
    if paquets / duree > 1:
        return None
    return {
        "niveau": INTERPRETATION,
        "base": f"{paquets} paquet(s) seulement en {duree:.0f} secondes",
        "texte": "La communication dure longtemps avec très peu de paquets : elle est "
                 "probablement maintenue ouverte et reste la plupart du temps silencieuse. "
                 "Une connexion établie qui n'échange rien peut aussi être le signe d'un "
                 "service qui ne répond plus.",
    }

def _regle_volume_important(communication):

    octets = communication.get("octets")
    duree = communication.get("duree")
    if not octets or octets < 100 * 1024:
        return None
    if duree and duree > 30:
        return None
    return {
        "niveau": OBSERVATION,
        "base": f"{octets} octets échangés en {duree:.1f} seconde(s) au plus",
        "texte": "Le volume échangé est important pour une durée aussi courte : il s'agit "
                 "d'un transfert de données, et non d'un simple échange de contrôle.",
    }

REGLES = [

    _regle_fermeture_et_refus,
    _regle_fermeture_propre,
    _regle_connexion_refusee,
    _regle_ouverture_sans_reponse,
    _regle_service_connu,
    _regle_contenu_chiffre,
    _regle_service_inconnu,
    _regle_echange_unidirectionnel,
    _regle_communication_longue,
    _regle_volume_important,
    _regle_debit,
]

def interpreter(communication):

    constats = []
    for regle in REGLES:
        try:
            constat = regle(communication)
        except Exception:

            continue
        if constat:
            constat["regle"] = regle.__name__.lstrip("_").replace("regle_", "")
            constats.append(constat)
    return constats

def resumer(communication):

    premiere = communication.get("premiere_extremite") or {}
    seconde = communication.get("seconde_extremite") or {}
    port = communication.get("port_service")
    nom_port = nom_du_port(port) if port is not None else None
    protocole = communication.get("protocole")

    if not premiere.get("ip") or not seconde.get("ip"):
        return ("Les adresses de cette communication n'ont pas pu être lues : aucune "
                "explication fiable ne peut être produite.")

    locale_a = _est_locale(premiere.get("ip"))
    locale_b = _est_locale(seconde.get("ip"))

    if locale_a and not locale_b:
        ouverture = (f"Une machine du réseau local ({premiere['ip']}) communique avec "
                     f"un serveur distant ({seconde['ip']})")
    elif not locale_a and locale_b:
        ouverture = (f"Un serveur distant ({premiere['ip']}) communique avec une machine "
                     f"du réseau local ({seconde['ip']})")
    elif locale_a and locale_b:
        ouverture = (f"Deux machines du réseau local échangent : {premiere['ip']} et "
                     f"{seconde['ip']}")
    else:
        ouverture = (f"Deux machines distantes échangent : {premiere['ip']} et "
                     f"{seconde['ip']}")

    suite = ""
    if protocole:
        suite = f" en utilisant le protocole {protocole}"
    if port is not None:
        if nom_port:
            suite += f", sur le port {port} — généralement associé à {nom_port}"
        else:
            suite += f", sur le port {port}"

    etat = communication.get("etat")

    fin = {
        "terminee": " La connexion s'est terminée normalement.",
        "refusee": " La connexion a été refusée ou interrompue.",
        "inactive": " Plus rien n'a été échangé depuis un moment.",
        "en cours": " Aucun drapeau de fermeture n'a été observé : on ne peut pas conclure qu'elle est terminée.",
        "ouverte": " Aucun drapeau de fermeture n'a été observé.",
    }.get(etat, "")

    volume = ""
    octets = communication.get("octets")
    if octets:
        if octets >= 1024:
            volume = f" {octets} octets ont été échangés, soit environ {octets / 1024:.1f} Ko."
        else:
            volume = f" {octets} octets ont été échangés."

    return f"{ouverture}{suite}.{fin}{volume}"

def _est_locale(adresse):

    if not adresse:
        return False
    adresse = str(adresse)

    if adresse.startswith("192.168."):
        return True
    if adresse.startswith("10."):
        return True
    if adresse.startswith("127."):
        return True
    if adresse.startswith("169.254."):
        return True
    if adresse.lower().startswith(("fe80:", "fc", "fd")):
        return True

    if adresse.startswith("172."):
        morceaux = adresse.split(".")
        if len(morceaux) > 1:
            try:
                return 16 <= int(morceaux[1]) <= 31
            except ValueError:
                return False

    return False

def expliquer(communication):

    from explication.faits import faits_observes, resume_chiffre

    constats = interpreter(communication)
    faits = faits_observes(communication)
    nb_observes = sum(1 for f in faits if f["disponible"])

    return {
        "resume": resumer(communication),
        "resume_chiffre": resume_chiffre(communication),
        "faits": faits,
        "constats": constats,
        "comptes": {
            "faits_observes": nb_observes,

            "observations": sum(1 for c in constats if c["niveau"] == OBSERVATION),
            "interpretations": sum(1 for c in constats if c["niveau"] == INTERPRETATION),
            "hypotheses": sum(1 for c in constats if c["niveau"] == HYPOTHESE),
        },
    }
