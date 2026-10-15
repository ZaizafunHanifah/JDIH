"""
Cek pr scraping: hitung dokumen llaves indikasi dokumen anggaran besar
dari judul di metadata_perda_2020_2026.json (TANPA buka PDF).

Jalankan: python cek_anggaran.py
"""
import collections
import io
import json
import os
import re
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(BASE, "metadata_perda_2020_2026.json")

# Keyword asli yang dimintauser: APBD / Penjabaran / Lampiran.
# Hasil verifikasi: TIGA KATA ITU TIDAK PERNAH MUNCUL di 92 judul JDIH.
# JDIH memakai ejaan penuh, jadi klasifikasi memakai kata kunci nyata.
KEYWORD_AWAL = ["APBD", "Penjabaran", "Lampiran"]
KEYWORD_NYATA = ["Anggaran", "Pendapatan", "Belanja", "Pelaksanaan",
                 "Realisasi", "Rencana", "Perubahan", "Dana"]


def main():
    # --- 1. ruang disk ---
    drive = os.path.dirname(os.path.dirname(BASE))
    total, used, free = shutil.disk_usage(drive)
    print("=" * 78)
    print("1. RUANG DISK")
    print("=" * 78)
    print(f"drive      : {drive}")
    print(f"total      : {total / 1024**3:>8.1f} GB")
    print(f"terpakai   : {used / 1024**3:>8.1f} GB  ({used / total * 100:.1f}%)")
    print(f"TERSEDIA   : {free / 1024**3:>8.1f} GB  ({free / total * 100:.1f}%)")

    for p in ("pdf_raw", "text_raw"):
        d = os.path.join(BASE, p)
        if os.path.isdir(d):
            files = os.listdir(d)
            size = sum(os.path.getsize(os.path.join(d, f)) for f in files)
            print(f"  {p:<10}: {size / 1024**2:>7.2f} MB ({len(files)} file)")
    print()

    # --- 2. dokumen indikasi anggaran ---
    with open(META, encoding="utf-8") as f:
        data = json.load(f)

    def cocok_awal(doc):
        judul = doc.get("judul") or ""
        return [k for k in KEYWORD_AWAL if re.search(r"\b" + k, judul, re.I)]

    def cocok_nyata(doc):
        judul = doc.get("judul") or ""
        return [k for k in KEYWORD_NYATA if re.search(r"\b" + k, judul, re.I)]

    # kata kunci "anggaran" yang paling kuat menandakan dokumen anggaran
    anggaran = [d for d in data if cocok_nyata(d)]
    biasa = [d for d in data if not cocok_nyata(d)]

    print("=" * 78)
    print("2. INDIKASI DOKUMEN ANGGARAN BESAR (dari judul, tanpa buka PDF)")
    print("=" * 78)
    print(f"total dokumen : {len(data)}")
    print()
    print("CATATAN: keyword yang diminta (APBD/Penjabaran/Lampiran)")
    print("TIDAK PERNAH muncul di 92 judul. JDIH memakai ejaan penuh.")
    print("  APBD       :", sum(len(cocok_awal(d)) for d in data), "dokumen")
    print("  Penjabaran :", sum(len(cocok_awal(d)) for d in data), "dokumen")
    print("  Lampiran   :", sum(len(cocok_awal(d)) for d in data), "dokumen")
    print()
    print(f"Dengan kata kunci nyata: {len(anggaran)} indikasi anggaran / "
          f"{len(biasa)} dokumen biasa")
    print()
    print("Jumlah per kata kunci nyata:")
    for k in KEYWORD_NYATA:
        n = sum(1 for d in data if re.search(r"\b" + k, d.get("judul") or "", re.I))
        print(f"   {k:<14}: {n}")

    hitung = collections.Counter(k for d in anggaran for k in cocok_nyata(d))
    print("\nKemunculan (dokumen bisa punya >1):")
    for k, v in hitung.most_common():
        print(f"   {k:<14}: {v}")

    # dokumen dengan strongest signal: 'Anggaran' di judul
    kuat = [d for d in anggaran if re.search(r"\bAnggaran\b", d.get("judul") or "", re.I)]
    print(f"\nSubset dengan kata 'Anggaran' (indikasi terkuat): {len(kuat)}")
    print(f"\n{'id':<7}{'th':<6}{'status':<15}judul")
    print("-" * 78)
    for d in sorted(anggaran, key=lambda x: (x["tahun"], x["id"])):
        print(f"{d['id']:<7}{d['tahun']:<6}{str(d['status_hukum']):<15}"
              f"{(d.get('judul') or '')[:66]}")

    b = sum(1 for d in anggaran if d["status_hukum"] == "Berlaku")
    print("-" * 78)
    print(f"anggaran Berlaku       : {b}")
    print(f"anggaran Tidak Berlaku : {len(anggaran) - b}")

    per_tahun = collections.Counter(d["tahun"] for d in anggaran)
    print("\nPer tahun:", dict(sorted(per_tahun.items())))

    # --- proyeksi kasar ---
    print()
    print("=" * 78)
    print("PROYEKSI KASAR (kasus 4947: 25,7 MB / 1458 halaman / berlabel 'Anggaran')")
    print("=" * 78)
    print(f"  dokumen berlabel 'Anggaran' : {len(kuat)}")
    print(f"  jika semua ~= 25,7 MB       : ~{len(kuat) * 25.7 / 1024:.2f} GB")
    print(f"  jika 92 semua ~= 25,7 MB    : ~{len(data) * 25.7 / 1024:.2f} GB")
    print(f"  ruang tersisa              : {free / 1024**3:.1f} GB")
    print("\n  CATATAN: kata 'Anggaran' tidak selalu berarti PDF 1458 halaman.")
    print("  Dari 3 PDF 2026, hanya 4947 (anggaran) yang terbukti sangat besar.")


if __name__ == "__main__":
    main()
