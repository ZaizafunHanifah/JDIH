"""
Verifikasi PASCA-IMPORT PERDA.
Membandingkan 386 Perbup dengan snapshot sebelum import (bukan asumsi).
Jalankan: python scraping_perda/verifikasi_import_perda.py
"""
import collections
import json
import os
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DB = os.path.join(ROOT, "jdih.db")
SNAP = os.path.join(BASE, "snapshot_sebelum_perda.json")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
gagal = []

def cek(nama, gotusar, exp):
    ok = (gotusar == exp)
    if not ok:
        gagal.append(nama)
    print(f"  {nama:<44}{gotusar:>6}   (harus {exp})  {'OK' if ok else 'GAGAL'}")

# ---------- 1 ----------
print("=" * 78)
print("1. TOTAL DOKUMEN & JENIS")
print("=" * 78)
total = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
cek("total dokumen", total, 469)
for jenis, n in conn.execute(
        "SELECT jenis_dokumen, COUNT(*) FROM documents GROUP BY jenis_dokumen "
        "ORDER BY jenis_dokumen").fetchall():
    print(f"    {jenis:<42}{n:>6}")
cek("jumlah jenis_dokumen",
    conn.execute("SELECT COUNT(DISTINCT jenis_dokumen) FROM documents").fetchone()[0], 2)

# ---------- 2. Perbup tidak berubah ----------
print()
print("=" * 78)
print("2. 386 PERBUP TIDAK BERUBAH (vs snapshot sebelum import)")
print("=" * 78)
with open(SNAP, encoding="utf-8") as f:
    snap = json.load(f)
rows = conn.execute("""
    SELECT d.id, d.nomor, d.tanggal_terbit, d.judul, d.jenis_dokumen,
           d.konten_text, d.konten_text_asli, d.url_pdf,
           (SELECT GROUP_CONCAT(t.label_topik, '||') FROM document_topics dt
              JOIN topics t ON t.id=dt.topic_id WHERE dt.document_id=d.id) AS kat
    FROM documents d WHERE d.jenis_dokumen = 'Peraturan Bupati' ORDER BY d.id
""").fetchall()

cek("jumlah Perbup sekarang", len(rows), 386)
cek("jumlah di snapshot", snap["jumlah"], 386)
cek("id tertinggi Perbup",
    max(r["id"] for r in rows), snap["id_tertinggi"])

sekarang = {r["id"]: {
    "nomor": r["nomor"], "tahun": (r["tanggal_terbit"] or "")[:4],
    "judul": r["judul"], "jenis": r["jenis_dokumen"],
    "len_teks": len(r["konten_text"] or ""),
    "len_asli": len(r["konten_text_asli"] or ""),
    "url": r["url_pdf"], "kat": r["kat"] or "",
} for r in rows}
sebelum = {d["id"]: d for d in snap["docs"]}

cek("jumlah id cocok", len(set(sekarang) & set(sebelum)), 386)
beda = []
for i in sorted(set(sekarang) & set(sebelum)):
    a, b = sebelum[i], sekarang[i]
    for k in ("nomor", "tahun", "judul", "jenis", "len_teks", "len_asli", "url", "kat"):
        if a[k] != b[k]:
            beda.append((i, k, a[k], b[k]))
cek("field Perbup yang berbeda", len(beda), 0)
for i, k, x, y in beda[:10]:
    print(f"      id={i} field={k}: {str(x)[:40]} -> {str(y)[:40]}")

