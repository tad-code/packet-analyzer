# PHASE 0 — CONCEPTION
## Analyseur intelligent de paquets réseau

**Document de conception — à valider avant toute ligne de code**

---

## 0. Vérifications préalables (faites, pas supposées)

Avant de proposer une architecture, j'ai vérifié les points qui pouvaient la rendre impossible.

| Élément | État | Conséquence |
|---|---|---|
| **Pilote de capture Npcap** | **installé** (`C:\Windows\System32\Npcap\wpcap.dll`) | la capture de paquets réels est possible |
| **Scapy 2.8.0** | installé et testé | lecture du trafic confirmée |
| **Droits administrateur** | oui | la capture peut s'ouvrir |
| **Python** | 3.13.15 + pip | base de travail |
| **`gh` (GitHub CLI)** | connecté en tant que `tad-code` | le dépôt pourra être créé |
| **Wireshark / tshark** | absent | sans conséquence : Scapy suffit |

**Le test de capture réel a produit 158 paquets**, dont 83 TCP et 7 UDP, avec extraction réussie de tous les champs utiles : adresses source et destination, protocole, ports, taille, horodatage, drapeaux TCP, numéro de séquence.

Autrement dit : **le socle technique du projet est validé avant d'écrire quoi que ce soit.**

---

## 1. Fonctionnalités obligatoires

Ce sont les exigences du cahier des charges. Chacune est rattachée à un **artefact visible** — un élément que tu pourras montrer à la démonstration.

| # | Exigence | Artefact visible |
|---|---|---|
| 1 | Démarrer une capture | bouton **Démarrer** sur la page Capture |
| 2 | Arrêter une capture | bouton **Arrêter**, avec compteur en direct |
| 3 | Choisir l'interface | liste déroulante des interfaces détectées |
| 4 | Afficher les paquets capturés | page **Communications** + détail d'une communication |
| 5 | Extraire les informations d'un paquet | adresses, protocole, ports, taille, horodatage affichés sur la vue détaillée |
| 6 | Tolérer les informations manquantes | mention « information non disponible » au lieu d'une case vide |
| 7 | **Regrouper les paquets en communications** | une ligne par communication, avec nombre de paquets et volume |
| 8 | Répondre aux 7 questions sur une communication | bloc « Qui communique avec qui ? » — durée, protocole, port, paquets, octets, état |
| 9 | **Expliquer en langage humain** | bloc « Explication » sur chaque communication |
| 10 | Séparer FAIT OBSERVÉ / INTERPRÉTATION | deux blocs visuellement distincts, jamais mélangés |
| 11 | Reconnaître et expliquer les protocoles | page **Protocoles** : rôle, ce qu'on observe, ce que ça signifie |
| 12 | Identifier les étapes d'une connexion | état de la communication : ouverture / en cours / fermeture / échec |
| 13 | Détecter les comportements inhabitues | page **Alertes**, avec les règles nommées |
| 14 | Distinguer OBSERVATION / HYPOTHÈSE / ALERTE | étiquette de niveau sur chaque événement |
| 15 | **Au moins une API externe** | page **Enrichissement**, avec la réponse JSON brute affichée |
| 16 | Stocker dans **Supabase** | page **Historique**, plus la capture d'écran de la table dans Supabase |
| 17 | Interface web claire | 7 pages, chacune remplissant le premier écran |
| 18 | Tableau de bord | statistiques : paquets, communications, protocoles, sources, destinations, ports, volume, événements |
| 19 | Déployée en ligne | URL publique |
| 20 | Dépôt GitHub documenté | README professionnel |
| 21 | Gestion des erreurs (8 cas) | tableau des cas dans le README, avec le résultat obtenu |
| 22 | Tests réels | dossier `tests/` + section « Scénarios de test » du README |
| 23 | Sécurité : aucune clé dans GitHub | `.env` ignoré, `.env.example` versionné |

---

## 2. Fonctionnalités recommandées

Utiles au projet, mais **à ne construire qu'après** les vingt-trois exigences ci-dessus. L'ordre compte : le cahier des charges dit explicitement de ne pas inventer avant d'avoir terminé l'obligatoire.

- **Export d'une communication** en JSON ou CSV — utile pour l'analyste, simple à coder.
- **Filtres** sur la liste des communications : par protocole, par adresse, par port.
- **Recherche d'une adresse** dans l'historique.
- **Comparaison de deux analyses** — mesurer ce qui a changé entre deux captures.
- **Fiche d'une adresse IP** — tout ce que le système sait d'une adresse : communications, alertes, enrichissement.
- **Graphique de volume** dans le temps, sur le tableau de bord.
- **Mode « démonstration »** — rejouer un fichier de paquets enregistré, pour présenter sans dépendre du réseau du moment.

