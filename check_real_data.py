import sqlite3

conn = sqlite3.connect("jdih.db")

print("=== Total dokumen ===")
print(conn.execute("SELECT COUNT(*) FROM documents").fetchone())

print()
print("=== Distribusi per topik ===")
for r in conn.execute("""
    SELECT topics.label_topik, COUNT(*) 
    FROM document_topics 
    JOIN topics ON document_topics.topic_id = topics.id 
    GROUP BY topics.label_topik 
    ORDER BY COUNT(*) DESC
"""):
    print(r)

print()
print("=== Dokumen tanpa topik sama sekali ===")
print(conn.execute("""
    SELECT COUNT(*) FROM documents 
    WHERE id NOT IN (SELECT document_id FROM document_topics)
""").fetchone())

print()
print("=== Contoh 3 dokumen ASLI (cek judul asli, bukan karangan) ===")
for r in conn.execute("SELECT judul, nomor, tanggal_terbit FROM documents LIMIT 3"):
    print(r)

print()
print("=== Cek konten_text tidak semua kosong ===")
print(conn.execute("SELECT COUNT(*) FROM documents WHERE konten_text = '' OR konten_text IS NULL").fetchone())
print(conn.execute("SELECT COUNT(*) FROM documents WHERE LENGTH(konten_text) > 0").fetchone())

print()
print("=== Cek jenis_dokumen ===")
for r in conn.execute("SELECT jenis_dokumen, COUNT(*) FROM documents GROUP BY jenis_dokumen"):
    print(r)

conn.close()