"""
Verifikasi PASCA-IMPORT: query langsung ke jdih.db, bukancrivait output skrip.
Jalankan: python verifikasi_import.py
"""
import collections
import os
import re
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DB = os.path.join(ROOT, "jdih.db")
sys.path.insert(0, ROOT)
from import_real_data import TOPICS  # noqa: E402

# hasil simulasi sebelumnya (harus cocok)
EKSPEKTASI = {
    "Organisasi dan Tata Kerja Perangkat Daerah": 73,
    "Standar Biaya dan Honorarium": 20,
    "Pengadaan Barang/Jasa": 27,
    "Perencanaan Pembangunan Daerah": 19,
    "Kepegawaian dan Aparatur Sipil Negara": 33,
    "Pajak dan Retribusi Daerah": 41,
    "Pelayanan Kesehatan": 35,
    "Pendidikan": 13,
    "Pertanian dan Lingkungan Hidup": 11,
    "Sosial dan Kemasyarakatan": 39,
}
EKSPEKTASI_TER_TAG = 247
SPOT = ["45_2020", "20_2021", "8_2020"]
EKSPEKTASI_SPOT = {
    "45_2020": {"Pelayanan Kesehatan", "Sosial dan Kemasyarakatan"},
    "20_2021": {"Pengadaan Barang/Jasa", "Pertanian dan Lingkungan Hidup"},
    "8_2020": {"Pajak dan Retribusi Daerah"},
}

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
ok_semua = True

# ---------- 1 ----------
print("=" * 78)
print("1. TOTAL DOKUMEN")
print("=" * 78)
total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
perbup = conn.execute(
    "SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Replies'".replace(
        "Replies", "Bupati")).fetchone()[0]
per_jenis = dict(conn.execute(
    "SELECT jenis_dokumen, COUNT(*) FROM documents GROUP BY jenis_dokumen").fetchall())
n_topik = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
n_rel = conn.execute("SELECT COUNT(*) FROM document_topics").fetchone()[0]
print(f"  total documents           : {total}   (harus 386) "
      f"{'OK' if total == 386 else 'GAGAL'}")
print(f"  jenis_dokumen='Peraturan Bupati': {perbup} "
      f"{'OK' if perbup == 386 else 'GAGAL'}")
print(f"  jumlah jenis_dokumen      : {per_jenis}")
print(f"  jumlah topics             : {n_topik}")
print(f"  jumlah relasi doc-topics  : {n_rel}   (harus 311) "
      f"{'OK' if n_rel == 311 else 'GAGAL'}")
ok_semua &= (total == 386 and perbup == 386 and n_rel == 311)

# ---------- 2 ----------
print()
print("=" * 78)
print("2. DOKUMEN DENGAN MINIMAL 1 TOPIK")
print("=" * 78)
tert = conn.execute("""
    SELECT COUNT(*) FROM (
        SELECT document_id FROM document_topics GROUP BY document_id
    )
""").fetchone()[0]
print(f"  dokumen dengan >=1 topik : {tert}   (harus {EKSPEKTASI_TER_TAG}) "
      f"{'OK' if tert == EKSPEKTASI_TER_TAG else 'GAGAL'}")
print(f"  dokumen tanpa topik      : {total - tert}   (harus 139) "
      f"{'OK' if total - tert == 139 else 'GAGAL'}")
ok_semua &= (tert == EKSPEKTASI_TER_TAG)

# ---------- 3 ----------
print()
print("=" * 78)
print("3. DISTRIBUSI 10 KATEGORI (bandingkan dengan simulasi)")
print("=" * 78)
hasil = dict(conn.execute("""
    SELECT t.label_topik, COUNT(*) FROM document_topics dt
    JOIN topics t ON t.id = dt.topic_id GROUP BY t.label_topik
""").fetchall())
print(f"{'kategori':<46}{'DB':>5}{'simulasi':>10}{'selisih':>9}")
print("-" * 70)
for kat, exp in EKSPEKTASI.items():
    got = hasil.get(kat, 0)
    sel = got - exp
    print(f"{kat:<46}{got:>5}{exp:>10}{sel:>9}"
          f"{'   OK' if sel == 0 else '   GAGAL'}")
    if sel != 0:
        ok_semua = False
print("-" * 70)
print(f"{'TOTAL':<46}{sum(hasil.values()):>5}{sum(EKSPEKTASI.values()):>10}")
# kategori di DB yang tidak diharapkan
ekstra = set(hasil) - set(EKSPEKTASI)
if ekstra:
    print("KATEGORI TAMBAHAN YANG TIDAK DIHARAPKAN:", ekstra)
    ok_semua = False

# ---------- 4 ----------
print()
print("=" * 78)
print("4. SPOT CHECK 3 DOKUMEN DARI DAFTAR '24 BERUBAH'")
print("=" * 78)
for nt in SPOT:
    nomor, tahun = nt.split("_")
    row = conn.execute("""
        SELECT d.judul, GROUP_CONCAT(t.label_topik, '||') AS kat
        FROM documents d
        LEFT JOIN document_topics dt ON dt.document_id = d.id
        LEFT JOIN topics t ON t.id = dt.topic_id
        WHERE trim(d.nomor) = ? AND substr(d.tanggal_terbit,1,4) = ?
        GROUP BY d.id
    """, (nomor, tahun)).fetchone()
    if row is None:
        print(f"  [{nt}] TIDAK DITEMUKAN")
        ok_semua = False
        continue
    dapat = set((row["kat"] or "").split("||")) - {""}
    exp = EKSPEKTASI_SPOT[nt]
    cocok = (dapat == exp)
    print(f"\n  [{nt}] {'COCOK' if cocok else 'TIDAK COCOK'}")
    print(f"     judul     : {row['judul'].strip()[:74]}")
    print(f"     di DB     : {sorted(dapat)}")
    print(f"     simulasi  : {sorted(exp)}")
    if not cocok:
        print(f"     bisa      : {sorted(dapat ^ exp)}")
        ok_semua = False

# ---------- 5. integrasi tambahan ----------
print()
print("=" * 78)
print("5. PEMERIKSAAN TAMBAHAN")
print("=" * 78)
# FTS5 terisi?
fts = conn.execute("SELECT COUNT(*) FROM documents_fts").fetchone()[0]
print(f"  baris di documents_fts : {fts}")
#FTS bisa cari kata yang dulu false positive?
for uji in ["persampahan", "bangunan gedung", "air minum", "penyakit"]:
    n = conn.execute(
        "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH ?",
        (f'"{uji}"',)).fetchone()[0]
    print(f"  FTS5 cari \"{uji}\" : {n} dokumen")

# apakah ada dokumen dengan topik duplikat
dup = conn.execute("""
    SELECT COUNT(*) FROM (
        SELECT document_id, topic_id, COUNT(*) c
        FROM document_topics GROUP BY document_id, topic_id HAVING c > 1
    )
""").fetchone()[0]
print(f"  relasi doc-topic duplikat : {dup} (harus 0)")

# semua label topic di DB harus ada di TOPICS
label_db = {r[0] for r in conn.execute("SELECT label_topik FROM topics")}
print(f"  label di DB semua dikenal : {label_db == set(TOPICS)}")
if label_db != set(TOPICS):
    print("    selisih:", label_db ^ set(TOPICS))
    ok_semua = False

conn.close()
print()
print("=" * 78)
print("RINGKASAN VERIFIKASI")
print("=" * 78)
print("  SEMUA CEK LULUS" if ok_semua else "  ADA YANG GAGAL - periksa baris GAGAL di atas")
