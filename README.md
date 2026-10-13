# Analyseur réseau intelligent

**Application en ligne (lecture seule) :** <https://analyseur-reseau.vercel.app>
**Dépôt :** <https://github.com/tad-code/packet-analyzer>
**Version :** 4.0 — « détecter et enrichir »

Ce projet lit le trafic réseau d'une machine, le regroupe en communications et
**explique en langage humain** ce qui se passe, au lieu d'afficher des lignes
techniques illisibles. Il enregistre chaque capture dans une base Supabase, qu'un
site en ligne peut ensuite consulter.

---

## 1. À lire avant de tester : pourquoi la capture est locale

**Ce n'est pas un bug si le site en ligne affiche `paquets_vus: 0`. C'est l'architecture.**

```
   ┌──────────────────────────────┐          ┌───────────────────────────┐
   │  VOTRE MACHINE (mode local)  │          │  SITE EN LIGNE (Vercel)   │
   │                              │          │                           │
   │  carte réseau + pilote Npcap │          │  aucun accès à une carte  │
   │  -> capture des paquets      │          │  réseau : il ne peut pas  │
   │  -> analyse + explication    │  écrit   │  capturer                 │
   │        │                     │ ───────► │        │                  │
   │        └─► Supabase (base)   │ Supabase │        └─► lecture seule   │
   └──────────────────────────────┘          └───────────────────────────┘
```

- **La capture ne peut avoir lieu qu'en local.** Un site hébergé tourne dans un
  centre de données : il n'a accès à aucune carte réseau du réseau observé, et pas
  les droits d'en ouvrir une. L'observation se fait donc sur la machine de
  l'analyste, avec le pilote **Npcap**.
- **Les données remontent par Supabase.** Une fois la capture terminée, l'application
  locale écrit dans la base (API REST Supabase) la capture, ses communications, leurs
  explications et les alertes produites. La base est le seul point de rencontre entre
  les deux modes.
- **Ce que montre le site en ligne.** Il lit Supabase et affiche l'historique des
  captures enregistrées : compteurs, communications, explications, alertes. Il ne
  capture rien — son bandeau le dit : « Mode lecture seule — cette page montre la
  dernière capture enregistrée, et non le trafic de cette machine. »

Conclusion à retenir : `/health` du site répond `{"capture_possible": false,
"paquets_vus": 0, "mode": "en ligne", "etat": "ok"}`. C'est le comportement attendu
d'une instance en ligne, pas une panne.

---

## 2. Vérifier sans rien installer

### Le site

<https://analyseur-reseau.vercel.app>

### La preuve : la page `/historique`

<https://analyseur-reseau.vercel.app/historique> liste les captures **réellement
enregistrées en base**. Ligne la plus récente, lue le 13 octobre 2026 :

```
17 | 2026-10-13 10:36:19 | Wi-Fi | 500 | 13 | 110.7 Ko | terminee
```

Soit la capture n° 17, démarrée le 2026-10-13 à 10:36:19 sur l'interface **Wi-Fi**,
avec **500 paquets** observés, **13 communications** distinctes, **110.7 Ko** de
volume, état *terminée*. Ces données ne peuvent venir que d'une capture locale réelle.

Depuis cette page on peut aller plus loin sans rien installer :

| Pour voir | Aller à |
|---|---|
| le détail d'une capture (communications, explications, alertes) | `/historique/17` |
| le détail d'une communication, avec ses trois niveaux d'explication | `/historique/17/communication/476` |
| l'état du service en JSON | `/health` |

---

## 3. Vérifier les tests

**Commande exacte :**

```bash
python -m pytest tests/ -q
```

**Résultat relevé le 13 octobre 2026 : `105 passed`.**

Les 105 tests ont été comptés un par un (collecte + exécution) et se répartissent
ainsi :

| Fichier | Tests | Ce qui est couvert |
|---|---|---|
| `tests/test_regroupement.py` | 24 | les paquets d'une même conversation forment une seule communication ; comptages, état déduit des drapeaux, fin par inactivité, cas incomplets |
| `tests/test_explication.py` | 36 | la production des phrases : un fait observé n'est jamais présenté comme une déduction, une donnée manquante est annoncée |
| `tests/test_detection.py` | 17 | les règles d'alerte se déclenchent **et ne se déclenchent pas à tort** |
| `tests/test_stockage.py` | 15 | la traduction vers Supabase, y compris les réponses en erreur |
| `tests/test_enrichissement.py` | 13 | l'identification des adresses, les lots, le cache, les pannes |
| **Total** | **105** | |

