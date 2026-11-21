"""
Export hasil olahan dari database ke CSV.

Kolom yang diexport: id, judul, nomor, tanggal_terbit, jenis_dokumen,
konten_text_asli, konten_tsv, nomor_tahun.

Cara pakai:
    python export_hasil.py --output hasil.csv
    python export_hasil.py --output hasil.csv --limit 100
    python export_hasil.py --output hasil.csv --only-with-text

Env yang dibutuhkan: DB_PASSWORD (dan opsional DB_HOST/PORT/NAME/USER).
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db


def export(output_path: str, limit: int | None = None, only_with_text: bool = False):
    query = """
        SELECT id, judul, nomor, tanggal_terbit, jenis_dokumen,
               konten_text_asli, konten_tsv, nomor_tahun
        FROM documents
    """
    if only_with_text:
        query += " WHERE konten_text_asli IS NOT NULL AND konten_text_asli <> ''"
    query += " ORDER BY id"

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            cols = [d.name for d in cur.description]

    if limit:
        rows = rows[:limit]

    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        for r in rows:
            vals = []
            for c in cols:
                v = r[c]
                if v is None:
                    vals.append("")
                elif isinstance(v, str) and len(v) > 32000:
                    vals.append(v[:32000])
                else:
                    vals.append(str(v))
            writer.writerow(vals)

    print(f"Export selesai: {output_path}")
    print(f"Total baris: {len(rows)}")


def main():
    parser = argparse.ArgumentParser(description="Export hasil olahan ke CSV")
    parser.add_argument("--output", required=True, help="Path file CSV output")
    parser.add_argument("--limit", type=int, default=None, help="Batasi jumlah baris")
    parser.add_argument("--only-with-text", action="store_true", help="Hanya export dokumen yang punya konten_text_asli")
    args = parser.parse_args()

    export(args.output, limit=args.limit, only_with_text=args.only_with_text)


if __name__ == "__main__":
    main()