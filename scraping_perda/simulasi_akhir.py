"""
TUGAS 5 - SIMULASI kategorisasi setelah perbaikan word boundary.
JANGAN sentuh jdih.db - hanya READ (SELECT) untuk membandingkan
kategorisasi yang SAAT INI tersimpan di database.

Perbandingan:
  A) 386 Perbup : kategori di DB  vs  hasil match_topics() baru
  B) 83 Perda   : kategori di CSV vs  hasil match_topics() baru
Jalankan: python simulasi_akhir.py
"""
import collections
import csv
import io
import os
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DB = os.path.join(ROOT, "jdih.db")
CSV_PERDA = os.path.join(BASE, "perda_export.csv")
CSV_PERBUP = os.path.join(ROOT, "raw_documents_export.csv")

sys.path.insert(0, ROOT)
from import_real_data import TOPICS, match_topics  # noqa: E402

csv.field_size_limit(100000000)


def main():
    # ---------- baca DB (READ-ONLY) ----------
    print("=" * 78)
    print("SIMULASI KATEGORISASI SETELAH PERBAIKAN WORD BOUNDARY")
    print("=" * 78)
    print("jdih.db dibuka READ-ONLY - tidak ada penulisan sama sekali\n")

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    db_rows = conn.execute("""
        SELECT d.id, d.nomor, d.tanggal_terbit, d.judul, d.jenis_dokumen,
               GROUP_CONCAT(t.label_topik, '||') AS kat
        FROM documents d
        LEFT JOIN document_topics dt ON dt.document_id = d.id
        LEFT JOIN topics t ON t.id = dt.topic_id
        GROUP BY d.id
    """).fetchall()

    n_db = len(db_rows)
    print(f"Database berisi {n_db} dokumen "
          f"({sum(1 for r in db_rows if r['jenis_dokumen'] == 'Peraturan Bupati')} Perbup)")
    print(f"Topik di DB: {conn.execute('SELECT COUNT(*) FROM topics').fetchone()[0]}\n")

    # ---------- A) PERBUP ----------
    perbup = [r for r in db_rows if r["jenis_dokumen"] == "Peraturan Bupati"]
    berubah, sama = [], []
    for r in perbup:
        nt = f"{str(r['nomor']).strip()}_{str(r['tanggal_terbit'])[:4].strip()}"
        db_kat = set((r["kat"] or "").split("||")) - {""}
        baru_kat = set(match_topics(r["judul"]))
        if db_kat != baru_kat:
            berubah.append((nt, r["judul"], db_kat, baru_kat))
        else:
            sama.append(nt)

    print("=" * 78)
    print("A) PERBUP - perbandingan dengan yang TERSIMPAN DI jdih.db")
    print("=" * 78)
    print(f"Total Perbup di DB        : {len(perbup)}")
    print(f"Kategori BERUBAH         : {len(berubah)}")
    print(f"Kategori tetap sama      : {len(sama)}")
    print()

    lost = [b for b in berubah if b[2] and not b[3]]
    gain = [b for b in berubah if b[3] and not b[2]]
    both = [b for b in berubah if b[2] and b[3]]
    print(f"  kehilangan kategori (ada di DB, hilang sekarang) : {len(lost)}")
    print(f"  dapat kategori baru   (tak ada di DB, muncul)   : {len(gain)}")
    print(f"  kategori berubah (masih ada, tapi berbeda)       : {len(both)}")
    print()

    if lost:
        print("--- KEHILANGAN KATEGORI ---")
        for nt, judul, dk, bk in lost:
            print(f"  [{nt}] hilangnya: {sorted(dk)}")
            print(f"       {judul.strip()[:88]}")
        print()

    if gain:
        print("--- KATEGORI BARU MUNCUL ---")
        for nt, judul, dk, bk in gain:
            print(f"  [{nt}] didapat: {sorted(bk)}")
            print(f"       {judul.strip()[:88]}")
        print()

    if both:
        print("--- KATEGORI BERUBAH (ganti) ---")
        for nt, judul, dk, bk in both:
            print(f"  [{nt}] LAMA: {sorted(dk)}")
            print(f"       BARU: {sorted(bk)}")
            print(f"       {judul.strip()[:88]}")
        print()

    # ---------- B) PERDA ----------
    print("=" * 78)
    print("B) PERDA - hasil baru (simulasi, tidak diimport ke DB)")
    print("=" * 78)
    with io.open(CSV_PERDA, encoding="utf-8") as f:
        perda = list(csv.DictReader(f))

    baru_perda = [(r, match_topics(r["judul"])) for r in perda]
    ter_tag = [(r, m) for r, m in baru_perda if m]
    tanpa = [(r, m) for r, m in baru_perda if not m]

    # bandingkan dengan kolom topik yang sekarang di CSV (hasil substring lama)
    lama_tertag = [r for r in perda if (r.get("topik") or "").strip()]

    print(f"Total Perda              : {len(perda)}")
    print(f"Match minimal 1 topik    : {len(ter_tag)} ({len(ter_tag) / len(perda) * 100:.1f}%)")
    print(f"Tidak match              : {len(tanpa)}")
    print(f"Sebelumnya (substring)  : {len(lama_tertag)} match")
    print(f"Perubahan                : {len(ter_tag) - len(lama_tertag):+d} dokumen")
    print()

    per = collections.Counter()
    for _, m in ter_tag:
        for t in m:
            per[t] += 1
    print(f"{'kategori':<46}{'dok':>6}")
    print("-" * 52)
    for kat in TOPICS:
        n = per.get(kat, 0)
        print(f"{kat:<46}{n:>6}" + ("   (KOSONG)" if n == 0 else ""))
    print("-" * 52)
    print(f"{'TOTAL relasi':<46}{sum(per.values()):>6}")

    # dokumen yang kehilangan tag
    hilang = [r for r, m in baru_perda
              if not m and (r.get("topik") or "").strip()]
    if hilang:
        print()
        print(f"--- PERDA yang kehilangan tag: {len(hilang)} ---")
        for r in hilang:
            print(f"  [{r['nomor_tahun']}] sebelumnya: {r['topik']}")
            print(f"       {r['judul'].strip()[:85]}")

    dapat = [(r, m) for r, m in baru_perda
             if m and not (r.get("topik") or "").strip()]
    if dapat:
        print()
        print(f"--- PERDA yang dapat tag baru: {len(dapat)} ---")
        for r, m in dapat:
            print(f"  [{r['nomor_tahun']}] -> {m}")
            print(f"       {r['judul'].strip()[:85]}")

    # konfirmasi APBD
    print()
    FRASA = ["anggaran pendapatan dan belanja daerah", "apbd", "keuangan daerah",
             "anggaran", "pendapatan", "belanja"]
    apbd = [(r, m) for r, m in baru_perda
            if any(f in r["judul"].lower() for f in FRASA)]
    apbd_tag = [(r, m) for r, m in apbd if m]
    print(f"Dokumen APBD/anggaran : {len(apbd)}")
    print(f"D其中 ter-tag           : {len(apbd_tag)}".replace("D其中", "Dokumen yang"))
    for r, m in apbd_tag:
        print(f"   [{r['nomor_tahun']}] {m}")
        print(f"      {r['judul'].strip()[:85]}")

    conn.close()
    print("\n(jdih.db TIDAK diubah - koneksi read-only ditutup)")


if __name__ == "__main__":
    main()
