# Analyseur réseau

**Application en ligne :** https://analyseur-reseau.vercel.app

**Dépôt :** https://github.com/tad-code/packet-analyzer

> L'application en ligne fonctionne en **lecture seule** : un serveur distant n'a
> pas de carte réseau, il ne peut donc pas capturer. Il affiche les captures
> enregistrées depuis votre machine, qui remontent par Supabase.

Un outil qui lit le trafic réseau, le structure, et **explique en langage humain**
ce qui se passe — au lieu d'afficher des lignes techniques illisibles.

> **État actuel : version 4 — détecter et enrichir.**
> Capture réelle, regroupement en communications, enregistrement dans Supabase,
> historique, **explication en langage humain**, **alertes produites par des règles**,
> **identification des adresses distantes**, et **mode en ligne en lecture seule**.
>
> **Vérifié :** 105 tests unitaires, 53 contrôles fonctionnels, et **18 contrôles de
> bout en bout** contre la base réelle (écriture, relecture, tri, suppression en cascade,
> alertes). L'enrichissement a été exercé sur de vraies adresses.

---

## 1. Quel problème cet outil résout-il ?

Les analyseurs réseau classiques affichent ceci :

```
TCP  192.168.1.15:52341 -> 142.250.x.x:443  Flags: SYN
```

Une personne qui débute en cybersécurité n'y comprend rien. Elle voit des chiffres,
pas une situation.

Cet outil prend ces mêmes données et les transforme en une phrase compréhensible :

> « La machine 192.168.1.15 ouvre une connexion vers un serveur distant sur le port
> 443, généralement associé aux communications web sécurisées. »

La différence est le cœur du projet : **transformer des données techniques en
informations compréhensibles**, sans jamais confondre ce qui est observé avec ce qui
est supposé.

---

## 2. Comment fonctionne le système

Le trajet d'une donnée, de la carte réseau jusqu'à l'écran :

```
  Capture   capture/       ouvrir une carte reseau, lire les paquets bruts
     |
  Analyse   analyse/       traduire un paquet brut en champs nommes
     |
  Traitement  communications/  REGROUPER les paquets d'une meme conversation
     |
  Detection   detection/       (version 4) appliquer des regles, produire des alertes
     |
  Enrichissement  enrichissement/  (version 4) interroger une API externe
     |
  Explication  explication/    (version 3) produire des phrases en francais
     |
  Stockage  stockage/          (version 2) enregistrer dans Supabase
     |
  Interface  webapp/ + templates/   afficher
```

**Chaque étage ne connaît que le précédent.** Le module d'explication ne sait pas
qu'il existe un réseau : il reçoit des dictionnaires et écrit des phrases. C'est ce
découpage qui rend le projet testable module par module et explicable ligne par ligne.

---

## 3. Le point d'architecture à comprendre

**La capture de paquets ne peut pas se faire depuis un site en ligne.**

Un site hébergé tourne dans un centre de données : il n'a accès à aucune carte réseau,
et pas les droits d'en ouvrir une. L'application a donc deux modes :

| Mode | Où | Ce qu'il fait |
|---|---|---|
| **Local** | sur la machine de l'analyste | capture les paquets, écrit dans Supabase |
| **En ligne** | sur l'hébergeur | lit Supabase, affiche l'historique — ne capture rien |

Le mode est choisi par la variable `CAPTURE_LOCALE` (1 = local, 0 = en ligne). Le
module de capture n'est **jamais importé** en mode en ligne : sans cette précaution,
l'application refuserait de démarrer sur l'hébergeur, faute de pilote réseau.

---

## 4. Technologies et bibliothèques

| Bibliothèque | Rôle |
|---|---|
| **Scapy** | ouvrir une interface réseau et décoder les paquets (Ethernet, IP, TCP, UDP, DNS) |
| **Flask** | servir les pages web et recevoir les actions |
| **Jinja2** | remplir les gabarits HTML (fourni avec Flask) |
| **requests** | appeler l'API externe et l'API REST Supabase *(versions à venir)* |
| **python-dotenv** | lire les secrets depuis un fichier `.env` non versionné |
| **pytest** | exécuter les tests |

Aucune autre dépendance : chaque bibliothèque ajoutée serait une ligne de plus à
justifier.

### Le pilote de capture

Sur Windows, lire les paquets exige le pilote **Npcap** (gratuit) et des **droits
administrateur**. Sans lui, aucune bibliothèque Python ne peut accéder à la carte
réseau. C'est un prérequis, pas une option.

---

## L'explication

C'est la fonctionnalité centrale du projet : traduire des paquets en phrases
compréhensibles, **sans jamais confondre ce qui est observé avec ce qui est déduit**.

