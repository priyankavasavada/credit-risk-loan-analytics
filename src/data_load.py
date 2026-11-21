"""Create the tables and load the CSVs into Postgres.

Usage: python src/data_load.py
Connection string can be changed with the DATABASE_URL env variable.
"""
import os
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "datasets"
DB_URL = os.getenv("DATABASE_URL", "dbname=credit_risk")

# parents first so the foreign keys work
TABLES = ["customers", "credit_history", "loan_applications", "transactions"]


def get_conn():
    return psycopg2.connect(DB_URL)


def create_tables(conn):
    with conn.cursor() as cur:
        cur.execute((ROOT / "sql" / "schema.sql").read_text())


def load_csvs(conn):
    with conn.cursor() as cur:
        for table in TABLES:
            with open(DATA_DIR / f"{table}.csv") as f:
                cur.copy_expert(f"COPY {table} FROM STDIN WITH CSV HEADER", f)
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            print(f"{table}: {cur.fetchone()[0]} rows")


def check_orphans(conn):
    with conn.cursor() as cur:
        for table in TABLES[1:]:
            cur.execute(f"""
                SELECT COUNT(*) FROM {table} t
                LEFT JOIN customers c ON c.customer_id = t.customer_id
                WHERE c.customer_id IS NULL
            """)
            print(f"orphan rows in {table}: {cur.fetchone()[0]}")


if __name__ == "__main__":
    conn = get_conn()
    with conn:
        create_tables(conn)
        load_csvs(conn)
        check_orphans(conn)
    conn.close()
