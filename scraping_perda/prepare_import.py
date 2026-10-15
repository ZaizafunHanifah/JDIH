"""
Siapkan data Peraturan Daerah hasil scraping untuk diimpor ke jdih.db.
=====================================================================
Membaca metadata_perda_final.json, mengambil hanya dokumen yang ekstraksi
teksnya BERHASIL, lalu mengekspor ke perda_export.csv.

Kolom CSV: nomor_tahun, judul, nomor, tahun, url_pdf, konten_text,
            konten_text_asli, status_hukum, catatan_relasi

Catatan penting soal identifier:
  format nomor_tahun = "{nomor}_{tahun}" (mis. "1_2020") mengikuti konvensi
  raw_documents_export.csv milik Perbup. PERLU DIWASPADAI: karena tabel
  documents tidak punya kolom jenis_dokumen di kunci lookup-nya,
  identifier yang sama bisa dipakai lebih dari satu jenis dokumen.
  Laporan bentrok dicetak di akhir.

Jalankan: python prepare_import.py
"""
import collections
import csv
import io
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(BASE, "metadata_perda_final.json")
KELUARAN = os.path.join(BASE, "perda_export.csv")
CSV_PERBUP = os.path.join(os.path.dirname(BASE), "raw_documents_export.csv")

JENIS_DOKUMEN = "Peraturan Daerah"

# Definisi TOPICS dan match_topics TIDAK lagi didefinisikan di sini.
# Diimpor dari import_real_data.py supaya hanya ada SATU sumber kebenaran
# (pencocokan sama untuk Perbup dan Perda, selalu sinkron).
sys.path.insert(0, os.path.dirname(BASE))
from import_real_data import TOPICS, match_topics  # noqa: E402


def bersihkan_nomor(nilai):
    """
    Nomor peraturan dari JDIH kadang berisi spasi/tab tak terlihat
    (mis. '14 ' di tabel listing). Rapor supaya identifier tidak
    jadi '14 _2020'.
    """
    if nilai is None:
        return ""
    return " ".join(str(nilai).split()).strip()