# spot id spesifik: ambil dari snapshot supaya pasti ada
spot_ids = sorted(sebelum)
pilih = [spot_ids[0], spot_ids[len(spot_ids) // 2], spot_ids[-1]]
print("\n  Spot check ID Perbup spesifik:")
for id_ in pilih:
    d = sebelum[id_]
    r = conn.execute("SELECT id,judul,nomor,tanggal_terbit,jenis_dokumen "
                     "FROM documents WHERE id=?", (id_,)).fetchone()
    kat = conn.execute("""SELECT GROUP_CONCAT(t.label_topik,'||') FROM document_topics dt
                          JOIN topics t ON t.id=dt.topic_id WHERE dt.document_id=?""",
                       (id_,)).fetchone()[0] or ""
    print(f"    id={id_:<5} jenis={r['jenis_dokumen']:<18} "
          f"nomor={str(r['nomor']):<4} th={str(r['tanggal_terbit'])[:4]}")
    print(f"           judul: {r['judul'].strip()[:62]}")
    print(f"           topik DB   : {kat}")
    print(f"           topik snap : {d['kat']}")
    if kat != d["kat"]:
        gagal.append(f"spot id {id_}")
        print("           GAGAL: topik berubah")
    else:
        print("           OK: identik dengan snapshot")

# ---------- 3. identifier ----------
print()
print("=" * 78)
print("3. IDENTIFIER: prefix & tidak bentrok")
print("=" * 78)
nt_perda = [r[0] for r in conn.execute(
    "SELECT nomor_tahun FROM documents WHERE jenis_dokumen='Peraturan Daerah'")]
cek("jumlah identifier Perda", len(nt_perda), 83)
cek("identifier Perda berprefix 'perda_'", sum(1 for x in nt_perda if x and x.startswith("perda_")), 83)
cek("identifier Perda NULL", sum(1 for x in nt_perda if not x), 0)
cek("identifier unik Perda", len(set(nt_perda)), 83)
nt_perbup = [(str(r[0]).strip(), str(r[1])[:4]) for r in conn.execute(
    "SELECT nomor, tanggal_terbit FROM documents WHERE jenis_dokumen='Peraturan Bupati'")]
cek("identifier Perbup punya kolom nomor_tahun",
    conn.execute("SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Bupati' "
                 "AND nomor_tahun IS NOT NULL").fetchone()[0], 0)
tabrak = [x for x in nt_perda if x and not x.startswith("perda_")]
cek("identifier tanpa prefix (bentrok-prone)", len(tabrak), 0)
#撞 : apakah ada identifier yang sama setelah prefix dihapus
tanpa_prefix = {x[6:] for x in nt_perda if x and x.startswith("perda_")}
perbup_nt = {f"{a}_{b}" for a, b in nt_perbup}
cek("jumlah pasangan stem yang tumpang tindih",
    len(tanpa_prefix & perbup_nt), 70)
print("    (70 pasangan stem sama - itulah yang dicegah prefix, tidak bentrok di DB)")
print("    contoh identifier Perda :", ", ".join(sorted(nt_perda)[:6]))
print("    contoh stem Perbup     :", ", ".join(sorted(perbup_nt)[:6]))

# ---------- 4. status_hukum ----------
print()
print("=" * 78)
print("4. STATUS_HUKUM & CATATAN_RELASI")
print("=" * 78)
sh = dict(conn.execute(
    "SELECT COALESCE(status_hukum,'(NULL)') , COUNT(*) FROM documents "
    "GROUP BY jenis_dokumen, status_hukum").fetchall())
for row in conn.execute("""
    SELECT jenis_dokumen, COALESCE(status_hukum,'(NULL)') k, COUNT(*) c
    FROM documents GROUP BY jenis_dokumen, status_hukum ORDER BY jenis_dokumen
"""):
    print(f"    {row['jenis_dokumen']:<20} {row['k']:<16}{row['c']:>4}")
cek("Perda status_hukum='Berlaku'", conn.execute(
    "SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Daerah' "
    "AND status_hukum='Berlaku'").fetchone()[0], 75)
cek("Perda status_hukum='Tidak Berlaku'", conn.execute(
    "SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Daerah' "
    "AND status_hukum='Tidak Berlaku'").fetchone()[0], 8)
cek("Perbup status_hukum NULL", conn.execute(
    "SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Bupati' "
    "AND status_hukum IS NULL").fetchone()[0], 386)
# catatan_relasi tidak dispesifikasikan user -> hanya dilaporkan, bukan di-assert
n_catatan = conn.execute(
    "SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Daerah' "
    "AND catatan_relasi IS NOT NULL AND TRIM(catatan_relasi)<>''").fetchone()[0]
print(f"  {'Perda punya catatan_relasi (terisi)':<44}{n_catatan:>6}   "
      f"(observasi, bukan spesifikasi)")

# ---------- 5. topik ----------
print()
print("=" * 78)
print("5. TOPIK")
print("=" * 78)
cek("Perda dengan >=1 topik", conn.execute("""
    SELECT COUNT(DISTINCT dt.document_id) FROM document_topics dt
    JOIN documents d ON d.id=dt.document_id
    WHERE d.jenis_dokumen='Peraturan Daerah'""").fetchone()[0], 39)
cek("Perda tanpa topik", conn.execute(
    "SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Daerah' "
    "AND id NOT IN (SELECT document_id FROM document_topics)").fetchone()[0], 44)
cek("Perbup dengan >=1 topik", conn.execute("""
    SELECT COUNT(DISTINCT dt.document_id) FROM document_topics dt
    JOIN documents d ON d.id=dt.document_id
    WHERE d.jenis_dokumen='Peraturan Bupati'""").fetchone()[0], 247)
print()
print("    Distribusi topik PERDA:")
per = dict(conn.execute("""
    SELECT t.label_topik, COUNT(*) FROM document_topics dt
    JOIN documents d ON d.id=dt.document_id JOIN topics t ON t.id=dt.topic_id
    WHERE d.jenis_dokumen='Peraturan Daerah' GROUP BY t.label_topik""").fetchall())
for k, v in sorted(per.items(), key=lambda x: -x[1]):
    print(f"      {k:<46}{v:>4}")
print(f"      {'TOTAL relasi':<46}{sum(per.values()):>4}")

# ---------- 6. FTS ----------
print()
print("=" * 78)
print("6. FULL-TEXT SEARCH")
print("=" * 78)
cek("baris documents_fts", conn.execute("SELECT COUNT(*) FROM documents_fts").fetchone()[0], 469)
for uji in ("kepariwisataan", "persampahan", "APBD", "bangunan gedung"):
    n = conn.execute("SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH ?",
                     (f'"{uji}"',)).fetchone()[0]
    print(f"    FTS \"{uji}\" : {n} dokumen")
    # apakah ada yang salah jenis (Perbup ikut kena Perda-only term)
print()
cek("FTS Error (0 = sehat)",
    conn.execute("SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH '\"xyzzyqqq\"'")
    .fetchone()[0], 0)

# ---------- 7. konten ----------
print()
cek("Perda tanpa konten teks kosong", conn.execute(
    "SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Daerah' "
    "AND (konten_text IS NULL OR TRIM(konten_text)='')").fetchone()[0], 0)
cek("Perda konten==konten_asli", conn.execute(
    "SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Daerah' "
    "AND konten_text = konten_text_asli").fetchone()[0], 83)
cek("Perda dengan url_pdf terisi", conn.execute(
    "SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Daerah' "
    "AND url_pdf IS NOT NULL AND TRIM(url_pdf)<>''").fetchone()[0], 83)

conn.close()
print()
print("=" * 78)
print("RINGKASAN VERIFIKASI")
print("=" * 78)
print("  SEMUA CEK LULUS" if not gagal else f"  {len(gagal)} CEK GAGAL: {gagal}")
