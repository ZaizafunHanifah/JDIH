import psycopg2, os
c = psycopg2.connect(host='localhost', port=5432, dbname='jdih', user='postgres', password=os.environ['DB_PASSWORD'])
cur = c.cursor()
print('=== attstorage untuk kolom documents ===')
cur.execute("""
SELECT attname, attstorage
FROM pg_attribute
WHERE attrelid = 'documents'::regclass
  AND attname IN ('judul','konten_text','konten_text_asli','konten_tsv')
ORDER BY attname;
""")
for r in cur.fetchall():
    print(f"  {r[0]}: attstorage={r[1]}")
print()
print('=== reltoastrelid untuk tabel documents ===')
cur.execute("SELECT relname, reltoastrelid FROM pg_class WHERE relname = 'documents'")
for r in cur.fetchall():
    print(f"  tabel={r[0]}, reltoastrelid={r[1]}")
print("(reltoastrelid != 0 berarti tabel punya TOAST table)")
c.close()
