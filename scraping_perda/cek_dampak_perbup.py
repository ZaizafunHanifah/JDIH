"""
Simulasi dampak perubahan keyword pada data Perbup yang SUDAH ADA.
Murni simulasi (tidak menulis apa pun).

Impor TOPICS langsung dari import_real_data.py supaya yang dibandingkan
benar-benar definisi yang dipakai aplikasi.

Jalankan: python cek_dampak_perbup.py
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
sys.path.insert(0, ROOT)

import import_real_data  # noqa: E402

CSV_PERBUP = os.path.join(ROOT, "raw_documents_export.csv")

TAMBAH = {
    "Perencanaan Pembangunan Daerah": [
        "penyertaan modal", "bumd", "badan usaha milik daerah",
        "perumda", "persero", "tata ruang", "perumahan",
        "permukiman", "kawasan", "rumah susun", "bangunan",
    ],
    "Pelayanan Kesehatan": ["penyakit"],
    "Pertanian dan Lingkungan Hidup": ["air minum"],
}


def match(judul, topics):
    j = (judul or "").lower()
    return [l for l, k in topics.items() if any(kw.lower() in j for kw in k)]


def main():
    lama = {k: list(v) for k, v in import_real_data.TOPICS.items()}
    baru = {k: list(v) for k, v in lama.items()}
    for kat, kws in TAMBAH.items():
        if kat not in baru:
            print(f"[PERINGATAN] kategori '{kat}' tidak ada di TOPICS")
            continue
        baru[kat] = baru[kat] + kws

    csv.field_size_limit(100000000)
    with io.open(CSV_PERBUP, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    lama_match = sum(1 for r in rows if match(r["judul"], lama))
    baru_match = sum(1 for r in rows if match(r["judul"], baru))
    print(f"Perbup total dokumen          : {len(rows)}")
    print(f"match dengan keyword LAMA     : {lama_match} "
          f"({lama_match / len(rows) * 100:.1f}%)")
    print(f"match dengan keyword BARU     : {baru_match} "
          f"({baru_match / len(rows) * 100:.1f}%)")
    print(f"selisih                       : {baru_match - lama_match} dokumen")
    print()

    c_lama, c_baru = collections.Counter(), collections.Counter()
    for r in rows:
        for t in match(r["judul"], lama):
            c_lama[t] += 1
        for t in match(r["judul"], baru):
            c_baru[t] += 1

    print(f"{'kategori':<46}{'lama':>6}{'baru':>6}{'selisih':>9}")
    for k in lama:
        a, b = c_lama.get(k, 0), c_baru.get(k, 0)
        tanda = "  <-- berubah" if a != b else ""
        print(f"{k:<46}{a:>6}{b:>6}{b - a:>9}{tanda}")

    baru_tertag = [r for r in rows
                   if not match(r["judul"], lama) and match(r["judul"], baru)]
    print()
    print(f"Dokumen Perbup yang BERUPAH jadi ter-tag: {len(baru_tertag)}")
    for r in baru_tertag[:25]:
        jt = ", ".join(match(r["judul"], baru))
        print(f"   [{r['tahun']}] {jt}")
        print(f"       {r['judul'].strip()[:80]}")


if __name__ == "__main__":
    main()
