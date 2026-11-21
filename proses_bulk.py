"""
Proses bulk PDF dari satu folder.

Cara pakai:
    python proses_bulk.py --folder ./pdf_input
    python proses_bulk.py --folder ./pdf_input --judul-prefix "Peraturan"

Env yang dibutuhkan: DB_PASSWORD (dan opsional DB_HOST/PORT/NAME/USER).
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db, init_db
from app.pdf_extractor import deteksi_metadata, ekstrak_teks


def proses_satu_pdf(file_path: Path, judul_override: str = "") -> dict:
    """Ekstrak teks + simpan ke database. Return dict hasil."""
    try:
        teks = file_path.read_bytes()
    except Exception as e:
        return {"status": "gagal", "pesan": f"Gagal baca file: {e}", "file": str(file_path)}

    hasil = ekstrak_teks(teks)
    if hasil["status"] == "rusak":
        return {"status": "gagal", "pesan": hasil["pesan"], "file": str(file_path)}
    if hasil["status"] == "tanpa_teks":
        return {"status": "tanpa_teks", "pesan": hasil["pesan"], "file": str(file_path)}

    konten_text_asli = hasil["konten_text_asli"]
    metadata = deteksi_metadata(konten_text_asli)

    judul = (judul_override or metadata["judul"] or "").strip()
    jenis_dokumen = metadata["jenis_dokumen"] or ""
    nomor = metadata["nomor"] or ""
    tahun = metadata["tahun"] or ""
    tanggal_terbit = f"{tahun}-01-01" if tahun else ""
    nomor_tahun = f"{nomor}/{tahun}" if nomor and tahun else ""

    konten_text = re.sub(r"\s+", " ", konten_text_asli).strip()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents
                (judul, nomor, tanggal_terbit, jenis_dokumen, konten_text_asli, konten_text, nomor_tahun)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (judul, nomor, tanggal_terbit, jenis_dokumen, konten_text_asli, konten_text, nomor_tahun or None))
            new_id = cur.fetchone()[0]

    return {
        "status": "berhasil",
        "file": str(file_path),
        "id": new_id,
        "judul": judul,
        "jenis_dokumen": jenis_dokumen,
        "nomor": nomor,
        "tahun": tahun,
        "jumlah_karakter": len(konten_text_asli),
    }


def main():
    parser = argparse.ArgumentParser(description="Proses bulk PDF -> simpan ke database")
    parser.add_argument("--folder", required=True, help="Folder berisi file PDF")
    parser.add_argument("--judul-prefix", default="", help="Prefix judul untuk semua PDF (opsional)")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"ERROR: Folder tidak ditemukan: {folder}", file=sys.stderr)
        sys.exit(1)

    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        print(f"Tidak ada file PDF di {folder}", file=sys.stderr)
        sys.exit(1)

    print(f"Menemukan {len(pdf_files)} file PDF. Memulai proses...\n")

    init_db()

    sukses = 0
    gagal = 0
    tanpa_teks = 0

    for i, pdf in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Memproses: {pdf.name}")
        hasil = proses_satu_pdf(pdf, judul_override=args.judul_prefix)

        if hasil["status"] == "berhasil":
            sukses += 1
            print(f"  OK -> id={hasil['id']} judul={hasil['judul']} teks={hasil['jumlah_karakter']} char")
        elif hasil["status"] == "tanpa_teks":
            tanpa_teks += 1
            print(f"  SKIP -> {hasil['pesan']}")
        else:
            gagal += 1
            print(f"  FAIL -> {hasil['pesan']}")

    print(f"\n=== RINGKASAN ===")
    print(f"Total PDF       : {len(pdf_files)}")
    print(f"Sukses          : {sukses}")
    print(f"Tanpa teks      : {tanpa_teks}")
    print(f"Gagal           : {gagal}")


if __name__ == "__main__":
    main()