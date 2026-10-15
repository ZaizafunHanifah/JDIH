"""Snapshot state DB sebelum import Perda (untuk pembuktian 'Perbup tidak berubah')."""
import json
import os
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DB = os.path.join(ROOT, "jdih.db")
OUT = os.path.join(BASE, "snapshot_sebelum_perda.json")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT d.id, d.nomor, d.tanggal_terbit, d.judul, d.url_pdf,
           d.jenis_dokumen, d.konten_text, d.konten_text_asli,
           (SELECT GROUP_CONCAT(t.label_topik, '||') FROM document_topics dt
             JOIN topics t ON t.id = dt.topic_id
             WHERE dt.document_id = d.id) AS kat
    FROM documents d
    ORDER BY d.id
""").fetchall()

data = {
    "jumlah": len(rows),
    "id_tertinggi": max(r["id"] for r in rows),
    "docs": [{
        "id": r["id"], "nomor": r["nomor"], "tahun": (r["tanggal_terbit"] or "")[:4],
        "judul": r["judul"], "jenis": r["jenis_dokumen"],
        "len_teks": len(r["konten_text"] or ""),
        "len_asli": len(r["konten_text_asli"] or ""),
        "url": r["url_pdf"], "kat": r["kat"] or "",
    } for r in rows],
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

topik = dict(conn.execute(
    "SELECT t.label_topik, COUNT(*) FROM document_topics dt "
    "JOIN topics t ON t.id=dt.topic_id GROUP BY t.label_topik").fetchall())

print(f"snapshot ditulis : {OUT}")
print(f"jumlah dokumen   : {data['jumlah']}")
print(f"id tertinggi     : {data['id_tertinggi']}")
print(f"distribusi topik : {topik}")
conn.close()