---

## 3. Technologies Python proposées

| Brique | Choix | Pourquoi ce choix |
|---|---|---|
| Langage | **Python 3.13** | imposé par le contexte du sprint |
| Capture | **Scapy** | lit et fabrique des paquets ; c'est la référence en Python pour l'analyse réseau ; **testé et fonctionnel sur ta machine** |
| Application web | **Flask** | léger, explicite, déployable sur Vercel ; tu l'as déjà utilisé sur un projet précédent, donc tu sais le défendre |
| Accès base | **`requests` vers l'API REST Supabase** | évite une dépendance lourde, et surtout **explicable à l'oral** : une requête HTTP, une méthode, des en-têtes, du JSON, un code de statut |
| Variables d'environnement | **`python-dotenv`** | sépare les secrets du code ; `.env` jamais versionné |
| Tests | **`pytest`** | standard, lisible |
| Interface | **HTML + CSS + Jinja2** | pas de framework JavaScript : rien à justifier qui ne soit pas du Python |

**Décision assumée : pas de JavaScript, pas de framework front.** Le cahier des charges demande une interface claire, pas une application monopage. Un rendu côté serveur avec Jinja2 est plus simple, plus rapide à charger, et **entièrement défendable** : chaque page est produite par une fonction Python que tu peux expliquer ligne par ligne.

---

## 4. Bibliothèques nécessaires et leur rôle

| Bibliothèque | Rôle exact | Où elle intervient |
|---|---|---|
| **scapy** | ouvrir une interface réseau et lire les paquets bruts ; décoder les couches Ethernet, IP, TCP, UDP, DNS, HTTP | module `capture/` et `analyse/` |
| **flask** | servir les pages web, recevoir les actions (démarrer, arrêter), produire les réponses HTTP | module `webapp/` |
| **jinja2** | remplir les gabarits HTML avec les données (vient avec Flask) | `templates/` |
| **requests** | appeler l'API externe **et** l'API REST Supabase | `enrichissement/` et `stockage/` |
| **python-dotenv** | lire les secrets depuis un fichier `.env` non versionné | au démarrage |
| **pytest** | exécuter les tests | `tests/` |

**Aucune autre bibliothèque n'est nécessaire.** Chaque dépendance supplémentaire est une ligne de plus à défendre à l'oral.

---

## 5. Architecture complète

### Le point central à comprendre

**La capture de paquets ne peut pas se faire depuis un site en ligne.**

Concrètement : ton application déployée sur Vercel tourne dans un centre de données ; elle n'a accès à aucune carte réseau de ta machine, et n'a pas les droits pour en ouvrir une.

Il faut donc **deux rôles pour une seule application** :

```
   APPLICATION LOCALE (sur ta machine)          APPLICATION EN LIGNE (Vercel)
   +------------------------------+             +------------------------------+
   |  CAPTURE   -> les paquets    |             |  lit Supabase                |
   |  ANALYSE   -> les champs     |   écrit     |  affiche le tableau de bord  |
   |  REGROUPEMENT -> communications| ------+   |  affiche l'historique        |
   |  DETECTION -> alertes        |      |      |  affiche les details         |
   |  ENRICHISSEMENT -> API       |      |      +------------------------------+
   |  EXPLICATION -> phrases      |      |                     ^
   +------------------------------+      |                     |
                                         v                     |
                                   +-------------------------------+
                                   |   SUPABASE                    |
                                   |   analyses / communications   |
                                   |   alertes / enrichissements   |
                                   +-------------------------------+
```

**Une seule base de code**, deux usages. Un interrupteur dans la configuration décide :

- **Mode local** (`CAPTURE_LOCALE=1`) : capture active, écriture dans Supabase.
- **Mode en ligne** : lecture seule ; la page Capture affiche un message expliquant que la capture nécessite la machine locale.

**C'est le point le plus important de l'architecture, et la première question qu'un correcteur posera.** La réponse est : *« la capture exige un accès direct à la carte réseau et les droits administrateur — un serveur en ligne n'a ni l'un ni l'autre. Le site publié consulte donc les résultats enregistrés par l'application locale. »*

### Les huit étages, un module chacun

