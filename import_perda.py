"""
Import 83 dokumen Peraturan Daerah ke jdih.db.
=================================================
Membaca perda_export.csv, menambahkan prefix 'perda_' pada identifier
agar tidak bentrok dengan Perbup, lalu INSERT (bukan replace).

Perbedaan penting dari import_real_data.py:
  - TIDAK menghapus data yang sudah ada
  - Idempotent: dokumen yang identifier-nya sudah ada dilewati
  - Topik diambil dari kolom `topik` di CSV, TIDAK dihitung ulang

Jalankan: python import_perda.py
"""
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db, init_db

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_LOKAL = os.path.join(BASE, "scraping_perda", "perda_export.csv")
CSV_ROOT = os.path.join(BASE, "perda_export.csv")

PREFIX = "perda_"
JENIS = "Peraturan Daerah"
TEMPAT_TERBIT = "{tahun}-01-01"  # placeholder, sama seperti Perbup

csv.field_size_limit(100000000)


def siapkan_csv():
    """Pastikan CSV ada di root; copy dari scraping_perda/ bila perlu."""
    if os.path.exists(CSV_ROOT):
        return CSV_ROOT
    if os.path.exists(CSV_LOKAL):
        import shutil
        shutil.copy2(CSV_LOKAL, CSV_ROOT)
        print(f"[csv] disalin ke root: {CSV_ROOT}")
        return CSV_ROOT
    raise FileNotFoundError(
        f"CSV tidak ditemukan di {CSV_LOKAL} maupun {CSV_ROOT}")


def baca_rows(path):
    with io.open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def import_perda():
    csv_path = siapkan_csv()
    rows = baca_rows(csv_path)
    print(f"CSV  : {csv_path}")
    print(f"Baris: {len(rows)}")
    print(f"Prefix identifier: {PREFIX!r}")
    print()

    init_db()  # menambah kolom status_hukum / catatan_relasi bila belum ada

    with get_db() as conn:
        # pastikan label topik ada (ikut terisi oleh import Perbup)
        label_di_db = {r[0] for r in conn.execute("SELECT label_topik FROM topics")}
        topik_baru = 0

        inserted = 0
        skipped = 0
        tanpa_topik = 0
        relasi = 0

        for r in rows:
            nomor = (r.get("nomor") or "").strip()
            tahun = (r.get("tahun") or "").strip()
            identifier = f"{PREFIX}{nomor}_{tahun}"   # mis. perda_1_2020

            judul = (r.get("judul") or "").strip()
            if not judul:
                print(f"  ! dilewati (judul kosong): {identifier}")
                skipped += 1
                continue

            # --- cek idempotensi: sudah ada? ---
            cols = {c[1] for c in conn.execute("PRAGMA table_info(documents)")}
            if "nomor_tahun" in cols:
                ada = conn.execute(
                    "SELECT id FROM documents WHERE nomor_tahun = ?", (identifier,)
                ).fetchone()
            else:
                ada = conn.execute(
                    "SELECT id FROM documents WHERE jenis_dokumen = ? AND nomor = ? "
                    "AND substr(tanggal_terbit, 1, 4) = ?",
                    (JENIS, nomor, tahun),
                ).fetchone()
            if ada:
                print(f"  - sudah ada, dilewati: {identifier}")
                skipped += 1
                continue

            isi = {
                "judul": judul,
                "nomor": nomor,
                "tanggal_terbit": TEMPAT_TERBIT.format(tahun=tahun),
                "jenis_dokumen": JENIS,
                "url_pdf": (r.get("url_pdf") or "").strip(),
                "konten_text": r.get("konten_text") or "",
                "konten_text_asli": r.get("konten_text_asli") or "",
            }
            if "nomor_tahun" in cols:
                isi["nomor_tahun"] = identifier
            if "status_hukum" in cols:
                isi["status_hukum"] = (r.get("status_hukum") or "").strip() or None
            if "catatan_relasi" in cols:
                isi["catatan_relasi"] = (r.get("catatan_relasi") or "").strip() or None

            kolom = list(isi)
            cur = conn.execute(
                f"INSERT INTO documents ({', '.join(kolom)}) "
                f"VALUES ({', '.join('?' * len(kolom))})",
                tuple(isi[k] for k in kolom),
            )
            doc_id = cur.lastrowid
            inserted += 1

            # --- relasi topik: PAKAI kolom topik dari CSV, jangan hitung ulang ---
            label = (r.get("topik") or "").strip()
            if not label:
                tanpa_topik += 1
            for lab in [x.strip() for x in label.split(";") if x.strip()]:
                row_t = conn.execute(
                    "SELECT id FROM topics WHERE label_topik = ?", (lab,)
                ).fetchone()
                if row_t:
                    conn.execute(
                        "INSERT OR IGNORE INTO document_topics "
                        "(document_id, topic_id) VALUES (?, ?)",
                        (doc_id, row_t[0]),
                    )
                    relasi += 1
                else:
                    topik_baru += 1
                    print(f"  ! label topik tidak dikenal: {lab!r} "
                          f"(dokumen {identifier})")
            print(f"  + {identifier:<14} id={doc_id:<5} "
                  f"topik={label or '(tanpa topik)'}")

        conn.commit()

    print()
    print("=" * 78)
    print("RINGKASAN IMPORT")
    print("=" * 78)
    print(f"  dokumen di CSV        : {len(rows)}")
    print(f"  berhasil di-insert    : {inserted}")
    print(f"  dilewati (sudah ada)  : {skipped}")
    print(f"  relasi topik dibuat   : {relasi}")
    print(f"  dokumen tanpa topik    : {tanpa_topik}")
    print(f"  label topik tak dikenal: {topik_baru}")
    print(f"\n  topics yang dikenal sistem: {len(label_di_db)}")


if __name__ == "__main__":
    import_perda()
