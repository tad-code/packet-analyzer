
create table if not exists reseau_alertes (
    id                bigint generated always as identity primary key,

    analyse_id        bigint not null
                      references reseau_analyses (id) on delete cascade,

    regle             text not null,

    gravite           text not null,

    titre             text not null,
    explication       text,

    base              text,

    conseil           text,

    nb_communications integer not null default 0,

    constraint gravite_alerte_valide
        check (gravite in ('information', 'attention', 'vigilance'))
);

create index if not exists idx_alertes_analyse
    on reseau_alertes (analyse_id);

alter table reseau_alertes enable row level security;


