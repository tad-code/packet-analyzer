"""
Moteur de capture.

Ce module est le seul du projet a parler directement au pilote reseau. Il fait
trois choses :

    1. demarrer l'ecoute sur une interface choisie ;
    2. conserver les paquets lus dans un tampon limite en memoire ;
    3. arreter proprement l'ecoute, et signaler ce qui s'est mal passe.

Pourquoi l'ecoute tourne dans un fil d'execution separe : l'application web doit
rester capable de repondre aux clics de l'utilisateur pendant la capture. Si
l'ecoute occupait le fil principal, la page ne se rafraichirait plus.

Pourquoi le tampon est limite : une capture d'une heure produit des centaines de
milliers de paquets. Les garder tous epuiserait la memoire. On conserve donc les
derniers, et on le dira clairement dans l'interface.
"""

import threading
import time

from scapy.all import AsyncSniffer


class ErreurCapture(Exception):
    """Erreur de capture portant un message comprehensible par l'utilisateur."""

    def __init__(self, message, detail=None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class MoteurCapture:
    """Ecoute une interface reseau et conserve les paquets lus."""

    def __init__(self, taille_tampon=500):
        # Le verrou protege le tampon : un fil y ecrit, les autres le lisent.
        self._verrou = threading.Lock()
        self._paquets = []
        self._taille_tampon = taille_tampon

        self._sniffer = None
        self._interface = None
        self._en_cours = False
        self._erreur = None
        self._total_vu = 0

    # --- Etat ---------------------------------------------------------------

    def en_cours(self):
        """La capture est-elle active ?"""
        with self._verrou:
            return self._en_cours

    def interface(self):
        """Nom de l'interface actuellement ecoutee."""
        with self._verrou:
            return self._interface

    def erreur(self):
        """Derniere erreur rencontree, ou None."""
        with self._verrou:
            return self._erreur

    def total_vu(self):
        """Nombre total de paquets vus depuis le demarrage de la capture."""
        with self._verrou:
            return self._total_vu

    def paquets(self):
        """
        Copie de la liste des paquets conserves.

        On rend une copie et non la liste elle-meme : sans cela, l'affichage
        travaillerait sur une structure que le fil de capture est en train de
        modifier, ce qui produit des erreurs difficiles a reproduire.
        """
        with self._verrou:
            return list(self._paquets)

    # --- Commandes ----------------------------------------------------------

    def demarrer(self, interface):
        """
        Lance l'ecoute sur une interface.

        Leve ErreurCapture avec un message clair si l'ecoute ne peut pas
        s'ouvrir : interface inexistante, droits insuffisants, pilote absent.
        """
        with self._verrou:
            if self._en_cours:
                raise ErreurCapture(
                    "Une capture est deja en cours.",
                    "Arretez la capture actuelle avant d'en demarrer une nouvelle.",
                )

        if not interface:
            raise ErreurCapture(
                "Aucune interface reseau n'a ete fournie.",
                "Choisissez une interface dans la liste avant de demarrer.",
            )

        try:
            sniffer = AsyncSniffer(iface=interface, prn=self._recevoir, store=False)
            sniffer.start()

            # Point important, et verifie par l'experience :
            #
            #   - AsyncSniffer ouvre l'interface dans un fil d'execution separe,
            #     et sa methode start() rend la main immediatement ;
            #   - si l'interface n'existe pas, start() NE LEVE PAS d'erreur ;
            #   - l'attribut `running` vaut True malgre l'echec : il ne faut donc
            #     surtout pas s'y fier ;
            #   - le vrai signal est l'attribut `exception`, qui contient le
            #     message d'erreur, et le fil d'ecoute, qui n'est plus vivant.
            #
            # Sans ce controle, l'application annoncerait « capture demarree »
            # alors que rien n'ecoute — le pire des mensonges pour un outil
            # d'analyse.
            time.sleep(0.6)
            probleme = getattr(sniffer, "exception", None)
            fil = getattr(sniffer, "thread", None)
            fil_mort = fil is not None and not fil.is_alive()

            if probleme is not None or fil_mort:
                try:
                    sniffer.stop()
                except Exception:
                    pass
                raise ErreurCapture(
                    f"Impossible d'ouvrir l'interface « {interface} ».",
                    "Vérifiez que cette carte réseau existe et qu'elle est active. "
                    f"Détail technique : {probleme}" if probleme else
                    "Vérifiez que cette carte réseau existe et qu'elle est active.",
                )
        except ErreurCapture:
            # Deja formee plus haut : on la laisse remonter telle quelle.
            raise
        except PermissionError:
            raise ErreurCapture(
                "La capture a ete refusee par le systeme.",
                "La capture de paquets exige les droits administrateur et le pilote Npcap.",
            )
        except OSError as e:
            raise ErreurCapture(
                f"Impossible d'ouvrir l'interface « {interface} ».",
                f"Verifiez que cette interface existe et qu'elle est active. Detail : {e}",
            )
        except Exception as e:
            raise ErreurCapture(
                "La capture n'a pas pu demarrer.",
                f"Detail technique : {type(e).__name__} — {e}",
            )

        with self._verrou:
            self._sniffer = sniffer
            self._interface = interface
            self._en_cours = True
            self._erreur = None

    def arreter(self):
        """Arrete l'ecoute. Sans effet si aucune capture n'est en cours."""
        with self._verrou:
            sniffer = self._sniffer
            self._sniffer = None
            self._en_cours = False

        if sniffer is not None:
            try:
                sniffer.stop()
            except Exception as e:
                with self._verrou:
                    self._erreur = f"L'arret de la capture a signale : {e}"

    def vider(self):
        """Vide le tampon. Utile avant une nouvelle analyse."""
        with self._verrou:
            self._paquets.clear()
            self._total_vu = 0
            self._erreur = None

    # --- Reception ----------------------------------------------------------

    def _recevoir(self, paquet):
        """
        Appelee par Scapy pour chaque paquet lu.

        Le paquet est simplement mis de cote : sa lecture detaillee est faite
        plus tard, par le module d'analyse. On separe ainsi la capture de
        l'interpretation, ce qui permet de tester l'analyse sans reseau.
        """
        with self._verrou:
            self._total_vu += 1
            self._paquets.append(paquet)
            # Au-dela de la limite, on oublie les plus anciens.
            if len(self._paquets) > self._taille_tampon:
                del self._paquets[: len(self._paquets) - self._taille_tampon]
