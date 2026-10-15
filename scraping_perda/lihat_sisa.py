"""Tampilkan judul PENUH 11 dokumen yang belum tertangkap tema."""
import csv
import io
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
TARGET = {
    "11_2020", "8_2020", "1_2021", "3_2021", "11_2021",
    "1_2022", "3_2022", "1_2023", "3_2024", "4_2024", "6_2024",
}

csv.field_size_limit(100000000)
with io.open(os.path.join(BASE, "perda_export.csv"), encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print(f"JUDUL LENGKAP {len(TARGET)} dokumen:\n")
for r in rows:
    if r["nomor_tahun"] in TARGET:
        print(f"[{r['nomor_tahun']}] {r['judul'].strip()}")
        print()
