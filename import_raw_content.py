import csv
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.db import get_db

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw_content_export.csv")

csv.field_size_limit(sys.maxsize)

total_rows = 0
updated = 0
empty_content = 0
missing = []

with open(CSV_PATH, newline="", encoding="utf-8", errors="replace") as f:
    reader = csv.reader(f)
    header = next(reader)

    with get_db() as conn:
        for row in reader:
            total_rows += 1
            nomor_tahun = row[0].strip()
            konten_mentah = row[1] if len(row) > 1 else ""

            parts = nomor_tahun.rsplit("_", 1)
            if len(parts) != 2:
                missing.append(nomor_tahun)
                continue

            nomor, tahun = parts[0], parts[1]

            if not konten_mentah.strip():
                empty_content += 1
                continue

            cursor = conn.execute(
                "SELECT id FROM documents WHERE nomor = ? AND substr(tanggal_terbit, 1, 4) = ?",
                (nomor, tahun),
            )
            doc = cursor.fetchone()

            if doc:
                conn.execute(
                    "UPDATE documents SET konten_text_asli = ? WHERE id = ?",
                    (konten_mentah, doc[0]),
                )
                updated += 1
            else:
                missing.append(nomor_tahun)

        conn.commit()

print(f"Total baris di CSV: {total_rows}")
print(f"Total berhasil di-update: {updated}")
print(f"Total konten_mentah kosong (tidak diupdate): {empty_content}")
if missing:
    print(f"Total tidak ketemu di database: {len(missing)}")
else:
    print("Total tidak ketemu di database: 0")