```
  1. CAPTURE          capture/        ouvrir l'interface, lire les paquets bruts
        |
  2. ANALYSE          analyse/        traduire un paquet brut en champs nommes
        |
  3. TRAITEMENT       communications/ regrouper les paquets d'une meme conversation
        |
  4. DETECTION        detection/      appliquer des regles, produire des alertes
        |
  5. ENRICHISSEMENT   enrichissement/ interroger l'API externe
        |
  6. EXPLICATION      explication/    transformer les faits en phrases comprensibles
        |
  7. STOCKAGE         stockage/       ecrire et lire dans Supabase
        |
  8. INTERFACE        webapp/ + templates/   afficher
```

Chaque étage **ne connaît que le précédent**. Le module d'explication ne sait pas qu'il y a un réseau ; il reçoit des dictionnaires et produit des phrases. C'est ce découpage qui rend le projet explicable, testable, et qui répond à l'exigence « ne pas tout mettre dans un fichier géant ».

---

## 6. Arborescence des fichiers

```
analyseur-reseau/
│
├── app.py                      point d'entrée : cree et configure l'application Flask
├── config.py                   lit les variables d'environnement, choisit le mode local/en ligne
├── requirements.txt            dependances Python
├── .env.example                modele des secrets (versionne) — le vrai .env ne l'est jamais
├── .gitignore                  exclut .env, .venv, les captures enregistrees
├── README.md                   documentation professionnelle
│
├── capture/
│   ├── __init__.py
│   ├── interfaces.py           lister les interfaces reseau disponibles
│   └── moteur.py               demarrer / arreter la capture dans un fil d'execution
│
├── analyse/
│   ├── __init__.py
│   ├── paquet.py               un paquet brut -> un dictionnaire de champs nommes
│   └── protocoles.py           connaitre TCP, UDP, DNS, HTTP, HTTPS : role et ports
│
├── communications/
│   ├── __init__.py
│   └── regroupement.py         rapprocher les paquets d'une meme conversation
│
├── detection/
│   ├── __init__.py
│   ├── regles.py               une fonction par regle : nom, condition, poids, explication
│   └── niveaux.py              OBSERVATION / HYPOTHESE / ALERTE
│
├── enrichissement/
│   ├── __init__.py
│   ├── api_geo.py              appel de l'API externe (geolocalisation, ASN, hebergeur)
│   └── cache.py                eviter d'appeler l'API deux fois pour la meme adresse
│
├── explication/
│   ├── __init__.py
│   ├── phrases.py              fabriques de phrases a partir des faits observes
│   └── faits.py               separation stricte : fait observe / interpretation
│
├── stockage/
│   ├── __init__.py
│   └── supabase.py             lecture et ecriture via l'API REST
│
├── webapp/
│   ├── __init__.py
│   ├── routes.py               les adresses des pages
│   └── rendu.py                fonction unique de rendu des pages
│
├── templates/
│   ├── base.html               gabarit commun : en-tete, menu, pied de page
│   ├── tableau_bord.html       /
│   ├── capture.html            /capture
│   ├── communications.html     /communications
│   ├── communication.html      /communication/<id>
│   ├── protocoles.html         /protocoles
│   ├── alertes.html            /alertes
│   ├── enrichissement.html     /enrichissement
│   ├── glossaire.html          /glossaire
│   └── erreur.html             page d'erreur (garde le menu et l'habillage)
│
├── static/
│   └── style.css               une seule feuille de style
│
├── sql/
│   └── schema.sql              creation des tables + fermeture des acces (RLS)
│
├── api/
│   └── index.py                point d'entree serverless pour Vercel
│
├── tools/
│   ├── verifier_capture.py     test de faisabilite de la capture (deja ecrit)
│   ├── fabriquer_trafic.py     provoque du TCP, de l'UDP et du DNS pour les tests
│   └── verifier_supabase.py    teste l'API Supabase sans passer par l'interface
│
└── tests/
    ├── conftest.py             fixtures communes
    ├── test_analyse.py         un paquet brut -> les bons champs
    ├── test_regroupement.py    les paquets d'une conversation sont bien rapproches
    ├── test_protocoles.py      reconnaissance de TCP, UDP, DNS, HTTP
    ├── test_detection.py       chaque regle se declenche sur son cas
    ├── test_explication.py     l'explication ne melange jamais fait et interpretation
    ├── test_erreurs.py         les 8 cas d'erreur du cahier des charges
    └── test_routes.py          chaque page repond 200
```

**Vingt-neuf fichiers, dont aucun ne dépasse sa responsabilité.** Le plus gros module fera quelques dizaines de lignes.

---

## 7. Choix de l'API externe

