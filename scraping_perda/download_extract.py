"""
Download PDF Peraturan Daerah + ekstraksi teks.
==============================================
TEST KECIL: hanya 3 dokumen tahun 2026 (dari test_2026.json).

Sumber PDF : /downloadprodukhukum/{doc_id}   (pola sudah diverifikasi, HTTP 200, %PDF-1.7)
Simpan PDF : scraping_perda/pdf_raw/{doc_id}.pdf
Simpan teks: scraping_perda/text_raw/{doc_id}.txt

Catatan: scraping_perda/test_2026.json hanya berisi tahun 2026, jadi file ini
memproses dokumen dari file tersebut - BUKAN 92 dokumen scope penuh.
Jalankan: python download_extract.py
"""
import json
import os
import re
import sys
import time

import pdfplumber
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
FOLDER_PDF = os.path.join(BASE, "pdf_raw")
FOLDER_TEKS = os.path.join(BASE, "text_raw")
INPUT_JSON = os.path.join(BASE, "test_2026.json")

DELAY = 1.5
TIMEOUT = 120
# Batas keras per dokumen: PDF bureaucracy bisa ribuan halaman
# (terverifikasi: id 4947 = 1458 halaman) dan pdfplumber bisa berjalan
# sangat lama. Dokumen yang melewati batas ditandai, tidak digagalkan diam-diam.
# 1000 halaman + 180 detik cukup untuk dokumen anggaran non-scan:
# contoh sukses 3632 (151 hal / 390.045 kar) dan 3285 (93 hal / 172.160 kar).
BATAS_HALAMAN = 1000
BATAS_WAKTU_DETIK = 180
# Halaman sampel untuk memutuskan "PDF scan atau bukan" sebelum ekstrak semua.
# JANGAN diubah: ini yang menyaring dokumen scan tanpa layer teks
# (4277, 3628, 4182, 4437) yang tidak bisa diproses tanpa OCR.
HALAMAN_SAMPEL = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
    "Referer": "https://jdih.banyumaskab.go.id/",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def download_pdf(doc_id, url_pdf, folder=FOLDER_PDF):
    """
    Download PDF ke {folder}/{doc_id}.pdf.
    Idempotent: kalau file sudah ada, tidak di-download ulang.
    Return (path, dipcache) atau (None, False) bila gagal.
    """
    os.makedirs(folder, exist_ok=True)
    tujuan = os.path.join(folder, f"{doc_id}.pdf")

    if os.path.exists(tujuan) and os.path.getsize(tujuan) > 0:
        return tujuan, True

    try:
        # stream=True supaya file besar tidak menahan seluruh isi di memori
        with SESSION.get(url_pdf, timeout=TIMEOUT, stream=True) as resp:
            if resp.status_code != 200:
                print(f"    ! HTTP {resp.status_code} untuk {url_pdf}")
                return None, False

            # tulis ke file sementara dulu, rename bila selesai,
            # supaya file tidak pernah ada dalam keadaan setengah jadi
            sementara = tujuan + ".part"
            total = 0
            with open(sementara, "wb") as f:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)
            os.replace(sementara, tujuan)

        if total == 0:
            print("    ! file PDF kosong (0 byte)")
            os.remove(tujuan)
            return None, False
        return tujuan, False
    except Exception as exc:
        print(f"    ! gagal download: {type(exc).__name__}: {exc}")
        return None, False


def extract_text(pdf_path):
    """
    Ekstrak teks dari PDF, digabung jadi satu string.
    Return (teks, info) dengan:
      teks : string gabungan, atau None jika kosong/gagal/tidakenger
      info : dict berisi jumlah_halaman, kar_teks, dan alasan jika tidak jadi

    Return None jika file tidak bisa dibuka atau teks kosong
    (mis. PDF hasil scan tanpa layer teks).
    """
    info = {"jumlah_halaman": 0, "kar_teks": 0, "alasan": None}
    if not pdf_path or not os.path.exists(pdf_path):
        info["alasan"] = "file tidak ditemukan"
        return None, info

    mulai = time.time()
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_halaman = len(pdf.pages)
            info["jumlah_halaman"] = total_halaman

            if total_halaman == 0:
                info["alasan"] = "PDF tanpa halaman"
                return None, info

            # 1) Sampling halaman awal: PDF scan biasanya tanpa teks sama sekali
            #    di halaman mana pun. Ini menghemat waktu untuk file 1000+ halaman.
            cuplikan = ""
            for halaman in pdf.pages[:HALAMAN_SAMPEL]:
                try:
                    cuplikan += (halaman.extract_text() or "") + "\n"
                except Exception:
                    pass
                if time.time() - mulai > BATAS_WAKTU_DETIK:
                    info["alasan"] = f"timeout saat sampling ({BATAS_WAKTU_DETIK}s)"
                    return None, info

            if not cuplikan.strip():
                info["alasan"] = "PDF hasil scan, tidak ada layer teks"
                return None, info

            # 2) Ekstrak semua halaman (mulai dari nol, sampling tadi tidak disimpan)
            if total_halaman > BATAS_HALAMAN:
                info["alasan"] = (
                    f"PDF sangat besar ({total_halaman} halaman, "
                    f"batas {BATAS_HALAMAN}), dilewati"
                )
                return None, info

            bagian = []
            for i, halaman in enumerate(pdf.pages, 1):
                try:
                    bagian.append(halaman.extract_text() or "")
                except Exception:
                    bagian.append("")
                if time.time() - mulai > BATAS_WAKTU_DETIK:
                    info["alasan"] = (
                        f"timeout {BATAS_WAKTU_DETIK}s di halaman {i}/{total_halaman}"
                    )
                    return None, info

        teks = "\n".join(bagian).strip()
        info["kar_teks"] = len(teks)
        if not teks:
            info["alasan"] = "teks hasil ekstraksi kosong"
            return None, info
        return teks, info
    except Exception as exc:
        info["alasan"] = f"{type(exc).__name__}: {exc}"
        print(f"    ! gagal ekstrak: {info['alasan']}")
        return None, info


