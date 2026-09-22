import sqlite3

conn = sqlite3.connect("jdih.db")

print("=== Surat Keputusan (3 contoh) ===")
for r in conn.execute("SELECT judul, nomor FROM documents WHERE jenis_dokumen = 'Surat Keputusan' LIMIT 3"):
    print(r)

print()
print("=== Peraturan Desa (3 contoh) ===")
for r in conn.execute("SELECT judul, nomor FROM documents WHERE jenis_dokumen = 'Peraturan Desa' LIMIT 3"):
    print(r)

conn.close()