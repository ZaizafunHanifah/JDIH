"""Catat sidik jari konten_text_asli SEBELUM import_raw_content.py,
lalu bandingkan SESUDAH. Bukti 0 baris Perda tertimpa.
Jalankan: python scraping_perda/sidik_jari_raw_content.pyHitam <sebelum|sesudah>
"""
import hashlib, sqlite3, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

mode = sys.argv[1] if len(sys.argv) > 1 else "sebelum"
conn = sqlite3.connect("jdih.db")
conn.row_factory = sqlite3.Row


def fp(t):
    if t is None:
        return "NULL"
    return f"{len(t)}:{hashlib.sha256(t.encode('utf-8')).hexdigest()[:16]}"


rows = conn.execute("""
    SELECT id, nomor_tahun, jenis_dokumen, konten_text_asli
    FROM documents WHERE jenis_dokumen='Peraturan Daerah' ORDER BY nomor_tahun
""").fetchall()

jalur = f"scraping_perda/sidik_perda_{mode}.txt"
with open(jalur, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(f"{r['id']}\t{r['nomor_tahun']}\t{fp(r['konten_text_asli'])}\n")

terisi = sum(1 for r in rows if r["konten_text_asli"])
print(f"mode={mode}  Perda={len(rows)}  konten_text_asli terisi={terisi}  -> {jalur}")