Le cahier des charges demande de confronter plusieurs solutions avant de choisir, et d'expliquer précisément : quelles données sont envoyées, ce qui revient, et comment le résultat est utilisé.

### Les candidats examinés

| API | Clé requise | Ce qu'elle apporte | Limites |
|---|---|---|---|
| **ip-api.com** | **non** | pays, ville, fournisseur d'accès (FAI), numéro de système autonome (ASN), **indicateur « hébergé en centre de données »** | 45 requêtes/minute en version gratuite ; HTTP seulement |
| **ipwho.is** | non | pays, ville, FAI, ASN | moins de champs ; pas d'indicateur d'hébergement |
| **AbuseIPDB** | **oui** | **réputation** : signalements d'abus, score de confiance | 1 000 requêtes/jour en gratuit ; nécessite une inscription |
| **VirusTotal** | oui | réputation, détections antivirus | 4 requêtes/minute seulement ; pensé pour des fichiers et des URL |
| **RDAP (registres internet)** | non | titulaire d'un bloc d'adresses, pays d'enregistrement | aucun renseignement sur l'usage réel |

### Le choix : **ip-api.com**, avec AbuseIPDB en second si tu fournis une clé

**Pourquoi ip-api.com en principal :**

1. **Aucune clé.** Le projet fonctionne dès la première minute, sans inscription — donc rien à perdre si l'API change.
2. **Elle répond exactement à la question que se pose un analyste réseau.** Devant une communication, on veut savoir : *d'où vient cette adresse, à qui appartient-elle, et est-ce une machine ordinaire ou un serveur ?*
3. **Le champ `hosting` a une vraie valeur analytique.** « Cette adresse appartient à un hébergeur de centre de données » est un **signal** exploitable par le moteur de détection : une communication vers un hébergeur n'a pas la même signification qu'une communication vers un fournisseur d'accès grand public.
4. **Le numéro d'ASN relie les communications entre elles.** Dix destinations différentes dans le même ASN, c'est probablement un réseau de diffusion de contenu — pas dix attaques. **C'est l'apport le plus fort au projet**, car il nourrit directement la détection.

**Pourquoi AbuseIPDB en complément, et non en principal :** le cahier des charges demande aussi un « niveau de risque ». Une réputation d'adresse est l'information la plus directe pour cela. Mais elle exige une clé et un compte. La stratégie retenue est donc : **fonctionner sans clé, et s'améliorer si la clé est présente** — avec un repli automatique. C'est une décision que tu pourras expliquer, et un bon point de soutenance.

### Les données envoyées et reçues

**Envoyé :** uniquement l'**adresse IP publique distante** observée dans une communication. Rien d'autre. Aucune donnée locale, aucun paquet, aucune donnée personnelle.

**Reçu :** un objet JSON, par exemple :

```
{
  "status": "success",
  "country": "Ireland", "countryCode": "IE",
  "isp": "Amazon.com, Inc.", "org": "AWS EC2",
  "as": "AS16509 Amazon.com, Inc.",
  "hosting": true
}
```

**Comment le résultat est utilisé, précisément :**

1. **Affiché** sur la fiche de la communication : le pays, le fournisseur, l'hébergeur.
2. **Transformé en signal** pour le moteur de détection : `hosting = true` devient un signal « destination hébergée ». Il **ne décide pas seul** — il informe.
3. **Stocké** dans la table `enrichissements`, mis en cache par adresse : on n'appelle l'API qu'une fois par IP, jamais deux.

**Deux précautions obligatoires, prévues dès le départ :**

- **Cette API répond parfois `200` en annonçant un échec dans le corps** (adresse privée, par exemple) : il faut donc tester le **contenu**, pas seulement le code HTTP. Nos propres adresses locales (`192.168.x.x`) ne sont pas interrogeables — l'interface doit dire « adresse privée, aucun enrichissement possible » plutôt que d'afficher une erreur.
- **Un timeout est obligatoire** sur chaque appel : si l'API ne répond pas, l'analyse continue sans l'enrichissement. Le cahier des charges l'exige (cas « API indisponible »).

---

## 8. Modèle Supabase proposé

### Pourquoi ces tables existent

Le cahier des charges demande de pouvoir répondre à « pourquoi cette table existe ». Voici la réponse, table par table.

### Table `analyses` — une session de capture

**Ce qu'elle contient :** le nom de l'analyse, l'interface écoutée, l'instant de début et de fin, l'état, et les compteurs totaux (paquets, communications, alertes).

