import os, datetime
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host="localhost", port=5432, dbname="jdih", user="postgres", password=os.getenv("DB_PASSWORD"), cursor_factory=RealDictCursor)
cur = conn.cursor()

tables = ["documents", "topics", "document_topics"]
date = datetime.date.today().strftime("%Y%m%d")
fname = f"jdih_pg_backup_{date}.sql"
with open(fname, "w", encoding="utf-8") as f:
    for t in tables:
        cur.execute(f"SELECT * FROM {t}")
        rows = cur.fetchall()
        cols = [d.name for d in cur.description]
        f.write(f"-- Table {t}\n")
        for r in rows:
            vals = []
            for c in cols:
                v = r[c]
                if v is None:
                    vals.append("NULL")
                elif isinstance(v, str):
                    vals.append("'" + v.replace("'", "''") + "'")
                else:
                    vals.append(str(v))
            f.write(f"INSERT INTO {t} ({','.join(cols)}) VALUES ({','.join(vals)});\n")
        f.write("\n")

print("backup:", fname, os.path.getsize(fname), "bytes")
cur.close(); conn.close()