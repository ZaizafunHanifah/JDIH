import os, sys
sys.path.insert(0, '.')
import psycopg2
from psycopg2.extras import RealDictCursor
c = psycopg2.connect(host='localhost', port=5432, dbname='jdih',
                     user='postgres', password=os.environ['DB_PASSWORD'],
                     cursor_factory=RealDictCursor)
cur = c.cursor()
cur.execute("""SELECT id, nomor, judul FROM documents
               WHERE konten_text_asli ILIKE '%izin usaha%'
                  OR konten_text_asli ILIKE '%perizinan usaha%'
                  OR judul ILIKE '%izin usaha%'
                  OR judul ILIKE '%perizinan usaha%'
               ORDER BY id""")
rows = cur.fetchall()
print(f'Dokumen dengan "izin usaha" atau "perizinan usaha": {len(rows)}')
for r in rows:
    print(f'  ID {r["id"]}: {r["nomor"]} | {r["judul"][:90]}')
c.close()