**Pourquoi elle existe :** sans elle, l'historique serait une liste plate de communications sans repère de temps. Le concept d'**analyse** est ce qui permet de dire : *« Voici la capture de mardi soir, voici ce qu'elle a donné, comparons-la avec celle de ce matin. »* C'est la table qui donne son sens à l'historique.

### Table `communications` — une conversation entre deux machines

**Ce qu'elle contient :** l'adresse et le port source, l'adresse et le port destination, le protocole, le nombre de paquets, le volume d'octets, l'instant du premier et du dernier paquet, l'état de la connexion, le service probable, l'explication produite et le niveau de risque. Plus un échantillon plafonné de paquets, en JSON.

**Pourquoi elle existe :** **c'est la table centrale du projet.** Le cahier des charges est explicite : un paquet isolé ne représente pas une communication. C'est la communication qui répond aux sept questions attendues — qui, avec qui, depuis combien de temps, sur quel protocole, sur quel port, combien de paquets, combien de données, encore active ou non.

**Pourquoi `analyse_id` dedans :** pour rattacher chaque communication à la session qui l'a produite. C'est la relation **analyse → communications** (une analyse, plusieurs communications).

### Table `alertes` — ce qui mérite l'attention

**Ce qu'elle contient :** le type d'événement, son niveau (**OBSERVATION**, **HYPOTHÈSE** ou **ALERTE**), le message en français, le nom de la règle déclenchée, l'horodatage, et éventuellement la communication concernée.

**Pourquoi elle existe :** séparer les événements des communications évite d'alourdir la table centrale, et permet une page dédiée. **Le niveau est stocké explicitement**, parce que le cahier des charges l'exige : une anomalie ne doit jamais être présentée comme une attaque.

### Table `enrichissements` — ce que l'API a appris

**Ce qu'elle contient :** l'adresse IP concernée, le nom de l'API, la réponse JSON complète, et l'horodatage de l'appel.

**Pourquoi elle existe :** pour **ne pas rappeler l'API** pour une adresse déjà vue, et pour conserver la **preuve** de ce qui a été reçu. Un point de soutenance important : on stocke la réponse brute, pas seulement notre interprétation — ainsi on peut toujours remonter à la source.

### Table `analyses` et le reste : les relations

```
   analyses (1) ------------> (N) communications
       |                              |
       |                              +----> (N) alertes
       |
       +---------------------> (N) enrichissements
```

- Une **analyse** contient plusieurs **communications**.
- Une **communication** peut déclencher plusieurs **alertes**.
- Une **analyse** produit plusieurs **enrichissements** (un par adresse unique rencontrée).

### Et les paquets, individuellement ?

**Décision assumée : on ne stocke pas chaque paquet.** Une capture d'une minute produit facilement des milliers de paquets ; les écrire un par un saturerait la base et ralentirait l'application.

À la place, un **échantillon plafonné** (les premiers paquets de chaque communication) est conservé dans la communication elle-même, en JSON.

**C'est une décision à assumer et à expliquer** : le cahier des charges autorise « paquets **ou** informations pertinentes ». On conserve les informations pertinentes, et on justifie le choix par le volume. Un correcteur verra là une décision réfléchie, pas un oubli.

### Sécurité de la base

La table sera **fermée** (RLS activée, aucune politique publique). La clé **secrète** reste côté serveur, dans les variables d'environnement. Une clé publique exposée dans le navigateur rendrait la base effaçable par n'importe qui — c'est la faute classique sur ce type de projet.

---

## 9. Fonctionnement général de l'application

### Le trajet d'un paquet, de bout en bout

```
   1. Tu cliques sur « Demarrer »
        |
   2. capture/moteur.py ouvre l'interface choisie et lance un fil d'ecoute
        |
   3. Chaque paquet lu part vers analyse/paquet.py
        -> il ressort sous forme de dictionnaire nomme :
           {source, destination, protocole, ports, taille, horodatage, drapeaux}
        |
   4. communications/regroupement.py range ce paquet dans la conversation
      correspondante (meme source, meme destination, memes ports, meme protocole)
        |
   5. Toutes les quelques secondes, les communications sont consolidees :
        - detection/regles.py les examine et produit des alertes si necessaire
        - enrichissement/api_geo.py interroge l'API pour chaque nouvelle adresse
        - explication/phrases.py produit l'explication en francais
        |
   6. stockage/supabase.py ecrit le tout dans Supabase
        |
   7. L'interface affiche : tableau de bord, communications, detail, alertes,
      enrichissement, historique
```

### Le point de vigilance sur le regroupement

