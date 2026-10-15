"""Verifikasi file perda_export.csv."""
import collections
import csv
import io
import os
import sys

csv.field_size_limit(100000000)
p = "perda_export.csv"

with io.open(p, encoding="utf-8") as f:
    r = csv.DictReader(f)
    rows = list(r)
    kolom = r.fieldnames

print("file   :", p, "|", os.path.getsize(p) / 1024**2, "MB")
print("kolom  :", kolom)
print("baris  :", len(rows))
print()

harapan = ["nomor_tahun", "judul", "nomor", "tahun", "url_pdf",
           "konten_text", "konten_text_asli", "status_hukum", "catatan_relasi"]
print("kolom sesuai permintaan:", kolom == harapan)
print()

# isi wajib
for k in ["nomor_tahun", "judul", "nomor", "tahun", "url_pdf"]:
    kosong = [x["nomor_tahun"] for x in rows if not x[k].strip()]
    print(f"  {k:<20} kosong: {len(kosong)}" + (f" {kosong[:5]}" if kosong else ""))

# konten_text == konten_text_asli
beda = [x["nomor_tahun"] for x in rows if x["konten_text"] != x["konten_text_asli"]]
print(f"\nkonten_text == konten_text_asli : {len(rows) - len(beda)}/{len(rows)}"
      + (f" | beda: {beda[:5]}" if beda else ""))

# status_hukum hanya nilai baku
nilai = collections.Counter(x["status_hukum"] for x in rows)
print("nilai status_hukum :", dict(nilai))

# url_pdf sesuai pola
salah = [x["nomor_tahun"] for x in rows
         if not x["url_pdf"].rstrip("/").endswith(x["url_pdf"].rstrip("/").split("/")[-1])]
print("url_pdf tidak mengandung id sendiri:",
      sum(1 for x in rows if x["url_pdf"].split("/")[-1] != x["nomor_tahun"]))

# cek karakter newline/tab tidak merusak csv
print()
print("Cek 3 baris pertama:")
for x in rows[:3]:
    print(f"  {x['nomor_tahun']:<10} {x['status_hukum']:<14} "
          f"teks {len(x['konten_text']):>9,} kar | relasi: {x['catatan_relasi'][:45]!r}")
    print(f"      {x['judul'][:75]}")
