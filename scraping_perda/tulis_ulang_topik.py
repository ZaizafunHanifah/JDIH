"""
Tulis ulang kolom 'topik' di perda_export.csv memakai definisi FINAL
dari import_real_data.py (sumber tunggal, sudah termasuk 3 perbaikan:
persampahan, perseroan, perumdam).

HANYA kolom topik yang ditulis ulang. Tidak ada scraping, tidak ada
ekstraksi ulang, jdih.db tidak disentuh.

Jalankan: python tulis_ulang_topik.py
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
from import_real_data import TOPICS, match_topics  # noqa: E402

csv.field_size_limit(100000000)


def main():
    with io.open(CSV_PERDA, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        kolom = reader.fieldnames

    print("=" * 78)
    print("TULIS ULANG KOLOM 'topik' DENGAN KATA KUNCI FINAL")
    print("=" * 78)
    print(f"Sumber definisi : import_real_data.TOPICS ({len(TOPICS)} kategori)")
    print(f"Dokumen         : {len(rows)}")
    print(f"Kolom CSV       : {kolom}")
    print()

    # verifikasi kata kunci final yang dipakai
    t = TOPICS
    print("Kata kunci final yang dipakai:")
    print(f"   persampahan di Pertanian : {'persampahan' in t['Pertanian dan Lingkungan Hidup']}")
    print(f"   perseroan  di Perencanaan: {'perseroan' in t['Perencanaan Pembangunan Daerah']}")
    print(f"   persero    di Perencanaan: {'persero' in t['Perencanaan Pembangunan Daerah']} (harus False)")
    print(f"   perumdam   di Perencanaan: {'perumdam' in t['Perencanaan Pembangunan Daerah']}")
    print(f"   bangunan   di Perencanaan: {'bangunan' in t['Perencanaan Pembangunan Daerah']} (harus False)")
    print(f"   'bangunan gedung'         : {'bangunan gedung' in t['Perencanaan Pembangunan Daerah']}")
    print()

    for r in rows:
        r["topik"] = "; ".join(match_topics(r["judul"]))

    # pastikan kolom topik ada di posisi akhir
    kolom_baru = [k for k in kolom if k != "topik"] + ["topik"]
    with io.open(CSV_PERDA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kolom_baru)
        w.writeheader()
        w.writerows(rows)

    # ---------- laporan ----------
    ter = [r for r in rows if r["topik"].strip()]
    print("=" * 78)
    print("HASIL")
    print("=" * 78)
    print(f"Baris ditulis   : {len(rows)}")
    print(f"Match 1+ topik  : {len(ter)} ({len(ter) / len(rows) * 100:.1f}%)")
    print(f"Tanpa topik     : {len(rows) - len(ter)}")

    per = collections.Counter()
    for r in ter:
        for t in r["topik"].split("; "):
            per[t] += 1
    print()
    print(f"{'kategori':<46}{'dok':>5}")
    print("-" * 51)
    for kat in TOPICS:
        n = per.get(kat, 0)
        print(f"{kat:<46}{n:>5}" + ("   (KOSONG)" if n == 0 else ""))
    print("-" * 51)
    print(f"{'TOTAL relasi':<46}{sum(per.values()):>5}")

    # integritas
    print()
    print("Integritas file:")
    print(f"   baris             : {len(rows)}")
    print(f"   kolom             : {kolom_baru}")
    print(f"   konten utuh       : "
          f"{all(r['konten_text'] == r['konten_text_asli'] for r in rows)}")
    print(f"   panjang total     : {sum(len(r['konten_text']) for r in rows):,} karakter")
    print(f"   status_hukum sah  : "
          f"{all(r['status_hukum'] in ('Berlaku', 'Tidak Berlaku') for r in rows)}")
    print(f"   topik valid         : "
          f"{all(all(t in TOPICS for t in r['topik'].split('; ') if t) for r in rows)}")

    # APBD
    frasa = ["anggaran pendapatan dan belanja daerah", "apbd", "keuangan daerah",
             "anggaran", "pendapatan", "belanja"]
    apbd = [r for r in rows if any(f in r["judul"].lower() for f in frasa)]
    apbd_tag = [r for r in apbd if r["topik"].strip()]
    print()
    print(f"Dokumen APBD/anggaran : {len(apbd)}")
    print(f"Yang ter-tag            : {len(apbd_tag)}")

    print()
    print("Contoh baris pertama:")
    for r in rows[:3]:
        print(f"  {r['nomor_tahun']:<10} {r['status_hukum']:<14} "
              f"topik={r['topik']!r}")


if __name__ == "__main__":
    main()
