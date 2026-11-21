# creates the tables and loads the csv files into postgres
# run from the project folder: python src/data_load.py
import psycopg2

conn = psycopg2.connect(dbname="credit_risk")
cur = conn.cursor()

cur.execute(open("sql/schema.sql").read())

for table in ["customers", "credit_history", "loan_applications", "transactions"]:
    with open(f"datasets/{table}.csv") as f:
        cur.copy_expert(f"COPY {table} FROM STDIN WITH CSV HEADER", f)
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    print(table, cur.fetchone()[0])

conn.commit()
conn.close()
