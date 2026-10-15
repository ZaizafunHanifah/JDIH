"""
Proses SEMUA dokumen Peraturan Daerah 2020-2026: download PDF + ekstrak teks.
==============================================================================
Kebijakan hemat disk:
  - PDF langsung DIHAPUS setelah teks diekstrak (sukses maupun gagal),
    karena drive D: tinggal ~6 GB dan dokumen anggaran bisa ratusan MB.
  - Sebelum tiap download, cek sisa ruang. Di bawah MIN_FREE_GB proses
    berhenti total (bukan dipaksa lanjut).
  - Checkpoint ditulis tiap dokumen, supaya tidak ada dokumen yang hilang
    jejak kalau proses terhenti.

Checkpoint : checkpoint_ekstraksi.json
Output     : metadata_perda_final.json
Teks       : text_raw/{id}.txt
Jalankan   : python proses_semua.py
"""
import json
import os
import shutil
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from download_extract import (  # noqa: E402
    FOLDER_PDF,
    FOLDER_TEKS,
    download_pdf,
    extract_text,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
META_SUMBER = os.path.join(BASE, "metadata_perda_2020_2026.json")
CHECKPOINT = os.path.join(BASE, "checkpoint_ekstraksi.json")
OUTPUT = os.path.join(BASE, "metadata_perda_final.json")

TAHUN = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
DRIVE = os.path.dirname(os.path.dirname(BASE))
MIN_FREE_GB = 1.5
DELAY = 1.5

# Alasan gagal yang permanen: PDF scan tanpa layer teks, tidak akan pernah
# berhasil berapa kali pun dicoba (butuh OCR). Dokumen lain (gagal karena
# batas halaman/waktu) selalu dicoba ulang di run berikutnya.
PENANDA_GAGAL_PERMANEN = {"PDF hasil scan, tidak ada layer teks"}

KONSUMEN_PDF = {
    "ok": "berhasil",
    "gagal_ekstraksi": "gagal",
    "gagal_download": "gagal",
}


def free_gb(path=DRIVE):
    """Sisa ruang disk dalam GB."""
    return shutil.disk_usage(path).free / 1024**3


def simpan_json(path, data):
    """Tulis JSON secara atomik supaya file tidak korup saat proses mati."""
    sementara = path + ".tmp"
    with open(sementara, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(sementara, path)


def muat_checkpoint():
    if not os.path.exists(CHECKPOINT):
        return {}
    try:
        with open(CHECKPOINT, encoding="utf-8") as f:
            cp = json.load(f)
        print(f"[checkpoint] dimuat: {len(cp)} dokumen sudah diproses")
        return cp
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[checkpoint] gagal dibaca ({exc}), mulai dari nol")
        return {}


def hapus_pdf(path, doc_id):
    """Hapus PDF setelah diproses. File .part yang menggantung juga dibersihkan."""
    if not path:
        return
    for p in (path, path + ".part"):
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError as exc:
                print(f"    ! gagal hapus {os.path.basename(p)}: {exc}")
            else:
                if p == path:
                    print(f"    PDF dihapus: {os.path.basename(path)}")


def proses_dokumen(doc, cp):
    """
    Download + ekstrak satu dokumen, lalu simpan hasilnya ke cp.
    PDF selalu dihapus apa pun hasilnya. Return dict hasil.
    """
    doc_id = doc["id"]
    url_pdf = doc.get("url_pdf") or (
        f"https://jdih.banyumaskab.go.id/downloadprodukhukum/{doc_id}"
    )

    # 1. download
    path, dari_cache = download_pdf(doc_id, url_pdf)
    if path is None:
        return {
            "id": doc_id, "tahun": doc.get("tahun"), "status_ekstraksi": "gagal_download",
            "path_teks": None, "panjang_teks": 0, "jumlah_halaman": 0,
            "ukuran_kb": 0, "alasan": "request PDF gagal",
        }

    ukuran_kb = os.path.getsize(path) / 1024
    sumber = "cache" if dari_cache else "unduh"

    # 2. ekstrak (tidak boleh melempar keluar)
    try:
        teks, info = extract_text(path)
    except Exception as exc:
        teks = None
        info = {"jumlah_halaman": 0, "kar_teks": 0,
                "alasan": f"{type(exc).__name__}: {exc}"}
        traceback.print_exc()

    # 3. simpan teks kalau ada isinya
    path_teks = None
    if teks:
        os.makedirs(FOLDER_TEKS, exist_ok=True)
        path_teks = os.path.join(FOLDER_TEKS, f"{doc_id}.txt")
        with open(path_teks, "w", encoding="utf-8") as f:
            f.write(teks)

    # 4. PDF SELALU dihapus, sukses maupun gagal
    hapus_pdf(path, doc_id)

    if teks:
        return {
            "id": doc_id, "tahun": doc.get("tahun"), "status_ekstraksi": "ok",
            "path_teks": os.path.relpath(path_teks, BASE).replace("\\", "/"),
            "panjang_teks": len(teks), "jumlah_halaman": info.get("jumlah_halaman", 0),
            "ukuran_kb": round(ukuran_kb, 1), "alasan": None,
        }
    return {
        "id": doc_id, "tahun": doc.get("tahun"), "status_ekstraksi": "gagal_ekstraksi",
        "path_teks": None, "panjang_teks": 0,
        "jumlah_halaman": info.get("jumlah_halaman", 0),
        "ukuran_kb": round(ukuran_kb, 1),
        "alasan": info.get("alasan") or "teks kosong",
    }


def sudah_selesai(entry):
    """
    True kalau entri checkpoint menandakan pekerjaan yang SUDAH SELESAI.

    Hanya status 'ok' yang dihitung selesai. Dokumen yang gagal karena
    batas halaman/waktu akan dicoba ULANG pada run berikutnya, karena
    batasnya bisa saja sudah dinaikkan. Dokumen scan tanpa layer teks
    ditandai permanen supaya tidak diulang terus-menerus.
    """
    if not entry:
        return False
    if entry.get("status_ekstraksi") == "ok":
        return True
    return entry.get("alasan") in PENANDA_GAGAL_PERMANEN


def main():
    with open(META_SUMBER, encoding="utf-8") as f:
        semua = json.load(f)
    cp = muat_checkpoint()

    # pisahkan yang selesai vs yang perlu dicoba ulang
    gagal_lama = [i for i, e in cp.items() if not sudah_selesai(e)]
    # buang entri gagal agar dokumen itu diproses ulang dari nol
    for i in gagal_lama:
        del cp[i]
    sisa_docs = [d for d in semua if not sudah_selesai(cp.get(str(d["id"])))]

    print("=" * 78)
    print("PROSES SEMUA 92 DOKUMEN - download PDF + ekstrak teks + hapus PDF")
    print("=" * 78)
    print(f"Sisa disk awal : {free_gb():.2f} GB (henti jika < {MIN_FREE_GB} GB)")
    print(f"Total dokumen  : {len(semua)}")
    print()
    print(f"Melanjutkan dari checkpoint, {len(cp)} dokumen sudah selesai, "
          f"memproses {len(sisa_docs)} dokumen sisanya")
    if gagal_lama:
        print(f"  (diulang karena gagal sebelumnya: {', '.join(gagal_lama)})")
    print()

    berhenti = None  # (tahun, id, alesan, free_gb)
    rekap_tahun = {}

    for tahun in TAHUN:
        dok_tahun = [d for d in semua if str(d.get("tahun")) == str(tahun)]
        belum = [d for d in dok_tahun if not sudah_selesai(cp.get(str(d["id"])))]

        print("=" * 78)
        print(f"TAHUN {tahun}  ({len(dok_tahun)} dokumen, {len(belum)} belum diproses)")
        print("=" * 78)

        if not dok_tahun:
            print("  tidak ada dokumen\n")
            rekap_tahun[tahun] = {"sukses": 0, "gagal": 0, "free_gb": round(free_gb(), 2)}
            continue

        for i, doc in enumerate(dok_tahun, 1):
            doc_id = str(doc["id"])

            # --- pengaman disk SEBELUM download ---
            sisa = free_gb()
            if sisa < MIN_FREE_GB:
                berhenti = (tahun, doc_id, "disk hampir penuh", sisa)
                break

            if sudah_selesai(cp.get(doc_id)):
                print(f"  ({i}/{len(dok_tahun)}) id={doc_id} [checkpoint, dilewati]")
                continue

            hasil = proses_dokumen(doc, cp)
            cp[doc_id] = hasil

            # checkpoint tiap dokumen: PDF sudah dihapus, jadi tidak boleh
            # ada dokumen yang dikerjakan tapi tidak tercatat
            simpan_json(CHECKPOINT, cp)

            tanda = "OK " if hasil["status_ekstraksi"] == "ok" else "GAGAL"
            print(f"  ({i}/{len(dok_tahun)}) {tanda} id={doc_id} "
                  f"{hasil['ukuran_kb']:.0f}KB {hasil['jumlah_halaman']}hal "
                  f"{hasil['panjang_teks']}kar"
                  + (f" <- {hasil['alasan']}" if hasil.get("alasan") else ""))

            time.sleep(DELAY)

        # rekap per tahun: dokumen tetap dihitung sukses/gagal sesuai status
        # TERAKHIR di checkpoint (bukan hanya yang diproses run ini)
        dokids = [str(d["id"]) for d in dok_tahun]
        sukses = sum(1 for i in dokids if cp.get(i, {}).get("status_ekstraksi") == "ok")
        gagal = len(dokids) - sukses
        rekap_tahun[tahun] = {
            "sukses": sukses, "gagal": gagal, "free_gb": round(free_gb(), 2)
        }
        print(f"  --> TAHUN {tahun} SELESAI: {sukses} berhasil, {gagal} gagal, "
              f"sisa disk {free_gb():.2f} GB\n")

        if berhenti:
            break

    # --- gabungkan metadata + hasil ekstraksi ---
    final = []
    for d in semua:
        h = cp.get(str(d["id"]), {})
        gabung = dict(d)
        gabung["status_ekstraksi"] = h.get("status_ekstraksi", "belum diproses")
        gabung["path_teks"] = h.get("path_teks")
        gabung["panjang_teks"] = h.get("panjang_teks", 0)
        gabung["jumlah_halaman"] = h.get("jumlah_halaman", 0)
        gabung["ukuran_pdf_kb"] = h.get("ukuran_kb", 0)
        gabung["alasan_gagal"] = h.get("alasan")
        final.append(gabung)
    simpan_json(OUTPUT, final)

    # --- laporan akhir ---
    print("=" * 78)
    print("LAPORAN AKHIR")
    print("=" * 78)
    if berhenti:
        t, i, alasan, gb = berhenti
        print(f"!! PROSES DIHENTIKAN: {alasan}")
        print(f"   tahun {t}, dokumen id {i}")
        print(f"   sisa disk saat berhenti: {gb:.2f} GB (batas {MIN_FREE_GB} GB)")
        print()

    print(f"{'tahun':<8}{'sukses':>8}{'gagal':>8}{'sisa disk':>14}")
    for t in TAHUN:
        r = rekap_tahun.get(t)
        if r:
            print(f"{t:<8}{r['sukses']:>8}{r['gagal']:>8}{r['free_gb']:>13.2f}G")

    ok = [d for d in final if d["status_ekstraksi"] == "ok"]
    gagal = [d for d in final if d["status_ekstraksi"].startswith("gagal")]
    belum = [d for d in final if d["status_ekstraksi"] == "belum diproses"]

    print()
    print(f"Total dokumen        : {len(final)}")
    print(f"Ekstraksi berhasil   : {len(ok)}")
    print(f"Ekstraksi gagal      : {len(gagal)}")
    print(f"Belum diproses        : {len(belum)}")
    if gagal:
        print(f"  id gagal: {', '.join(str(d['id']) for d in gagal)}")
    if belum:
        print(f"  id belum: {', '.join(str(d['id']) for d in belum)}")

    if ok:
        total_kar = sum(d["panjang_teks"] for d in ok)
        rata = total_kar / len(ok)
        print(f"\nTotal teks   : {total_kar:,} karakter (rata-rata {rata:,.0f} / dokumen)")
        paling = max(ok, key=lambda d: d["panjang_teks"])
        print(f"Teks terpanjang : id {paling['id']} ({paling['panjang_teks']:,} kar, "
              f"{paling['jumlah_halaman']} hal)")

    sisa_pdf = (len(os.listdir(FOLDER_PDF))
                if os.path.isdir(FOLDER_PDF) else 0)
    print(f"\nSisa file PDF di pdf_raw : {sisa_pdf} (harusnya 0)")
    print(f"Sisa ruang disk          : {free_gb():.2f} GB")
    print(f"Output : {os.path.basename(OUTPUT)}")
    print(f"Checkpoint: {os.path.basename(CHECKPOINT)}")


if __name__ == "__main__":
    main()
