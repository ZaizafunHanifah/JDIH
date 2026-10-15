"""Uji logika pengaman pada berbagai kondisi DB, tanpa menyentuh jdih.db.
Memakai SQL guard yang sama persis dengan import_real_data.py / seed.py.
"""
import sqlite3, sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GUARD = ("SELECT jenis_dokumen, COUNT(*) FROM documents "
         "WHERE jenis_dokumen IS NULL OR jenis_dokumen <> ? GROUP BY jenis_dokumen")

def cek(kondisi, isi):
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE documents (jenis_dokumen TEXT)")
    c.executemany("INSERT INTO documents VALUES (?)", isi)
    bocor = c.execute(GUARD, ("Peraturan Bupati",)).fetchall()
    return bool(bocor), bocor

KASUS = [
    ("DB kosong", []),
    ("hanya Perbup", [("Peraturan Bupati",)] * 386),
    ("Perbup + Perda", [("Peraturan Bupati",)] * 386 + [("Peraturan Daerah",)] * 83),
    ("ada NULL jenis", [("Peraturan Bupati",)] * 386 + [(None,)]),
    ("hanya Perda", [("Peraturan Daerah",)] * 83),
    ("jenis tak dikenal", [("Peraturan Bupati",)] * 10 + [("Surat Keputusan",)] * 5),
]

print(f"{'kondisi':<22}{'diblokir?':<12}detail")
print("-" * 78)
for nama, isi in KASUS:
    diblokir, detail = cek(nama, isi)
    expect = "YA" if diblokir else "TIDAK"
    ket = ", ".join(f"{j or 'NULL'}={n}" for j, n in detail) or "-"
    print(f"{nama:<22}{expect:<12}{ket}")

print()
print("Penjelasan: DB kosong dan 'hanya Perbup' harus TIDAK diblokir,")
print("supaya kedua script tetap bisa dipakai pada DB baru / DB Perbup saja.")
