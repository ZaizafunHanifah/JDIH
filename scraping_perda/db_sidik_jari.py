"""Sidik jari penuh DB sebelum & sesudah uji pengaman, untuk membuktikan
tidak ada data yang berubah (bukan hanya jumlah baris)."""
import hashlib, json, sqlite3, sys

mode = sys.argv[1]
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

conn = sqlite3.connect("jdih.db")


def tabel(nama, kolom):
    out = []
    for r in conn.execute(f"SELECT {kolom} FROM {nama} ORDER BY rowid"):
        out.append(hashlib.sha256(repr(r[0]).encode()).hexdigest()[:12])
    return {"n": len(out), "hash": hashlib.sha256("".join(out).encode()).hexdigest()}


snap = {
    "documents": tabel("documents", "id,judul,nomor,tanggal_terbit,jenis_dokumen,"
                                  "url_pdf,konten_text,konten_text_asli,status_hukum,"
                                  "catatan_relasi,nomor_tahun"),
    "topics": tabel("topics", "id,label_topik,top_keywords"),
    "document_topics": tabel("document_topics", "document_id,topic_id"),
    "jumlah": conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
    "per_jenis": dict(conn.execute("SELECT jenis_dokumen, COUNT(*) FROM documents "
                                   "GROUP BY jenis_dokumen").fetchall()),
}
with open(f"scraping_perda/db_sidik_{mode}.json", "w", encoding="utf-8") as f:
    json.dump(snap, f, ensure_ascii=False, indent=2)
print(f"mode={mode}  dokumen={snap['jumlah']}  per_jenis={snap['per_jenis']}  "
      f"docs_hash={snap['documents']['hash'][:16]}  topics_hash={snap['topics']['hash'][:16]}")
