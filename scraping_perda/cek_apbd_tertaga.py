"""Cek dokumen APBD yang ikut ter-tag: kata mana yang memicu."""
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from import_real_data import TOPICS, match_topics  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
FRASA = ["anggaran pendapatan dan belanja daerah", "apbd", "keuangan daerah",
         "anggaran", "pendapatan", "belanja"]

csv.field_size_limit(100000000)
with io.open(os.path.join(BASE, "perda_export.csv"), encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print("Dokumen APBD yang ter-tag - kata kunci mana yang memicu:\n")
for r in rows:
    if not any(f in r["judul"].lower() for f in FRASA):
        continue
    m = match_topics(r["judul"])
    if not m:
        continue
    print(f"[{r['nomor_tahun']}] topik={m}")
    print(f"  judul: {r['judul'].strip()}")
    print(f"  frasa APBD di judul : "
          f"{[f for f in FRASA if f in r['judul'].lower()]}")
    j = r["judul"].lower()
    for kat in m:
        cocok = [kw for kw in TOPICS[kat] if kw.lower() in j]
        print(f"  memicu dari {kat}: {cocok}")
    print()

# verifikasi file tidak rusak
print("=" * 70)
print("Verifikasi file:")
print(f"  baris        : {len(rows)}")
print(f"  kolom topik  : ada = {'topik' in rows[0]}")
print(f"  ter-tag      : {sum(1 for r in rows if r['topik'].strip())}")
print(f"  teks utuh    : {all(r['konten_text'] == r['konten_text_asli'] for r in rows)}")
print(f"  status ok    : {all(r['status_hukum'] in ('Berlaku','Tidak Berlaku') for r in rows)}")
print(f"  panjang teks total: {sum(len(r['konten_text']) for r in rows):,}")
