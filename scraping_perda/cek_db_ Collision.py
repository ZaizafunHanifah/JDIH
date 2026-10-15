"""Cek risiko bentrok identifier antara Perbup dan Perda di jdih.db."""
import os
import sqlite3
import sys

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jdih.db")
print("db:", DB, "| ada?", os.path.exists(DB))
if not os.path.exists(DB):
    sys.exit(0)

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print()
print("Tabel:", [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'").fetchall()])

cols = [r[1] for r in conn.execute("PRAGMA table_info(documents)").fetchall()]
print("kolom documents:", cols)

n = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
print("total dokumen:", n)
print()
print("dokumen per jenis_dokumen:")
for r in conn.execute(
        "SELECT jenis_dokumen, COUNT(*) c FROM documents GROUP BY jenis_dokumen"):
    print(f"   {r[0]}: {r[1]}")
print()
print("status_hukum / catatan_relasi sudah ada di tabel?",
      "status_hukum" in cols, "catatan_relasi" in cols)
print()
#模拟 bentrok: nomor+tahun yang akan dipakai Perda
print("Contoh bentrok potensial (nomor+tahun sama dengan Perbup):")
rows = conn.execute(
    "SELECT nomor, substr(tanggal_terbit,1,4) th, jenis_dokumen, judul "
    "FROM documents WHERE jenis_dokumen='Peraturan Bupati' LIMIT 5").fetchall()
for r in rows:
    print(f"   {r[0]}_{r[1]}  [{r[2]}]  {r[3][:60]}")
conn.close()
