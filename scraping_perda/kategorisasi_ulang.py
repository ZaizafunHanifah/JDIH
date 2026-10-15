"""
Kategori ulang 83 dokumen Perda di perda_export.csv memakai definisi TOPICS
dari import_real_data.py (sumber tunggal, sama dengan yang dipakai Perbup).

HANYA menulis kolom 'topik' - tidak ada scraping, tidak ada ekstraksi ulang.
Metadata lain (konten_text, status_hukum, dll) tidak disentuh.

Jalankan: python kategorisasi_ulang.py
"""
import collections
import csv
import io
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
CSV_PERDA = os.path.join(BASE, "perda_export.csv")

sys.path.insert(0, ROOT)

# impor definisi & fungsi dari sumber tunggal - TIDAU didefinisikan ulang di sini
from import_real_data import TOPICS, match_topics  # noqa: E402

# frasa yang menandai dokumen APBD/keuangan - dipakai HANYA untuk laporan
# konfirmasi, TIDAK ikut ke TOPICS (sesuai keputusan: tidak ditambahkan)
FRASA_APBD = [
    "anggaran pendapatan dan belanja daerah", "apbd", "keuangan daerah",
    "anggaran", "pendapatan", "belanja",
]


def main():
    csv.field_size_limit(100000000)
    with io.open(CSV_PERDA, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        kolom_lama = reader.fieldnames

    print("=" * 78)
    print("KATEGORIZASI ULANG 83 DOKUMEN PERDA")
    print("=" * 78)
    print(f"Sumber definisi topik : import_real_data.TOPICS ({len(TOPICS)} kategori)")
    print(f"Jumlah dokumen         : {len(rows)}")
    print()

    # pastikan kolom 'topik' ada, di positioned paling akhir
    kolom_baru = [k for k in kolom_lama if k != "topik"] + ["topik"]

    for r in rows:
        r["topik"] = "; ".join(match_topics(r["judul"]))

    # tulis ulang file yang sama
    with io.open(CSV_PERDA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kolom_baru)
        w.writeheader()
        w.writerows(rows)

    # --- laporan ---
    ter_tag = [r for r in rows if r["topik"].strip()]
    tanpa_tag = [r for r in rows if not r["topik"].strip()]

    print("=" * 78)
    print("COVERAGE")
    print("=" * 78)
    print(f"Match minimal 1 topik : {len(ter_tag)} / {len(rows)} "
          f"({len(ter_tag) / len(rows) * 100:.1f}%)")
    print(f"Tidak match topik     : {len(tanpa_tag)} / {len(rows)} "
          f"({len(tanpa_tag) / len(rows) * 100:.1f}%)")
    print(f"Sebelumnya           : 25 match / 58 tidak match")
    print(f"Perubahan             : +{len(ter_tag) - 25} dokumen jadi ter-tag")

    print()
    print("=" * 78)
    print("DISTRIBUSI SEMUA 10 KATEGORI")
    print("=" * 78)
    per = collections.Counter()
    for r in ter_tag:
        for t in r["topik"].split("; "):
            per[t] += 1
    print(f"{'kategori':<46}{'dok':>6}")
    print("-" * 52)
    for kat in TOPICS:
        n = per.get(kat, 0)
        tanda = "   (KOSONG)" if n == 0 else ""
        print(f"{kat:<46}{n:>6}{tanda}")
    print("-" * 52)
    print(f"{'TOTAL relasi topik':<46}{sum(per.values()):>6}")
    print(f"{'(dokumen bisa punya >1 topik)':<46}")

    # --- konfirmasi APBD tidak ikut ter-tag ---
    print()
    print("=" * 78)
    print("KONFIRMASI: DOKUMEN APBD TIDAK IKUT TER-TAG")
    print("=" * 78)
    apbd = [r for r in rows
            if any(f in r["judul"].lower() for f in FRASA_APBD)]
    apbd_tertag = [r for r in apbd if r["topik"].strip()]
    print(f"Dokumen dengan kata APBD/anggaran di judul : {len(apbd)}")
    print(f"Dokumen APBD yang TER-TAG                 : {len(apbd_tertag)}")

    if apbd_tertag:
        print("\n  dokumen APBD yang justru ter-tag (perlu ditinjau):")
        for r in apbd_tertag:
            print(f"    - [{r['tahun']}] topik={r['topik']}")
            print(f"      {r['judul'].strip()[:88]}")
    else:
        print("  -> SEMUA dokumen APBD tetap tanpa topik. Sesuai keputusan.")

    # dokumen tanpa topik yang TIDAK APBD
    bukan_apbd = [r for r in tanpa_tag
                  if not any(f in r["judul"].lower() for f in FRASA_APBD)]
    print(f"\nDokumen tanpa topik yang BUKAN APBD : {len(bukan_apbd)}")
    for r in bukan_apbd:
        print(f"  - [{r['tahun']}] {r['judul'].strip()[:88]}")

    print(f"\nFile diperbarui: {os.path.basename(CSV_PERDA)}")
    print(f"Kolom: {kolom_baru}")


if __name__ == "__main__":
    main()