Chaque communication produit :

| Élément | Ce que c'est |
|---|---|
| **Résumé** | une phrase en français courant |
| **Faits observés** | ce qui a été vu dans les paquets, avec le champ d'origine |
| **Déductions** | ce qui en a été conclu, chacune citant le fait sur lequel elle repose |
| **Comptes** | combien d'observations, d'interprétations, d'hypothèses |

Trois niveaux de certitude, distingués à l'écran : **observation**, **interprétation**,
**hypothèse**. Quand une donnée manque, elle est annoncée comme manquante — jamais comblée.

L'explication produite au moment de la capture est **enregistrée en base**, afin que
l'historique reste stable quand les règles évolueront.

### Une seule explication, deux sources

La vue en direct travaille sur les communications du regroupement ; l'historique
travaille sur des lignes de la base. Les deux formes diffèrent — extrémités en
dictionnaires d'un côté, en colonnes de l'autre. `explication/adaptateur.py` traduit
la seconde vers la première, ce qui évite d'écrire et de maintenir **deux moteurs**
qui finiraient par diverger.

### Les pages de référence

`/protocoles` détaille ce que le programme sait des protocoles et des ports.
`/glossaire` définit tout le vocabulaire employé.

Ces deux pages existent pour une raison : **rien dans l'application ne doit reposer
sur une connaissance cachée**. Ce que le programme affirme, l'utilisateur peut le lire
et le contester.

## La détection

Six règles examinent l'ensemble des communications et produisent des **alertes**.
Elles ne disent jamais « c'est une attaque » : chacune énonce ce qu'elle a observé,
ce qu'elle en déduit, et ce qu'il faudrait vérifier.

| Règle | Ce qu'elle repère |
|---|---|
| `refus-repetes` | Plusieurs connexions refusées — recherche de services, ou logiciel qui réessaie |
| `service-en-clair` | Telnet, FTP, HTTP : le contenu circule sans chiffrement |
| `connexions-repetees` | Une même destination contactée par des échanges brefs et réguliers |
| `destinations-multiples` | Une machine locale échange avec un grand nombre de serveurs |
| `volume-concentre` | Une seule communication transporte la majeure partie du volume |
| `service-non-identifie` | Un port inconnu, avec un échange soutenu |

Trois gravités : **information**, **attention**, **vigilance**. Les alertes sont
enregistrées avec la capture, pour la même raison que les résumés : les règles
évolueront, et l'historique ne doit pas changer sous les pieds de l'utilisateur.

> Une règle qui échoue est ignorée, les autres continuent. Une alerte manquante est
> fâcheuse ; un plantage qui masque tout l'est davantage.

## L'enrichissement

Les adresses distantes sont identifiées par **ip-api.com**, qui ne demande aucune clé.

- **Les adresses locales et de multidiffusion ne sont pas interrogées.** Une adresse
  192.168.x.x n'appartient à aucun pays : l'envoyer à un service externe révèlerait la
  structure du réseau sans rien apprendre en retour.
- **Les adresses sont interrogées en lot**, cent par requête. Une requête par adresse
  épuiserait le quota autorisé en quelques secondes.
- **Seules les réponses obtenues sont mises en cache.** Une panne passagère n'est pas
  figée dans le fichier.

L'enrichissement est un **confort**, jamais une dépendance. S'il échoue, l'analyse
reste complète : les adresses s'affichent, sans pays ni opérateur.

## Les deux modes

**Une seule base de code, deux fonctionnements.**

| | Mode local (`CAPTURE_LOCALE=1`) | Mode en ligne |
|---|---|---|
| Où | votre machine | un serveur distant |
| Capture | possible | **impossible** — pas de carte réseau |
| Source des données | le tampon de capture | la dernière capture enregistrée |
| Usage | observer son propre réseau | consulter ce qui a été observé ailleurs |

Un serveur distant ne peut pas capturer de paquets : ce n'est pas un réglage, c'est
une limite technique. L'interface le dit à l'utilisateur au lieu de l'afficher comme
une panne.

## La base de données

L'application écrit dans **Supabase**, par son API REST.

**Sans clé à privilèges élevés, tout le reste fonctionne** — capture, communications,
tableau de bord. Seul l'enregistrement et l'historique réclament la base.

### Mise en place, une seule fois

**1. Créer la clé.** Supabase → projet → **Settings → API Keys** → section
**Secret keys** → **Create new secret key**. Elle ne s'affiche qu'une fois : copiez-la.

*(Variante : la clé historique `service_role`, même page, section « Legacy API keys ».
Elle est consultable à tout moment et fonctionne identiquement.)*

**2. La renseigner.** Dans `.env`, l'une ou l'autre de ces lignes :

