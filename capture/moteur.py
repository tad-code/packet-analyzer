

import threading
import time

from scapy.all import AsyncSniffer

class ErreurCapture(Exception):

    def __init__(self, message, detail=None):
        super().__init__(message)
        self.message = message
        self.detail = detail

class MoteurCapture:

    def __init__(self, taille_tampon=500):

        self._verrou = threading.Lock()
        self._paquets = []
        self._taille_tampon = taille_tampon

        self._sniffer = None
        self._interface = None
        self._en_cours = False
        self._erreur = None
        self._total_vu = 0

    def en_cours(self):

        with self._verrou:
            return self._en_cours

    def interface(self):

        with self._verrou:
            return self._interface

    def erreur(self):

        with self._verrou:
            return self._erreur

    def total_vu(self):

        with self._verrou:
            return self._total_vu

    def paquets(self):

        with self._verrou:
            return list(self._paquets)

    def demarrer(self, interface):

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

        with self._verrou:
            self._paquets.clear()
            self._total_vu = 0
            self._erreur = None

    def _recevoir(self, paquet):

        with self._verrou:
            self._total_vu += 1
            self._paquets.append(paquet)

            if len(self._paquets) > self._taille_tampon:
                del self._paquets[: len(self._paquets) - self._taille_tampon]