def main():
    csv.field_size_limit(100000000)

    with io.open(META, encoding="utf-8") as f:
        semua = json.load(f)

    print("=" * 78)
    print("PERSIAPAN IMPORT PERATURAN DAERAH")
    print("=" * 78)

    berhasil = [d for d in semua if d.get("status_ekstraksi") == "ok"]
    gagal = [d for d in semua if d.get("status_ekstraksi") != "ok"]
    print(f"Total di metadata : {len(semua)}")
    print(f"Berhasil ekstraksi : {len(berhasil)}  (dipakai)")
    print(f"Gagal ekstraksi    : {len(gagal)}  (dilewati)")
    print()

    baris = []
    tanpa_teks = []
    tanpa_topik = []
    total_kar = 0

    for d in berhasil:
        doc_id = d["id"]
        nomor = bersihkan_nomor(d.get("no_peraturan") or d.get("Nomor Peraturan"))
        tahun = bersihkan_nomor(d.get("tahun") or d.get("Tahun Terbit"))
        path_teks = d.get("path_teks")
        if not path_teks:
            path_teks = os.path.join("text_raw", f"{doc_id}.txt")
        absolut = path_teks if os.path.isabs(path_teks) else os.path.join(BASE, path_teks)

        try:
            with io.open(absolut, encoding="utf-8") as f:
                teks = f.read()
        except OSError as exc:
            print(f"  ! id={doc_id} tidak bisa baca teks ({exc})")
            continue

        if not teks.strip():
            tanpa_teks.append(doc_id)
            continue

        total_kar += len(teks)
        nomor_tahun = f"{nomor}_{tahun}"

        # konten_text dipakai untuk FTS5; konten_text_asli menyimpan apa adanya.
        # Keduanya sama persis - FTS5 tidak butuh cleaning/stemming.
        baris.append({
            "nomor_tahun": nomor_tahun,
            "judul": d.get("judul") or "",
            "nomor": nomor,
            "tahun": tahun,
            "url_pdf": d.get("url_pdf") or "",
            "konten_text": teks,
            "konten_text_asli": teks,
            "status_hukum": d.get("status_hukum") or "",
            "catatan_relasi": d.get("catatan_relasi") or "",
        })

        # kategorisasi topik dicek ke kolom judul (sama seperti Perbup)
        if not match_topics(d.get("judul") or ""):
            tanpa_topik.append((doc_id, nomor_tahun, (d.get("judul") or "")[:60]))

    # --- tulis CSV ---
    kolom = ["nomor_tahun", "judul", "nomor", "tahun", "url_pdf",
             "konten_text", "konten_text_asli", "status_hukum", "catatan_relasi"]
    with io.open(KELUARAN, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=kolom)
        w.writeheader()
        w.writerows(baris)

    # --- laporan ---
    print()
    print("=" * 78)
    print("LAPORAN")
    print("=" * 78)
    print(f"Total baris ditulis   : {len(baris)}")
    print(f"File                  : {os.path.basename(KELUARAN)} "
          f"({os.path.getsize(KELUARAN) / 1024**2:.2f} MB)")
    print(f"Total karakter teks   : {total_kar:,}")
    print(f"jenis_dokumen         : {JENIS_DOKUMEN}")

    # status_hukum
    dist = collections.Counter(b["status_hukum"] or "(kosong)" for b in baris)
    print("\nDistribusi status_hukum:")
    for k, v in dist.most_common():
        print(f"   {k:<20}: {v}")

    # catatan_relasi
    ada_relasi = [b for b in baris if b["catatan_relasi"].strip()]
    print(f"\nDokumen dengan catatan_relasi : {len(ada_relasi)}")
    print(f"Dokumen tanpa catatan_relasi  : {len(baris) - len(ada_relasi)}")

    # topik
    print("\nKategori topik (dicek ke kolom judul):")
    n_match = 0
    per_topik = collections.Counter()
    for b in baris:
        m = match_topics(b["judul"])
        if m:
            n_match += 1
            for t in m:
                per_topik[t] += 1
    print(f"   match minimal 1 topik : {n_match}")
    print(f"   TIDAK match topik      : {len(baris) - n_match}")
    for t, c in per_topik.most_common():
        print(f"      {t:<45}: {c}")

    if tanpa_teks:
        print(f"\nDokumen dengan file teks kosong: {tanpa_teks}")

    # --- risiko bentrok identifier dengan Perbup ---
    if os.path.exists(CSV_PERBUP):
        with io.open(CSV_PERBUP, encoding="utf-8") as f:
            perbup = {r["nomor_tahun"] for r in csv.DictReader(f)}
        tabrakan = sorted({b["nomor_tahun"] for b in baris} & perbup)
        print()
        print("=" * 78)
        print("PERINGATAN: RISIKO BENTROK IDENTIFIER")
        print("=" * 78)
        print(f"Perbup di raw_documents_export.csv : {len(perbup)} identifier")
        print(f"Perda di {os.path.basename(KELUARAN)} : "
              f"{len({b['nomor_tahun'] for b in baris})} identifier")
        print(f"nomor_tahun yang SAMA di keduanya  : {len(tabrakan)}")
        if tabrakan:
            print("   contoh:", ", ".join(tabrakan[:12]))
            print("   -> identifier ini tidak unik lintas jenis dokumen.")
            print("   -> app.db tidak punya UNIQUE(nomor, tahun, jenis_dokumen),")
            print("      dan import_raw_content.py mencari dokumen hanya dengan")
            print("      nomor + tahun, jadi update konten bisa salah sasaran.")

    # duplikat di dalam Perda sendiri
    dup = [k for k, c in collections.Counter(b["nomor_tahun"] for b in baris).items() if c > 1]
    print(f"\nnomor_tahun duplikat di dalam Perda : {len(dup)}")
    if dup:
        print("   ", ", ".join(dup[:12]))


if __name__ == "__main__":
    main()