Ces tests ne capturent aucun paquet et ne touchent à aucun réseau ni à aucune base :
ils fabriquent des paquets à la main. Ils s'exécutent donc partout, en moins d'une
seconde, avec toujours le même résultat.

### Les autres vérifications (facultatives)

Elles demandent l'application lancée en local et ne sont pas nécessaires pour juger
le projet :

| Script | Ce qu'il vérifie |
|---|---|
| `tools/tester_application.py` | contrôles fonctionnels sur les pages (l'application doit tourner sur 127.0.0.1:5000) |
| `tools/tester_bout_en_bout.py` | capture → enregistrement → historique, puis nettoyage ; `GARDER=1` conserve la capture |
| `tools/verifier_ecriture_supabase.py` | écriture, relecture et suppression réelle en base |
| `tools/verifier_capture.py` | que des paquets réels sont bien interceptés (Npcap + droits admin) |
| `tools/verifier_schema_sql.py` | le script SQL, sur un PostgreSQL local jetable |
| `tools/verifier_prerequis.py` | droits, Npcap, Scapy, Git |
| `tools/etat_supabase.py` | si le projet Supabase est actif ou en pause |

---

## 4. Exécuter en local (seul mode où la capture est possible)

**Prérequis :**

- Python 3.11 ou plus récent ;
- le pilote **Npcap** installé — <https://npcap.com/#download> (obligatoire : sans
  lui, aucune bibliothèque Python n'accède à la carte réseau) ;
- les **droits administrateur** pour ouvrir l'interface ;
- le fichier `.env` renseigné (Supabase) pour l'enregistrement et l'historique.

**Lancement en un clic**, à la racine du projet :

```bash
demarrer-analyseur.bat
```

Le script ouvre l'application locale, puis :

**Adresse locale : <http://127.0.0.1:5000>**

Laissez la fenêtre ouverte pendant l'utilisation ; fermez-la (ou `Ctrl+C`) pour
arrêter l'analyseur.

> **C'est le seul mode où la capture est possible.** La version en ligne est en
> lecture seule : un serveur distant n'a aucun accès au réseau observé. Le mode est
> choisi par la variable `CAPTURE_LOCALE` (1 = local, 0 = en ligne) ; en mode en
> ligne, le module de capture n'est **jamais importé**, sans quoi l'application
> refuserait de démarrer sur l'hébergeur faute de pilote.

**Utilisation :** choisir la carte réseau (les interfaces marquées *virtuelle* —
VMware, Hyper-V, Wi-Fi Direct — ne transportent aucun trafic réel), cliquer sur
**Démarrer**, produire du trafic (ouvrir une page web), puis **Arrêter** pour figer
l'affichage.

---

## 5. La particularité du projet : trois niveaux d'explication

Chaque communication produit trois niveaux, distincts à l'écran et jamais mélangés,
conformément à la règle centrale du projet : **ce qui est observé et ce qui est déduit
ne sont jamais confondus**.

| Niveau | Ce que c'est | Vérifiable sur le site |
|---|---|---|
| **Observation** | ce qui a été lu dans les paquets, avec le champ d'origine cité (`premiere_extremite`, `protocole`, `port_service`…) | « 11 faits observés dans les paquets », « Ce qui a été observé — aucune de ces valeurs n'est déduite » |
| **Interprétation** | ce qui en est conclu, chaque conclusion citant le fait sur lequel elle repose | « interprétations », chaque déduction indique le fait observé qui la fonde |
| **Hypothèse** | ce qui reste incertain, annoncé comme tel et donc potentiellement faux | « hypothèses », « Les hypothèses sont annoncées comme telles : elles peuvent être fausses » |

Exemple, avant / après :

```
TCP  192.168.1.15:52341 -> 142.250.x.x:443  Flags: SYN
```

> « La machine 192.168.1.15 ouvre une connexion vers un serveur distant sur le port
> 443, généralement associé aux communications web sécurisées. »

Quand une donnée manque, elle est annoncée comme manquante — jamais comblée. Et
l'explication produite **au moment de la capture** est enregistrée en base : quand
les règles évolueront, l'historique ne changera pas sous les pieds de l'utilisateur.
La page de détail sépare deux blocs : « Phrase enregistrée au moment de la capture »
(ce qui a été constaté ce jour-là) et « Détail ci-dessous, recalculé depuis les
données conservées ».

### Une seule explication, deux sources

La vue en direct travaille sur les communications du regroupement ; l'historique
travaille sur des lignes de la base. Les deux formes diffèrent — extrémités en
dictionnaires d'un côté, en colonnes de l'autre (`ip_premiere`, `port_premiere`…).
`explication/adaptateur.py` traduit la seconde vers la première, ce qui évite d'écrire
et de maintenir **deux moteurs** qui finiraient par diverger : le jour où une phrase
change, la vue en direct et l'historique resteraient alignés.

---

## 6. Comment fonctionne le système

```
  Capture   capture/          ouvrir une carte reseau, lire les paquets bruts
     |
  Analyse   analyse/          traduire un paquet brut en champs nommes
     |
  Traitement  communications/ regrouper les paquets d'une meme conversation
     |
  Detection   detection/      (v4) appliquer des regles, produire des alertes
     |
  Enrichissement  enrichissement/  (v4) interroger une API externe
     |
  Explication  explication/   (v3) produire des phrases en francais
     |
  Stockage  stockage/         (v2) enregistrer dans Supabase
     |
  Interface  webapp/ + templates/   afficher
```

**Chaque étage ne connaît que le précédent.** Le module d'explication ne sait pas
qu'il existe un réseau : il reçoit des dictionnaires et écrit des phrases. C'est ce
découpage qui rend le projet testable module par module et explicable ligne par ligne.

### Les deux modes

| | Mode local (`CAPTURE_LOCALE=1`) | Mode en ligne |
|---|---|---|
| Où | votre machine | un serveur distant |
| Capture | possible | **impossible** — pas de carte réseau |
| Source des données | le tampon de capture | la dernière capture enregistrée dans Supabase |
| Usage | observer son propre réseau | consulter ce qui a été observé ailleurs |

### Technologies

| Bibliothèque | Rôle |
|---|---|
| **Scapy** | ouvrir une interface réseau et décoder les paquets (Ethernet, IP, TCP, UDP, DNS) |
| **Flask** | servir les pages web et recevoir les actions |
| **Jinja2** | remplir les gabarits HTML (fourni avec Flask) |
| **requests** | appeler l'API externe et l'API REST Supabase |
| **python-dotenv** | lire les secrets depuis un fichier `.env` non versionné |
| **pytest** | exécuter les tests |

Versions exactes dans `requirements.txt`.

---

## 7. Structure du projet

```
.
├── app.py                  point d'entree : cree l'application Flask
├── config.py               lit les variables d'environnement, choisit le mode
├── demarrer-analyseur.bat  lancement en local en un clic
├── requirements.txt        dependances et versions exactes
├── .env.example            modele des variables (versionne)
├── capture/                interfaces.py, moteur.py
├── analyse/                paquet.py — un paquet brut -> des champs nommes
├── communications/         regroupement.py — paquets -> communications
├── detection/              les regles d'alerte
├── enrichissement/         identification des adresses distantes
├── explication/            production des phrases (+ adaptateur.py)
├── stockage/               supabase.py — lire et ecrire (API REST)
├── sql/                    schema.sql, a-coller.sql (creation des tables)
├── webapp/                 routes.py, rendu.py
├── templates/              gabarits HTML
├── static/style.css        feuille de style unique
├── api/index.py            point d'entree pour l'hebergeur
├── tools/                  scripts de verification et de diagnostic
├── tests/                  tests unitaires (105)
└── documentation/          explications du code, un .txt par domaine
```

### Routes exposées

| Route | Méthode | Rôle |
|---|---|---|
| `/` | GET | tableau de bord : chiffres essentiels et dernières communications |
| `/communications` | GET | liste des communications observées |
| `/communication/<clé>` | GET | détail d'une communication |
| `/capture` | GET | choisir une carte réseau, démarrer, arrêter |
| `/capture/demarrer` | POST | démarrer une capture sur l'interface choisie |
| `/capture/arreter` | POST | arrêter la capture |
| `/capture/vider` | POST | vider la liste des paquets conservés |
| `/capture/enregistrer` | POST | enregistrer la capture et ses communications |
| `/historique` | GET | captures enregistrées dans Supabase |
| `/historique/<id>` | GET | détail d'une capture enregistrée |
| `/historique/<id>/communication/<clé>` | GET | détail d'une communication enregistrée |
| `/alertes` | GET | alertes produites par les règles |
| `/protocoles` | GET | ce que le programme sait des protocoles et des ports |
| `/glossaire` | GET | définition du vocabulaire employé |
| `/health` | GET | état du service, en JSON |

`/protocoles` et `/glossaire` existent pour une raison : **rien dans l'application ne
doit reposer sur une connaissance cachée**. Ce que le programme affirme, l'utilisateur
peut le lire et le contester.

---

## 8. La détection et l'enrichissement

Six règles examinent l'ensemble des communications et produisent des **alertes**.
Elles ne disent jamais « c'est une attaque » : chacune énonce ce qu'elle a observé,
ce qu'elle en déduit, et ce qu'il faudrait vérifier.

| Règle | Ce qu'elle repère |
|---|---|
| `refus-repetes` | plusieurs connexions refusées — recherche de services, ou logiciel qui réessaie |
| `service-en-clair` | Telnet, FTP, HTTP : le contenu circule sans chiffrement |
| `connexions-repetees` | une même destination contactée par des échanges brefs et réguliers |
| `destinations-multiples` | une machine locale échange avec un grand nombre de serveurs |
| `volume-concentre` | une seule communication transporte la majeure partie du volume |
| `service-non-identifie` | un port inconnu, avec un échange soutenu |

Trois gravités : **information**, **attention**, **vigilance**. Les alertes sont
enregistrées avec la capture, pour la même raison que les résumés.

> Une règle qui échoue est ignorée, les autres continuent. Une alerte manquante est
> fâcheuse ; un plantage qui masque tout l'est davantage.

L'**enrichissement** identifie les adresses distantes par **ip-api.com**, qui ne
demande aucune clé : les adresses locales et de multidiffusion ne sont pas interrogées
(une adresse `192.168.x.x` n'appartient à aucun pays), les adresses sont interrogées en
lot (cent par requête), et seules les réponses obtenues sont mises en cache.
L'enrichissement est un **confort**, jamais une dépendance : s'il échoue, l'analyse
reste complète, sans pays ni opérateur.

---

## 9. La base de données Supabase

L'application écrit dans **Supabase** par son API REST. **Sans clé à privilèges
élevés, tout le reste fonctionne** — capture, communications, tableau de bord. Seuls
l'enregistrement et l'historique réclament la base.

Mise en place, une seule fois :

1. **Créer la clé.** Supabase → projet → **Settings → API Keys** → **Secret keys** →
   **Create new secret key**. Elle ne s'affiche qu'une fois.
   *(Variante : la clé historique `service_role`, section « Legacy API keys ».)*
2. **La renseigner** dans `.env` : `SUPABASE_SECRET_KEY=…` ou
   `SUPABASE_SERVICE_ROLE_KEY=…`.
3. **Créer les tables.** SQL Editor → coller `sql/a-coller.sql` → **Run**. La version
   commentée, qui justifie chaque table, est dans `sql/schema.sql`.
4. **Vérifier.** `python tools/verifier_ecriture_supabase.py` — écrit, relit, supprime,
   et contrôle l'effacement en cascade. Les données d'essai sont retirées.

À savoir : le plan gratuit **met un projet en pause après sept jours sans activité**,
et le domaine cesse alors de répondre ; `python tools/etat_supabase.py` indique l'état.

Installation locale complète :

```bash
git clone https://github.com/tad-code/packet-analyzer.git
cd packet-analyzer
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # puis renseigner les valeurs Supabase
demarrer-analyseur.bat
```

---

## 10. Gestion des erreurs

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

## 11. Limites connues

**Le contenu des communications chiffrées n'est pas lisible.** C'est le principe même
du HTTPS. L'outil observe *qui* parle à *qui*, sur *quel port*, *combien* de données et
*pendant* combien de temps — jamais le contenu.

**Les paquets conservés sont limités** aux 500 derniers (valeur réglable via
`TAILLE_TAMPON`). Une capture longue produit plus de paquets que nécessaire à
l'affichage ; les plus anciens sont oubliés de l'affichage, mais ils restent comptés.

**Le DNS peut passer inaperçu** si la machine a déjà la réponse en cache : aucune
requête n'est alors émise.

**L'outil ne capture pas sur les autres machines du réseau.** Seul le trafic visible
depuis cette carte réseau est observé.

---

## 12. Usage responsable

Cet outil ne doit être utilisé que sur un réseau sur lequel vous êtes autorisé à
travailler : le vôtre, celui de votre organisation avec son accord, ou un
environnement d'entraînement prévu à cet effet.

Le dépôt ne contient pas de fichier de licence : le code est fourni pour la
démonstration et la consultation.

---

## Où sont les explications du code

**Le code ne contient aucun commentaire.** Les explications sont rassemblées dans le
dossier `documentation/`, un fichier `.txt` par domaine :

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

Chaque fichier décrit, dans l'ordre : le rôle du module, puis celui de chaque fonction.
Le document suit la structure du code, ce qui permet de le lire en parallèle.

Des captures d'écran réelles de l'application sont dans `docs/` (générées par
`tools/capturer_interface.py`).