def main():
    print("=" * 78)
    print("DOWNLOAD PDF + EKSTRAK TEKS - TEST 3 DOKUMEN TAHUN 2026")
    print("=" * 78)

    with open(INPUT_JSON, encoding="utf-8") as f:
        dokumen = json.load(f)
    print(f"Input : {os.path.basename(INPUT_JSON)} ({len(dokumen)} dokumen)")
    print(f"PDF   : {FOLDER_PDF}")
    print(f"Teks  : {FOLDER_TEKS}\n")

    ringkasan = []
    total = len(dokumen)

    for i, d in enumerate(dokumen, 1):
        doc_id = d["id"]
        url_pdf = d.get("url_pdf") or f"https://jdih.banyumaskab.go.id/downloadprodukhukum/{doc_id}"
        print("-" * 78)
        print(f"({i}/{total}) id={doc_id} | {d.get('no_peraturan')}/{d.get('tahun')}")
        print(f"  judul: {(d.get('judul') or '')[:100]}")

        # 1. download (selalu dicoba, tidak fatal)
        path, dari_cache = download_pdf(doc_id, url_pdf)
        if path is None:
            print("  DOWNLOAD GAGAL")
            ringkasan.append({
                "id": doc_id, "status": "gagal_download", "ukuran_kb": 0,
                "jumlah_halaman": 0, "karakter": 0,
                "alasan": "request PDF gagal",
            })
            if i < total:
                time.sleep(DELAY)
            continue

        ukuran_kb = os.path.getsize(path) / 1024
        print(f"  PDF: {os.path.basename(path)} | {ukuran_kb:.1f} KB "
              f"({'dari cache' if dari_cache else 'baru di-download'})")

        # 2. ekstrak (selalu dicoba, tidak fatal)
        try:
            teks, info = extract_text(path)
        except Exception as exc:
            teks, info = None, {"jumlah_halaman": 0, "kar_teks": 0,
                                "alasan": f"{type(exc).__name__}: {exc}"}

        if teks is None:
            print(f"  EKSTRAKSI GAGAL: {info.get('alasan')} "
                  f"({info.get('jumlah_halaman', 0)} halaman)")
            ringkasan.append({
                "id": doc_id, "status": "teks_kosong",
                "ukuran_kb": round(ukuran_kb, 1),
                "jumlah_halaman": info.get("jumlah_halaman", 0),
                "karakter": 0,
                "alasan": info.get("alasan"),
            })
            if i < total:
                time.sleep(DELAY)
            continue

        # 3. simpan teks
        os.makedirs(FOLDER_TEKS, exist_ok=True)
        with open(os.path.join(FOLDER_TEKS, f"{doc_id}.txt"), "w", encoding="utf-8") as f:
            f.write(teks)

        print(f"  Halaman : {info['jumlah_halaman']}")
        print(f"  Teks    : {len(teks)} karakter, {len(teks.split())} kata")
        print(f"  200 char pertama:")
        print(f"    {norm(teks)[:200]}")

        ringkasan.append({
            "id": doc_id, "status": "ok",
            "ukuran_kb": round(ukuran_kb, 1),
            "jumlah_halaman": info["jumlah_halaman"],
            "karakter": len(teks),
        })

        if i < total:
            time.sleep(DELAY)

    print("-" * 78)
    print()
    print("=" * 78)
    print("RINGKASAN")
    print("=" * 78)
    print(f"{'id':<8}{'status':<16}{'KB':>10}{'hal':>7}{'karakter':>11}  alasan")
    for r in ringkasan:
        print(f"{r['id']:<8}{r['status']:<16}{r['ukuran_kb']:>10.1f}"
              f"{r['jumlah_halaman']:>7}{r['karakter']:>11}  {r.get('alasan') or ''}")
    ok = sum(1 for r in ringkasan if r["status"] == "ok")
    print(f"\nberhasil ekstrak : {ok}/{len(ringkasan)}")
    print(f"PDF tersimpan    : {FOLDER_PDF}")
    print(f"Teks tersimpan   : {FOLDER_TEKS}")

    with open(os.path.join(BASE, "test_2026_extract.json"), "w", encoding="utf-8") as f:
        json.dump(ringkasan, f, ensure_ascii=False, indent=2)
    print(f"Ringkasan        : test_2026_extract.json")


if __name__ == "__main__":
    main()