Comment reconnaître que deux paquets appartiennent à la même conversation ? On utilise le **quintuplet** :

```
   (adresse source, port source, adresse destination, port destination, protocole)
```

Deux paquets partageant ces cinq valeurs appartiennent à la même communication. On ajoute une **durée d'expiration** : si aucun paquet n'est vu pendant plusieurs minutes, la conversation est considérée comme **terminée**.

**C'est une réponse directe à la question de défense « comment votre application identifie-t-elle une communication ? »** — et elle vaut aussi pour HTTP : une page web, c'est souvent plusieurs connexions TCP successives.

---

## 10. Plan de développement

Le cahier des charges impose une progression. Voici l'ordre, avec pour chaque version ce qui est livrable et vérifiable.

### Version 1 — Observer et afficher

**Objectif :** prouver qu'on capture du vrai trafic et qu'on sait l'afficher.

- `capture/interfaces.py` — lister les interfaces
- `capture/moteur.py` — démarrer et arrêter
- `analyse/paquet.py` — extraire les champs
- `webapp/` + `templates/base.html` + `templates/capture.html` — page de capture avec **Démarrer / Arrêter / choix de l'interface** et liste des paquets en direct
- Les 8 cas d'erreur de capture

**Vérification :** capture réelle, affichage des paquets, arrêt propre, message clair si aucune donnée.

### Version 2 — Analyser et structurer

**Objectif :** passer du paquet à la communication.

- `analyse/protocoles.py` — TCP, UDP, DNS, HTTP, HTTPS
- `communications/regroupement.py` — le quintuplet et l'expiration
- `templates/communications.html` et `communication.html` — la liste et la vue détaillée
- `templates/tableau_bord.html` — les statistiques
- **Supabase** : création des tables, écriture des analyses et des communications

**Vérification :** une capture produit des communications cohérentes ; les 7 questions ont une réponse ; les données sont dans Supabase.

### Version 3 — Comprendre et expliquer

**Objectif :** la fonctionnalité que le cahier des charges désigne comme la plus importante.

- `explication/faits.py` et `phrases.py` — **séparation stricte fait observé / interprétation**
- `templates/communication.html` enrichi : informations techniques, analyse, explication humaine, risque
- `templates/protocoles.html` — rôle de chaque protocole
- `templates/glossaire.html` — le vocabulaire, expliqué

**Vérification :** sur une communication vers le port 443, l'explication dit « généralement associé à HTTPS » **sans l'affirmer comme un fait**.

### Version 4 — Enrichir et détecter

**Objectif :** l'API externe et le moteur de règles.

- `enrichissement/api_geo.py` et `cache.py`
- `detection/regles.py` et `niveaux.py`
- `templates/alertes.html` et `enrichissement.html`
- Écriture des alertes et des enrichissements dans Supabase

**Vérification :** l'API répond, le JSON brut est affiché, une règle se déclenche sur un trafic fabriqué exprès, et le niveau est correct.

### Version finale — Assistant d'analyse

**Objectif :** l'ensemble devient cohérent et présentable.

- `templates/tableau_bord.html` complété : événements nécessitant l'attention
- Filtres et recherche
- README complet, guide de soutenance, rapport
- Déploiement sur Vercel et vérification de l'URL publique
- Création du dépôt GitHub

**Vérification :** la démonstration complète se déroule sans accroc, les 10 points de la section 20 du cahier des charges sont couverts.

---

## 11. Plan de tests

Le cahier des charges énumère les cas à tester. Voici comment chacun sera réellement provoqué.

| Cas exigé | Comment on le provoque | Ce qu'on vérifie |
|---|---|---|
| **TCP** | requête HTTP vers un site | la communication est reconnue, les ports et drapeaux sont corrects |
| **UDP** | requête DNS | le protocole UDP est identifié |
| **DNS** | résolution d'un nom de domaine | le nom demandé est extrait et expliqué |
| **HTTP / HTTPS** | requête vers un site en clair puis en TLS | le service probable est annoncé **comme probable** |
| **Communications différentes** | deux navigations simultanées | deux communications distinctes, pas une seule |
| **Connexions inhabituelles** | `tools/fabriquer_trafic.py` ouvre un grand nombre de connexions | la règle correspondante se déclenche |
| **Absence de données** | capture sur une interface sans trafic | message clair, pas une page vide ni une erreur |
| **API indisponible** | adresse d'API volontairement invalide | l'analyse se poursuit sans enrichissement, avec un avertissement |
| **Supabase indisponible** | clé volontairement fausse | le rapport s'affiche avec « analyse effectuée mais non enregistrée » |
| **Protocole non reconnu** | trafic ICMP ou protocole rare | affichage « protocole non identifié », sans plantage |

