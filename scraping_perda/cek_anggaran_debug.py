"""
Verifikasi: kenapa keyword APBD/Penjabaran/Lampiran menghasilkan 0.
Cek kata kunci apa yang SEBENARNYA muncul di 92 judul.
Jalankan: python cek_anggaran_debug.py
"""
import io
import json
import os
import re
import collections

BASE = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(BASE, "metadata_perda_2020_2026.json")

LEBIH_LEBAR = ["APBD", "Anggaran", "Penjabaran", "Lampiran", "Realisasi",
               "Pendapatan", "Belanja", "APM", "APBDes", "Anggaran Dasar",
               "Pelaksanaan", "Perubahan", "Dana"]

with open(META, encoding="utf-8") as f:
    data = json.load(f)

print("Cek kata kunci pada 92 judul:")
print("-" * 70)
for k in LEBIH_LEBAR:
    n = sum(1 for d in data if re.search(re.escape(k), d.get("judul") or "", re.I))
    print(f"  {k:<20}: {n}")

print()
print("Kata kunci asli yang diminta (dengan \\b):")
for k in ["APBD", "Penjabaran", "Lampiran"]:
    withb = sum(1 for d in data if re.search(r"\b" + k, d.get("judul") or "", re.I))
    tanpa = sum(1 for d in data if re.search(re.escape(k), d.get("judul") or "", re.I))
    print(f"  {k:<12}: dengan \\b = {withb}, tanpa \\b = {tanpa}")

print()
print("Kata yang paling sering muncul di judul:")
kata = collections.Counter()
for d in data:
    for w in re.findall(r"[A-Za-z]{3,}", (d.get("judul") or "")):
        kata[w.lower()] += 1
for w, c in kata.most_common(30):
    print(f"  {w:<18}: {c}")

print()
print("Semua judul 2026 (untuk lihat pola penamaan):")
for d in data:
    if d["tahun"] == "2026":
        print(f"  {d['id']}: {d['judul']}")
