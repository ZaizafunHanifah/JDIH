import os, sys
sys.path.insert(0, ".")
import psycopg2
from psycopg2.extras import RealDictCursor
from app.pasal_extractor import extract_pasal, potong_penjelasan

c = psycopg2.connect(host="localhost", port=5432, dbname="jdih", user="postgres", password=os.getenv("DB_PASSWORD"), cursor_factory=RealDictCursor)
cur = c.cursor()
cur.execute("SELECT konten_text_asli FROM documents WHERE id=888")
text = cur.fetchone()["konten_text_asli"]
cleaned = potong_penjelasan(text)
pasals = extract_pasal(cleaned)
print("Total pasal:", len(pasals))
for p in pasals:
    if p["nomor_pasal"] in (11, 19, 29):
        print(f"--- Pasal {p['nomor_pasal']} (after clean) ---")
        print(p["isi_penuh"][:200].replace(chr(10), " "))
        print()
c.close()
