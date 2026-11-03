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
TEMPAT_TERBIT = "{tahun}-01-01"

csv.field_size_limit(100000000)


def siapkan_csv():
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

    init_db()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT label_topik FROM topics")
            label_di_db = {r[0] for r in cur.fetchall()}
            topik_baru = 0

            inserted = 0
            skipped = 0
            tanpa_topik = 0
            relasi = 0

            for r in rows:
                nomor = (r.get("nomor") or "").strip()
                tahun = (r.get("tahun") or "").strip()
                identifier = f"{PREFIX}{nomor}_{tahun}"

                judul = (r.get("judul") or "").strip()
                if not judul:
                    print(f"  ! dilewati (judul kosong): {identifier}")
                    skipped += 1
                    continue

                cur.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'documents'"
                )
                cols = {row[0] for row in cur.fetchall()}

                if "nomor_tahun" in cols:
                    cur.execute(
                        "SELECT id FROM documents WHERE nomor_tahun = %s", (identifier,)
                    )
                else:
                    cur.execute(
                        "SELECT id FROM documents WHERE jenis_dokumen = %s AND nomor = %s "
                        "AND SUBSTRING(tanggal_terbit, 1, 4) = %s",
                        (JENIS, nomor, tahun),
                    )
                ada = cur.fetchone()

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
                placeholders = ", ".join(["%s"] * len(kolom))
                sql = f"INSERT INTO documents ({', '.join(kolom)}) VALUES ({placeholders}) RETURNING id"
                
                cur.execute(sql, tuple(isi[k] for k in kolom))
                doc_id = cur.fetchone()[0]
                inserted += 1

                label = (r.get("topik") or "").strip()
                if not label:
                    tanpa_topik += 1
                for lab in [x.strip() for x in label.split(";") if x.strip()]:
                    cur.execute(
                        "SELECT id FROM topics WHERE label_topik = %s", (lab,)
                    )
                    row_t = cur.fetchone()
                    if row_t:
                        cur.execute(
                            "INSERT INTO document_topics (document_id, topic_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            (doc_id, row_t[0]),
                        )
                        relasi += 1
                    else:
                        topik_baru += 1
                        print(f"  ! label topik tidak dikenal: {lab!r} (dokumen {identifier})")
                print(f"  + {identifier:<14} id={doc_id:<5} topik={label or '(tanpa topik)'}")

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


if __name__ == "__main__":
    import_perda()