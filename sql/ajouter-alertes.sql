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