```
SUPABASE_SECRET_KEY=***
SUPABASE_SERVICE_ROLE_KEY=***
```

**3. Créer les tables.** Supabase → **SQL Editor** → **New query** → coller le
contenu de `sql/a-coller.sql` → **Run**. La version commentée, qui justifie chaque
table, est dans `sql/schema.sql`.

**3 bis. La table des alertes.** Supabase → **SQL Editor** → coller le contenu de
`sql/ajouter-alertes.sql` → **Run**. *(Inutile si vous exécutez `sql/a-coller.sql`,
qui contient déjà les trois tables.)*

**4. Vérifier.** `python tools/verifier_ecriture_supabase.py` — écrit, relit,
supprime, et contrôle l'effacement en cascade. Les données d'essai sont retirées.

### Un point à connaître

Le plan gratuit **met un projet en pause après sept jours sans activité**, et le
domaine cesse alors de répondre. `python tools/etat_supabase.py` indique dans quel
état se trouve le projet.

## Installation

### Prérequis

- Python 3.11 ou plus récent
- **Npcap** installé — <https://npcap.com/#download>
- Les droits administrateur pour lancer une capture

### Mise en place

```bash
# 1. Recuperer le projet
git clone <adresse-du-depot>
cd <dossier-du-projet>

# 2. Creer un environnement virtuel
python -m venv .venv
.venv\Scripts\activate        # Windows

# 3. Installer les dependances
pip install -r requirements.txt

# 4. Creer le fichier de configuration
copy .env.example .env          # Windows
```

Renseigner ensuite `.env` avec vos propres valeurs si vous utilisez Supabase.

### Lancement

```bash
python app.py
```

Puis ouvrir <http://127.0.0.1:5000>.

---

## 6. Utilisation

1. **Choisir la carte réseau** dans la liste déroulante.
   Les interfaces marquées *virtuelle* (VMware, Hyper-V, adaptateurs Wi-Fi Direct)
   ne transportent aucun trafic réel : les choisir donne une liste vide.
2. **Cliquer sur « Démarrer ».** La page se rafraîchit automatiquement toutes les
   deux secondes.
3. **Produire du trafic** pour voir apparaître des paquets : ouvrir une page web,
   lancer une commande réseau.
4. **Cliquer sur « Arrêter »** pour figer l'affichage.
5. **« Vider la liste »** efface les paquets conservés en mémoire.

### Ce que l'on voit

| Colonne | Signification |
|---|---|
| **N°** | numéro d'ordre du paquet dans la capture |
| **Heure** | horodatage à la seconde près |
| **Source / Destination** | adresses IP des deux machines |
| **Protocole** | TCP (fiable, avec connexion), UDP (sans connexion), ICMP (contrôle) |
| **Ports** | port de l'émetteur, puis service contacté |
| **Taille** | octets du paquet, en-têtes compris |
| **Service probable** | service habituellement associé à ce port — une indication, pas une certitude |

---

## 7. Structure du projet

```
.
├── app.py                  point d'entree : cree l'application Flask
├── config.py               lit les variables d'environnement, choisit le mode
├── requirements.txt        dependances et versions exactes
├── .env.example            modele des variables (versionne)
├── capture/
│   ├── interfaces.py       lister les cartes reseau disponibles
│   └── moteur.py           demarrer, arreter, conserver les paquets
├── analyse/
│   └── paquet.py           un paquet brut -> des champs nommes
├── communications/
│   └── regroupement.py     regrouper les paquets en communications
├── stockage/
│   └── supabase.py         lire et ecrire dans Supabase (API REST)
├── sql/
│   └── schema.sql          creation des tables (a executer une fois)
├── webapp/
│   ├── routes.py           les adresses des pages
│   └── rendu.py            fonction unique de rendu des pages
├── templates/              gabarits HTML
├── static/style.css        feuille de style unique
├── api/index.py            point d'entree pour l'hebergeur
├── tools/                  scripts de test et de diagnostic
└── tests/                  tests unitaires (versions a venir)
```

---

## 8. Routes exposées

| Route | Méthode | Rôle |
|---|---|---|
| `/` | GET | tableau de bord : chiffres essentiels et dernières communications |
| `/communications` | GET | liste des communications observées |
| `/communication/<clé>` | GET | détail d'une communication : informations techniques et réponses |
| `/capture` | GET | choisir une carte réseau, démarrer, arrêter |
| `/capture/demarrer` | POST | démarrer une capture sur l'interface choisie |
| `/capture/arreter` | POST | arrêter la capture |
| `/capture/vider` | POST | vider la liste des paquets conservés |
| `/capture/enregistrer` | POST | enregistrer la capture et ses communications |
| `/historique` | GET | captures enregistrées dans Supabase |
| `/historique/<id>` | GET | détail d'une capture enregistrée |
| `/health` | GET | état du service, en JSON |

