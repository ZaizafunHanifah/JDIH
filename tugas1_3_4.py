import os, sys, re
sys.path.insert(0, '.')
import psycopg2
from psycopg2.extras import RealDictCursor
c = psycopg2.connect(host='localhost', port=5432, dbname='jdih',
                     user='postgres', password=os.environ['DB_PASSWORD'],
                     cursor_factory=RealDictCursor)
cur = c.cursor()

print('=== TASK 1: TOTAL KARAKTER konten_text_asli ===')
cur.execute("SELECT SUM(LENGTH(konten_text_asli)) AS total FROM documents WHERE konten_text_asli IS NOT NULL")
r = cur.fetchone()
print(f"SUM(LENGTH(konten_text_asli)) = {r['total']:,} karakter")

print()
print('=== TASK 3: CEK KATA KTP / KEPENDUDUKAN ===')
kata_list = ['KTP', 'kartu tanda penduduk', 'kependudukan', 'administrasi kependudukan']
for kata in kata_list:
    cur.execute("SELECT COUNT(*) AS jml FROM documents WHERE konten_text_asli ILIKE %s", (f'%{kata}%',))
    rr = cur.fetchone()
    print(f"  '{kata}': {rr['jml']} dokumen")

print()
print('=== TASK 4: TOP 10 tsquery "syarat izin usaha" ===')
keywords = ['syarat', 'izin', 'usaha']
tsq = 'syarat & (izin | perizinan) & usaha'
cur.execute("""
    SELECT id, judul, nomor, tanggal_terbit, jenis_dokumen,
           ts_rank(konten_tsv, to_tsquery('simple', %s)) AS rank
    FROM documents
    WHERE konten_tsv @@ to_tsquery('simple', %s)
    ORDER BY rank DESC
    LIMIT 10
""", (tsq, tsq))
rows = cur.fetchall()
print(f"tsquery: {tsq}")
print(f"Jumlah kandidat: {len(rows)}")
for rr in rows:
    print(f"  ID {rr['id']} rank={rr['rank']:.4f} | {rr['nomor']} | {rr['judul'][:80]}")

# Cari posisi 1164
cur.execute("""
    SELECT id, judul, nomor, ts_rank(konten_tsv, to_tsquery('simple', %s)) AS rank
    FROM documents
    WHERE konten_tsv @@ to_tsquery('simple', %s) AND id = 1164
""", (tsq, tsq))
r1164 = cur.fetchone()
print(f"\nID 1164 dalam hasil tsquery: {'YA rank='+str(r1164['rank']) if r1164 else 'TIDAK'}")

c.close()
