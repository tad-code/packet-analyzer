-- Cloisonnement des donnees par utilisateur.
--
-- A executer UNE FOIS dans l'editeur SQL de Supabase (base existante).
-- Le script est sans danger : il ne supprime aucune donnee. Il ajoute une
-- colonne de proprietaire, puis des politiques de securite par ligne (RLS)
-- qui font que la base elle-meme refuse de servir la capture d'un autre
-- compte, meme si une requete mal ecrite oubliait le filtre.
--
-- Apres l'execution, attribuer les captures deja enregistrees au compte de
-- demonstration :
--     update reseau_analyses set proprietaire_id = '<identifiant du compte>'
--      where proprietaire_id is null;
-- Le script tools/mettre_en_place_comptes.py fait cette attribution.

alter table reseau_analyses
    add column if not exists proprietaire_id uuid;

create index if not exists idx_analyses_proprietaire
    on reseau_analyses (proprietaire_id);

alter table reseau_analyses       enable row level security;
alter table reseau_communications enable row level security;
alter table reseau_alertes        enable row level security;

drop policy if exists analyses_proprietaire on reseau_analyses;
create policy analyses_proprietaire on reseau_analyses
    for all
    to authenticated
    using (proprietaire_id = auth.uid())
    with check (proprietaire_id = auth.uid());

drop policy if exists communications_proprietaire on reseau_communications;
create policy communications_proprietaire on reseau_communications
    for all
    to authenticated
    using (exists (
        select 1 from reseau_analyses a
         where a.id = reseau_communications.analyse_id
           and a.proprietaire_id = auth.uid()))
    with check (exists (
        select 1 from reseau_analyses a
         where a.id = reseau_communications.analyse_id
           and a.proprietaire_id = auth.uid()));

drop policy if exists alertes_proprietaire on reseau_alertes;
create policy alertes_proprietaire on reseau_alertes
    for all
    to authenticated
    using (exists (
        select 1 from reseau_analyses a
         where a.id = reseau_alertes.analyse_id
           and a.proprietaire_id = auth.uid()))
    with check (exists (
        select 1 from reseau_analyses a
         where a.id = reseau_alertes.analyse_id
           and a.proprietaire_id = auth.uid()));

grant select on reseau_analyses, reseau_communications, reseau_alertes
    to authenticated;
