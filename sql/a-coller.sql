create table if not exists reseau_analyses (
    id              bigint generated always as identity primary key,
    debut           timestamptz not null default now(),
    fin             timestamptz,
    interface       text,
    etat            text not null default 'en cours',
    nb_paquets      integer not null default 0,
    nb_communications integer not null default 0,
    octets          bigint not null default 0,
    note            text,
    constraint etat_analyse_valide check (etat in ('en cours', 'terminee'))
);
create table if not exists reseau_communications (
    id                  bigint generated always as identity primary key,
    analyse_id          bigint not null
                        references reseau_analyses (id) on delete cascade,
    cle                 text not null,
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
    resume              text
);
create index if not exists idx_communications_analyse
    on reseau_communications (analyse_id);
create index if not exists idx_communications_service
    on reseau_communications (port_service);
create index if not exists idx_analyses_debut
    on reseau_analyses (debut desc);
alter table reseau_analyses       enable row level security;
alter table reseau_communications enable row level security;
