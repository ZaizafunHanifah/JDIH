import os, sys, re
os.environ["DB_PASSWORD"] = "123"
sys.path.insert(0, ".")
import psycopg2
from psycopg2.extras import RealDictCursor

c = psycopg2.connect(host="localhost", port=5432, dbname="jdih", user="postgres", password=os.getenv("DB_PASSWORD"), cursor_factory=RealDictCursor)
cur = c.cursor()
cur.execute("SELECT id, judul, konten_text_asli FROM documents WHERE konten_text_asli IS NOT NULL")
rows = cur.fetchall()

# Cari pola footer berulang di seluruh dokumen
footer_candidates = {}
page_num_pattern = re.compile(r"-\s*\d+\s*-", re.IGNORECASE)
jidih_pattern = re.compile(r"JDIH\s+Kabupaten\s+Banyumas", re.IGNORECASE)

for r in rows:
    text = r["konten_text_asli"] or ""
    for m in jidih_pattern.finditer(text):
        footer_candidates.setdefault("JDIH Kabupaten Banyumas", 0)
        footer_candidates["JDIH Kabupaten Banyumas"] += 1
    for m in page_num_pattern.finditer(text):
        footer_candidates.setdefault("halaman -N-", 0)
        footer_candidates["halaman -N-"] += 1

print("=== Pola footer terdeteksi di seluruh 469 dokumen ===")
for k, v in sorted(footer_candidates.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v} kemunculan")

# Lihat contoh konteks footer di doc 888
cur.execute("SELECT konten_text_asli FROM documents WHERE id=888")
text = cur.fetchone()["konten_text_asli"]
print("\n=== Konteks footer di doc 888 ===")
for m in jidih_pattern.finditer(text):
    s = max(0, m.start()-80)
    e = min(len(text), m.end()+80)
    print(repr(text[s:e]))
    print("---")
for m in page_num_pattern.finditer(text):
    s = max(0, m.start()-40)
    e = min(len(text), m.end()+40)
    print("PAGE:", repr(text[s:e]))

cur.close(); c.close()