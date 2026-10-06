

import os
import re
from pathlib import Path

import psycopg

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = RACINE / "sql" / "a-coller.sql"

url = os.getenv("VERIF_PG_URL") or None
if url:
    print("  adresse fournie par la variable VERIF_PG_URL")

if not url:
    print("  Aucune adresse de base fournie : la verification est ignoree.")
    print()
    print("  Pour l'executer, indiquer un serveur PostgreSQL jetable :")
    print("      VERIF_PG_URL=postgresql://utilisateur@127.0.0.1:5432/postgres")
    print("      python tools/verifier_schema_sql.py")
    print()
    print("  Le script cree une base temporaire, y execute sql/a-coller.sql,")
    print("  controle le resultat, puis supprime la base. Rien n'est laisse.")
    raise SystemExit(0)

montrable = re.sub(r"://[^@]+@", "://***:***@", url)
print(f"  adresse : {montrable}")

url_serveur = url.rsplit("/", 1)[0] + "/postgres"
nom_base = "verif_schema_reseau"

sql = SCRIPT.read_text(encoding="utf-8")
print()
print("=" * 74)
print("  VERIFICATION DU SCRIPT SQL")
print("=" * 74)
print()

try:
    with psycopg.connect(url_serveur, autocommit=True, connect_timeout=10) as cx:
        print("  connexion au serveur local : OK")

        with cx.cursor() as cur:
            cur.execute(f'drop database if exists "{nom_base}"')
            cur.execute(f'create database "{nom_base}"')
        print(f"  base jetable « {nom_base} » creee")

        with psycopg.connect(url.rsplit("/", 1)[0] + "/" + nom_base) as base:
            with base.cursor() as cur:
                cur.execute(sql)
                print("  script execute : AUCUNE ERREUR")

            base.commit()

            with base.cursor() as cur:
                cur.execute("""
                    select tablename from pg_tables
                    where schemaname = 'public' and tablename like 'reseau_%'
                    order by tablename
                """)
                tables = [r[0] for r in cur.fetchall()]
            print(f"  tables creees : {tables}")

            with base.cursor() as cur:
                cur.execute("""
                    select tablename, rowsecurity from pg_tables
                    where schemaname = 'public' and tablename like 'reseau_%'
                    order by tablename
                """)
                etats = cur.fetchall()
            print("  securite par ligne :")
            for nom, actif in etats:
                marque = "ACTIVEE" if actif else "*** DESACTIVEE ***"
                print(f"      {nom:26s} {marque}")

            with base.cursor() as cur:
                cur.execute("""
                    select indexname from pg_indexes
                    where schemaname = 'public' and indexname like 'idx_%'
                    order by indexname
                """)
                index = [r[0] for r in cur.fetchall()]
            print(f"  index crees : {index}")

            with base.cursor() as cur:
                cur.execute("""
                    insert into reseau_analyses (interface, nb_paquets)
                    values ('Wi-Fi', 12) returning id
                """)
                analyse = cur.fetchone()[0]
                cur.execute("""
                    insert into reseau_communications
                        (analyse_id, cle, ip_premiere, port_premiere, protocole)
                    values (%s, 'cle-test', '192.168.1.6', 443, 'TCP')
                """, (analyse,))
                cur.execute("select count(*) from reseau_communications")
                nb = cur.fetchone()[0]
            print(f"  ecriture reelle    : 1 analyse + {nb} communication = OK")

            with base.cursor() as cur:
                cur.execute("delete from reseau_analyses where id = %s", (analyse,))
                cur.execute("select count(*) from reseau_communications")
                reste = cur.fetchone()[0]
            print(f"  cascade            : {reste} communication restante apres "
                  f"suppression de l'analyse {'= OK' if reste == 0 else '= PROBLEME'}")

            with base.cursor() as cur:
                try:
                    cur.execute("insert into reseau_analyses (etat) values ('nimporte quoi')")
                    print("  contrainte etat    : *** NON APPLIQUEE ***")
                except psycopg.errors.CheckViolation:
                    print("  contrainte etat    : refuse bien une valeur invalide = OK")
                base.rollback()

            base.commit()

    with psycopg.connect(url_serveur, autocommit=True) as cx:
        with cx.cursor() as cur:
            cur.execute(f'drop database if exists "{nom_base}"')
    print()
    print("  base jetable supprimee : rien n'a ete laisse derriere")

except psycopg.OperationalError as e:
    print(f"  serveur local injoignable : {e}")
    print("  (la verification n'a pas pu etre faite ici)")
except psycopg.errors.Error as e:
    print(f"  ERREUR SQL : {type(e).__name__} — {e}")