**Deux niveaux de test :**

1. **Tests unitaires** (`pytest`) — chaque module testé seul, sur des données fabriquées. Ils ne dépendent ni du réseau ni de la base, donc ils s'exécutent partout.
2. **Tests réels** (`tools/`) — capture véritable et API véritable. Ils prouvent que le système fonctionne sur du vrai trafic.

**Le README présentera ces scénarios dans un tableau**, avec le résultat obtenu — c'est explicitement demandé.

---

## 12. Plan de déploiement

**Trois étapes, dans cet ordre.**

**1. Supabase.** Création du projet, puis des tables via le bloc SQL fourni. La table reste fermée, la clé secrète va dans les variables d'environnement.

**2. Vercel.** L'application web est publiée ; elle lit Supabase et affiche l'historique. Le module de capture n'est **jamais importé** dans cet environnement — sans quoi l'application refuserait de démarrer, faute de pilote réseau. C'est une protection à écrire dès le premier jour.

**3. GitHub.** Dépôt public avec README, `.gitignore` excluant `.env`, et `.env.example` montrant les noms des variables **sans leurs valeurs**.

**Point de vigilance :** entre le code local et le déploiement, les variables d'environnement ne sont pas les mêmes (Vercel ne lit pas ton `.env` local). C'est l'erreur classique, et elle se solde par une page vide en ligne alors que tout fonctionne sur ta machine.

---

## 13. Risques techniques

| # | Risque | Gravité | Parade |
|---|---|---|---|
| 1 | **La capture ne fonctionne pas** | critique | **déjà levé** : Npcap installé, 158 paquets capturés lors du test |
| 2 | **Le site en ligne ne peut pas capturer** | élevée | architecture à deux modes, décidée dès maintenant — pas découverte en fin de projet |
| 3 | **Droits administrateur requis** | moyenne | documenté dans le README ; l'application explique le problème au lieu d'échouer |
| 4 | **Mauvaise interface choisie** | moyenne | ta machine expose des interfaces virtuelles (VMware, Wi-Fi Direct) : la page de capture les affiche toutes, avec leur adresse, pour éviter la confusion |
| 5 | **Volume de paquets** | moyenne | agrégation par communication ; écriture périodique, pas paquet par paquet |
| 6 | **HTTPS illisible** | moyenne | **limite assumée** : le contenu chiffré n'est pas analysable. On observe les métadonnées, et on l'écrit noir sur blanc dans le README |
| 7 | **DNS absent de la capture** | faible | le cache système évite parfois la requête ; `tools/fabriquer_trafic.py` forcera une résolution sur un nom jamais vu |
| 8 | **API externe indisponible ou limitée** | moyenne | timeout, cache par adresse, et poursuite de l'analyse sans l'enrichissement |
| 9 | **Supabase indisponible** | moyenne | le rapport s'affiche quand même, avec un avertissement explicite |
| 10 | **Clé exposée dans GitHub** | élevée | `.env` ignoré dès le premier commit ; contrôle avant chaque envoi |

**Le sixième mérite une phrase particulière.** Il ne faut pas promettre ce que le système ne peut pas faire : **le contenu des communications HTTPS n'est pas lisible**, puisque c'est précisément le but du chiffrement. L'analyseur observe *qui* parle à *qui*, sur *quel port*, *combien* de données, et *pendant* combien de temps. Le dire soi-même avant qu'on te le demande est une force, pas un aveu de faiblesse.

---

## 14. Questions probables de défense technique

Voici les questions du cahier des charges, avec l'orientation de la réponse. **Nous les travaillerons une par une à chaque version**, mais tu peux déjà voir où l'on va.

### Python

**Pourquoi Scapy plutôt qu'une autre bibliothèque ?**
Parce qu'elle fait exactement le travail demandé — décoder des paquets — sans dépendre d'un outil externe, et qu'elle fonctionne sur ta machine (vérifié). L'alternative, `pyshark`, obligerait à installer Wireshark en plus.

**Comment ton programme fonctionne-t-il ?**
Huit modules chaînés : capture, analyse, regroupement, détection, enrichissement, explication, stockage, interface. Chaque module reçoit une donnée simple et en produit une autre, plus riche. Le détail du trajet est au point 9 de ce document.

