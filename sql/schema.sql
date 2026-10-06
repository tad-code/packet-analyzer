-- ============================================================================
--  Schema de la base Supabase
-- ============================================================================
--
--  A executer une seule fois, dans Supabase : SQL Editor -> New query -> coller
--  -> Run.
--
--  Deux tables pour cette version. Elles portent le prefixe « reseau_ » pour ne
--  pas entrer en collision avec d'autres projets utilisant le meme espace
--  Supabase.
--
--  Pourquoi deux tables, et pas une seule ?
--
--    Une analyse est une session de capture : « la capture de mardi soir,
--    pendant 5 minutes, sur le Wi-Fi ». Une communication est une conversation
--    observee pendant cette capture. Une analyse contient plusieurs
--    communications.
--
--    Les ranger dans une seule table obligerait a repeter les informations de
--    la capture sur chaque ligne, et rendrait impossible la question « que
--    s'est-il passe pendant CETTE capture precise ? ».
--
--  Les tables « alertes » et « enrichissements » viendront avec les versions
--  qui les produisent. On ne cree pas de table vide a l'avance.
-- ============================================================================


-- ----------------------------------------------------------------------------
--  Table des analyses : une session de capture
-- ----------------------------------------------------------------------------
create table if not exists reseau_analyses (
    id              bigint generated always as identity primary key,

    -- Quand la capture a commence et quand elle s'est arretee.
    debut           timestamptz not null default now(),
    fin             timestamptz,

    -- La carte reseau ecoutee. Utile pour interpreter : le trafic du Wi-Fi et
    -- celui d'une carte virtuelle n'ont pas la meme signification.
    interface       text,

    -- Etat de la capture : « en cours » ou « terminee ». Permet de retrouver
    -- une session interrompue.
    etat            text not null default 'en cours',

    -- Compteurs figes a la fin de la capture. Les recalculer plus tard serait
    -- impossible : le tampon de paquets est volontairement limite et oublie les
    -- plus anciens.
    nb_paquets      integer not null default 0,
    nb_communications integer not null default 0,
    octets          bigint not null default 0,

    note            text,

    constraint etat_analyse_valide check (etat in ('en cours', 'terminee'))
);


-- ----------------------------------------------------------------------------
--  Table des communications : une conversation entre deux machines
-- ----------------------------------------------------------------------------
create table if not exists reseau_communications (
    id                  bigint generated always as identity primary key,

    -- Rattachement a la capture qui l'a produite.
    -- « on delete cascade » : supprimer une analyse supprime ses
    -- communications, qui n'ont plus de sens seules.
    analyse_id          bigint not null
                        references reseau_analyses (id) on delete cascade,

    -- La cle de regroupement, telle que calculee par le programme. Elle permet
    -- de reconnaitre la meme communication si on rejoue une analyse.
    cle                 text not null,

    -- Les deux extremites. On conserve l'initiateur separement : savoir qui a
    -- parle en premier est une information d'analyse, pas un detail.
    ip_premiere         text,
    port_premiere       integer,
    ip_seconde          text,
    port_seconde        integer,
    initiateur          text,

    protocole           text,
    port_service        integer,
    service_probable    text,

    nb_paquets          integer not null default 0,
    octets              bigint not null default 0,

    debut               timestamptz,
    fin                 timestamptz,
    duree               double precision,

    etat                text,
    drapeaux_vus        text,

    -- L'explication produite au moment de l'enregistrement.
    --
    -- Pourquoi la stocker, alors qu'elle est recalculable ? Parce que le
    -- vocabulaire et les regles evoluent : sans cela, l'historique changerait
    -- d'aspect a chaque mise a jour du moteur, et l'on ne pourrait plus
    -- comparer une analyse ancienne avec une nouvelle.
    resume              text
);


-- ----------------------------------------------------------------------------
--  Index : ils accelerent les questions que l'interface pose vraiment
-- ----------------------------------------------------------------------------
create index if not exists idx_communications_analyse
    on reseau_communications (analyse_id);
