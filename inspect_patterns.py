import os, re, sys
sys.path.insert(0, '.')
import psycopg2
from psycopg2.extras import RealDictCursor

c = psycopg2.connect(host="localhost", port=5432, dbname="jdih", user="postgres", password=os.getenv("DB_PASSWORD"), cursor_factory=RealDictCursor)
cur = c.cursor()
cur.execute("SELECT id, konten_text_asli FROM documents WHERE konten_text_asli IS NOT NULL LIMIT 3")
for r in cur.fetchall():
    text = r["konten_text_asli"]
    for m in re.finditer(r"-\s*\d+\s*-", text):
        s = max(0, m.start()-30); e = min(len(text), m.end()+30)
        print(f"doc {r['id']}: PAGE: ...{text[s:e].replace(chr(10),' ')}...")
        break
    for m in re.finditer(r"JDIH Kabupaten Banyumas", text):
        s = max(0, m.start()-50); e = min(len(text), m.end()+50)
        print(f"doc {r['id']}: JDIH: ...{text[s:e].replace(chr(10),' ')}...")
        break
c.close()