**Comment tes fonctions communiquent-elles ?**
Par des dictionnaires Python. Un module ne connaît pas l'existence du réseau : il reçoit un dictionnaire de champs et rend un dictionnaire enrichi. C'est ce qui rend chaque module testable seul.

**Comment gères-tu les erreurs ?**
Huit cas identifiés, chacun avec un message en français compréhensible pour l'utilisateur — jamais une trace technique brute. Le tableau est au point 11.

### Réseau

**Qu'est-ce qu'un paquet ?**
Un morceau de données transmis sur le réseau, portant une en-tête qui indique d'où il vient, où il va, et comment il doit être traité.

**Comment fonctionne une communication réseau ?**
Trois temps pour TCP : une **ouverture** (échange SYN / SYN-ACK / ACK), un **échange** de données, une **fermeture**. UDP, lui, envoie sans établir de connexion — c'est le cas de DNS.

**Comment ton application identifie-t-elle une communication ?**
Par le quintuplet : adresse et port source, adresse et port destination, protocole. Plus une durée d'expiration pour clore les conversations inactives.

**Différence entre les protocoles que tu as étudiés ?**
TCP est fiable et orienté connexion ; UDP est rapide et sans connexion ; DNS traduit les noms en adresses et utilise UDP ; HTTP transporte le web ; HTTPS est du HTTP dans un tunnel chiffré.

### API

**Qu'est-ce qu'une API ?**
Un service qu'on interroge par le réseau, qui reçoit une demande et renvoie une réponse structurée. Ici : on envoie une adresse IP, elle renvoie le pays, le fournisseur, l'hébergeur.

**Qu'est-ce que JSON ?**
Un format de texte structuré en paires « clé : valeur », lisible par un humain comme par un programme. C'est le format des réponses de l'API et de Supabase.

**Comment gères-tu une réponse invalide ?**
Trois tests successifs : le code HTTP est-il correct ? le corps est-il du JSON valide ? le contenu annonce-t-il un succès ? — car cette API répond parfois `200` en annonçant un échec dans le corps. L'interface affiche alors « enrichissement indisponible », sans interrompre l'analyse.

### Base de données

**Pourquoi Supabase ?**
Parce qu'il est demandé par le cahier des charges, et parce qu'il expose une API REST : on y accède par de simples requêtes HTTP, ce qui est directement explicable.

**Quelles informations stockes-tu, et pourquoi cette structure ?**
Quatre tables : analyses, communications, alertes, enrichissements. La justification est au point 8 — et la décision de **ne pas stocker chaque paquet** est un choix assumé, justifié par le volume.

### Intelligence

**Quelle information est réellement observée, et quelle information est déduite ?**
C'est la distinction la plus importante du projet, et elle est **affichée à l'écran** :

- **Observé** : `port_destination = 443`, `protocole = TCP`, `192.168.1.6 → 20.86.94.139`
- **Déduit** : « ce port est généralement associé à HTTPS »
- **Hypothèse** : « cette communication est probablement du trafic web chiffré »
- **Alerte** : « cette machine contacte un nombre inhabituel de destinations »

**Comment empêches-tu ton système d'inventer une conclusion ?**
Par construction, et non par surveillance : le moteur d'explication ne fabrique jamais une phrase à partir de rien. Il assemble des phrases **à partir des champs réellement présents** dans le paquet. Un champ absent produit « information non disponible » — jamais une supposition. Et l'intervention éventuelle d'une IA se limite à **reformuler ces mêmes faits**, sans jamais introduire d'information nouvelle.

---

## Ce dont j'ai besoin pour démarrer

**Deux éléments à me fournir** — ils s'obtiennent pendant que je code la Version 1, donc le travail ne s'arrête pas :

**1. Supabase.** L'**URL du projet** et la clé **`publishable`** (ou `anon`).
→ Ne me donne **jamais** la clé `secret` / `service_role` : elle se saisira plus tard directement dans les variables d'environnement, sans passer par cette conversation.

**2. La confirmation que je crée le dépôt GitHub** au nom de `tad-code`, une fois la Version 1 fonctionnelle.

Et une **validation de ta part** sur ce document, en particulier sur les quatre points de conception qui engagent toute la suite :

1. L'architecture **deux modes** (capture locale / lecture en ligne) — c'est le choix structurant.
2. Le choix de **ip-api.com** comme API principale, sans clé.
3. Le fait de **ne pas stocker chaque paquet**, mais les communications et un échantillon.
4. L'interface en **HTML rendu côté serveur**, sans framework JavaScript.

Dès ton accord, je commence la **Version 1** — et pour une seule chose : capturer et afficher.