create index if not exists idx_communications_service
    on reseau_communications (port_service);
create index if not exists idx_analyses_debut
    on reseau_analyses (debut desc);


-- ----------------------------------------------------------------------------
--  SECURITE : on ferme tout
-- ----------------------------------------------------------------------------
--
--  On active la securite au niveau des lignes (RLS) SANS creer aucune politique.
--  Consequence : ni la cle publique, ni la cle secrete utilisee depuis un
--  navigateur, ne peuvent lire ou ecrire quoi que ce soit.
--
--  POURQUOI C'EST INDISPENSABLE : si l'on ecrivait une politique
--  « for select using (true) », la base deviendrait lisible — et effacable —
--  par quiconque possede la cle publique. Or cette cle est faite pour etre
--  publiee.
--
--  L'application n'utilise donc jamais la cle publique pour cette base : elle
--  emploie la cle secrete, gardee dans les variables d'environnement du serveur,
--  qui contourne la RLS parce qu'elle a les droits complets.
-- ----------------------------------------------------------------------------
alter table reseau_analyses       enable row level security;
alter table reseau_communications enable row level security;

-- Aucune politique n'est volontairement creee.
-- Pour verifier que la fermeture est effective :
--     select tablename, rowsecurity from pg_tables
--     where tablename like 'reseau_%';
-- Les deux lignes doivent afficher « rowsecurity = true ».


-- ----------------------------------------------------------------------------
--  Verification apres execution
-- ----------------------------------------------------------------------------
--     select count(*) from reseau_analyses;
--     select count(*) from reseau_communications;
--  Les deux requetes doivent repondre 0 sans erreur.


-- ============================================================================
--  Table des alertes
-- ============================================================================
--
--  A executer UNE FOIS, en plus du premier script (sql/a-coller.sql), dans :
--  Supabase -> SQL Editor -> New query -> coller -> Run.
--
--  Les tables « reseau_analyses » et « reseau_communications » existant deja,
--  ce script ne les touche pas : il ajoute seulement celle des alertes.
--
--  POURQUOI CONSERVER LES ALERTES ?
--
--    Une alerte est produite par des regles. Ces regles evolueront : un seuil
--    sera ajuste, une regle ajoutee, une autre retiree. Si l'on recalculait les
--    alertes a l'affichage, l'historique d'hier changerait a chaque mise a jour,
--    et l'on ne pourrait plus comparer deux captures.
--
--    On conserve donc ce que les regles disaient AU MOMENT de la capture, comme
--    pour le resume des communications. C'est la meme decision, pour la meme
--    raison.
-- ============================================================================

create table if not exists reseau_alertes (
    id                bigint generated always as identity primary key,

    -- La capture qui a produit l'alerte. « on delete cascade » : supprimer une
    -- capture supprime ses alertes, qui n'ont plus de sens sans elle.
    analyse_id        bigint not null
                      references reseau_analyses (id) on delete cascade,

    -- L'identifiant de la regle qui a parle (« refus-repetes », etc.).
    -- Il permet de savoir plus tard quelle regle a produit quoi.
    regle             text not null,

    -- « information », « attention » ou « vigilance ».
    gravite           text not null,

    titre             text not null,
    explication       text,

    -- Le fait observe qui a declenche la regle. Sans lui, l'alerte ne serait
    -- pas verifiable — et une alerte invérifiable ne sert a rien.
    base              text,

    conseil           text,

    nb_communications integer not null default 0,

    constraint gravite_alerte_valide
        check (gravite in ('information', 'attention', 'vigilance'))
);

create index if not exists idx_alertes_analyse
    on reseau_alertes (analyse_id);

alter table reseau_alertes enable row level security;

-- Aucune politique n'est volontairement creee : la base reste fermee a la cle
-- publique, comme les deux autres tables.

-- Verification apres execution :
--     select count(*) from reseau_alertes;
-- doit repondre 0 sans erreur.
