"""
TUGAS 2 - AUDIT kata kunci topik terhadap SELURUH 469 judul
(386 Perbup + 83 Perda).

Untuk tiap kata kunci, cari kemunculan yang TIDAK berdiri sebagai kata utuh,
yaitu tidak didahului/diikuti oleh spasi, tanda baca, atau batas kata.
Itu indikasi kuat keyword yang merupakan substring dari kata lain.

Fokus utama: keyword pendek (< 6 huruf) yang paling rawan.

Murni analisis - tidak menulis apa pun.
Jalankan: python audit_keyword.py
"""
import collections
import csv
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
CSV_PERDA = os.path.join(BASE, "perda_export.csv")
CSV_PERBUP = os.path.join(ROOT, "raw_documents_export.csv")

sys.path.insert(0, ROOT)
from import_real_data import TOPICS  # noqa: E402

csv.field_size_limit(100000000)


def muat(path, jenis):
    with io.open(path, encoding="utf-8") as f:
        out = []
        for r in csv.DictReader(f):
            out.append((jenis, r.get("nomor_tahun") or f"{r.get('nomor')}_{r.get('tahun')}",
                        r.get("judul") or ""))
    return out


def cek_kata_utuh(judul_lower, kw_lower):
    """
    True kalau keyword muncul sebagai kata utuh (menggunakan \\b regex).
    """
    return re.search(r"\b" + re.escape(kw_lower) + r"\b", judul_lower) is not None


def kemunculan_tidak_utuh(judul_lower, kw_lower):
    """
    Kembalikan daftar substring match yang TIDAK berbatas kata.
    """
    hasil = []
    for m in re.finditer(re.escape(kw_lower), judul_lower):
        a, b = m.start(), m.end()
        kiri = judul_lower[a - 1] if a > 0 else " "
        kanan = judul_lower[b] if b < len(judul_lower) else " "
        # kata utuh bila kiri & kanan bukan karakter [\w]
        if re.match(r"\w", kiri) or re.match(r"\w", kanan):
            konteks = judul_lower[max(0, a - 14):b + 14]
            hasil.append((konteks, kiri, kanan))
    return hasil


def main():
    semua = muat(CSV_PERBUP, "Perbup") + muat(CSV_PERDA, "Perda")
    print("=" * 78)
    print(f"AUDIT KATA KUNCI - {len(semua)} judul "
          f"({len(semua) - 83} Perbup + 83 Perda)")
    print("=" * 78)
    print()

    # --- rangkuman per keyword ---
    baris_audit = []
    for kat, kws in TOPICS.items():
        for kw in kws:
            kwl = kw.lower()
            n_total = 0
            n_benar = 0
            n_salah = 0
            contoh_salah = []
            for jenis, nt, judul in semua:
                jl = judul.lower()
                if kwl not in jl:
                    continue
                n_total += 1
                if cek_kata_utuh(jl, kwl):
                    n_benar += 1
                else:
                    n_salah += 1
                    if len(contoh_salah) < 4:
                        salah = kemunculan_tidak_utuh(jl, kwl)
                        if salah:
                            contoh_salah.append((jenis, nt, salah[0][0]))
            baris_audit.append({
                "kategori": kat, "kw": kw, "len": len(kwl),
                "total": n_total, "benar": n_benar, "salah": n_salah,
                "contoh": contoh_salah,
            })

    # --- hanya yang punya masalah, urut dari paling parah ---
    bermasalah = [b for b in baris_audit if b["salah"] > 0]
    bermasalah.sort(key=lambda b: (-b["salah"], b["len"]))

    print(f"Total keyword diperiksa : {len(baris_audit)}")
    print(f"Keyword bermasalah      : {len(bermasalah)}")
    print()
    print("=" * 78)
    print("KEYWORD YANG COCOK TIDAK SEBAGAI KATA UTUH (butuh \\b)")
    print("=" * 78)
    print(f"{'kategori':<30}{'keyword':<26}{'total':>6}{'false':>7}")
    print("-" * 72)
    for b in bermasalah:
        print(f"{b['kategori'][:29]:<30}{b['kw'][:25]:<26}"
              f"{b['total']:>6}{b['salah']:>7}")
    print("-" * 72)
    total_false = sum(b["salah"] for b in bermasalah)
    print(f"{'TOTAL FALSE POSITIVE':<56}{sum(b['total'] for b in bermasalah):>6}"
          f"{total_false:>7}")

    # --- rincian contoh ---
    print()
    print("=" * 78)
    print("RINCIAN: kata mana yang 'menelan' kata mana")
    print("=" * 78)
    for b in bermasalah:
        print(f"\n### '{b['kw']}' ({b['kategori']})")
        print(f"    {b['salah']} dari {b['total']} kemunculan bukan kata utuh")
        for jenis, nt, konteks in b["contoh"]:
            print(f"      [{jenis} {nt}] ...{konteks.strip()}...")

    # --- keyword pendek yang bersih (aman) ---
    print()
    print("=" * 78)
    print("KEYWORD PENDEK (< 6 HURUF) YANG BERSIH - aman, tidak perlu diubah")
    print("=" * 78)
    bersih = [b for b in baris_audit if b["len"] < 6 and b["salah"] == 0 and b["total"] > 0]
    for b in bersih:
        print(f"   {b['kw']:<14} ({b['kategori'][:36]}) - {b['total']} kemunculan, semua kata utuh")
    if not bersih:
        print("   (tidak ada)")

    # --- keyword yang tidak muncul sama sekali ---
    nol = [b for b in baris_audit if b["total"] == 0]
    print()
    print("=" * 78)
    print(f"KEYWORD YANG TIDAK PERNAH MUNCUL DI 469 JUDUL ({len(nol)})")
    print("=" * 78)
    for b in nol:
        print(f"   {b['kw']:<28} ({b['kategori'][:40]})")


if __name__ == "__main__":
    main()