---

## 9. Gestion des erreurs

| Cas | Comportement |
|---|---|
| Interface inexistante | message « Impossible d'ouvrir l'interface… », la capture ne démarre pas |
| Pilote absent ou droits insuffisants | message expliquant que Npcap et les droits administrateur sont nécessaires |
| Aucune interface détectée | bandeau explicatif, capture impossible |
| Aucun paquet capturé | bandeau invitant à produire du trafic |
| Page inconnue | page 404 avec menu et habillage conservés |
| Mauvaise méthode HTTP | page 405 explicative |
| Erreur interne | page 500 ; l'application reste utilisable |

---

## 10. Limites connues

**Le contenu des communications chiffrées n'est pas lisible.** C'est le principe même
du HTTPS. L'outil observe *qui* parle à *qui*, sur *quel port*, *combien* de données
et *pendant* combien de temps — jamais le contenu.

**Les paquets conservés sont limités** aux 500 derniers (valeur réglable). Une capture
longue produit plus de paquets que nécessaire à l'affichage ; les plus anciens sont
oubliés, mais ils restent comptés.

**Le DNS peut passer inaperçu** si la machine a déjà la réponse en cache : aucune
requête n'est alors émise.

**L'outil ne capture pas sur les autres machines du réseau.** Seul le trafic visible
depuis cette carte réseau est observé.

---

## 11. Usage responsable

Cet outil ne doit être utilisé que sur un réseau sur lequel vous êtes autorisé à
travailler : le vôtre, celui de votre organisation avec son accord, ou un
environnement d'entraînement prévu à cet effet.

---

## Où sont les explications

**Le code ne contient aucun commentaire.** Les explications sont rassemblées dans
le dossier `documentation/`, un fichier `.txt` par domaine :

```
documentation/
    DOCUMENTATION-racine.txt           app.py, config.py
    DOCUMENTATION-capture.txt          lire les paquets
    DOCUMENTATION-analyse.txt          interpreter un paquet
    DOCUMENTATION-communications.txt   regrouper en conversations
    DOCUMENTATION-explication.txt      transformer en phrases
    DOCUMENTATION-detection.txt        les regles d'alerte
    DOCUMENTATION-enrichissement.txt   identifier les adresses
    DOCUMENTATION-stockage.txt         lire et ecrire dans Supabase
    DOCUMENTATION-webapp.txt           routes et rendu
    DOCUMENTATION-api.txt              point d'entree serveur
    DOCUMENTATION-sql.txt              creation des tables
    DOCUMENTATION-tests.txt            ce que verifie chaque test
    DOCUMENTATION-outils.txt           les scripts de verification
    DOCUMENTATION-gabarits.txt         gabarits et feuille de style
```

Chaque fichier décrit, dans l'ordre : le rôle du module, puis celui de chaque
fonction. Le document suit la structure du code, ce qui permet de le lire en
parallèle.

## Vérifications

| Script | Ce qu'il vérifie |
|---|---|
| `tools/verifier_prerequis.py` | droits, Npcap, Scapy, Git |
| `tools/verifier_capture.py` | que des paquets réels sont bien interceptés |
| `tools/tester_application.py` | 42 contrôles fonctionnels sur les pages |
| `tools/tester_bout_en_bout.py` | capture → enregistrement → historique, puis nettoyage |
| `tools/verifier_ecriture_supabase.py` | écriture, relecture et suppression en base |
| `tools/verifier_schema_sql.py` | le script SQL, sur un PostgreSQL local jetable |
| `tools/etat_supabase.py` | si le projet est actif ou en pause |
| `tools/capturer_interface.py` | les captures d'écran de `docs/` |

`tester_bout_en_bout.py` accepte `GARDER=1` pour conserver la capture au lieu de la
supprimer — utile pour montrer l'historique rempli.

## Tests

```bash
# Tests unitaires (aucun reseau, aucune base : ils s'executent partout)
python -m pytest tests/ -q

# Test fonctionnel complet (l'application doit etre lancee)
python tools/tester_application.py

# Verification du pilote de capture et des interfaces
python tools/verifier_capture.py
```

**24 tests unitaires** couvrent le regroupement : les deux sens d'un échange forment
une seule communication, les comptages sont exacts, l'état déduit des drapeaux est
correct, l'inactivité termine une communication, et les cas incomplets ne cassent rien.

**39 contrôles fonctionnels** couvrent l'application entière : pages, capture réelle,
regroupement, sept questions du cahier des charges, et les cas d'erreur.
