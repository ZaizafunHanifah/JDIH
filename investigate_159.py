import re
import sqlite3

conn = sqlite3.connect("jdih.db")
conn.row_factory = sqlite3.Row

row = conn.execute("SELECT id, nomor, konten_text_asli FROM documents WHERE id = 159").fetchone()

print(f"=== Document ID 159 ===")
print(f"id: {row['id']}")
print(f"nomor: {row['nomor']}")

if row["konten_text_asli"] is None:
    print("konten_text_asli: NULL")
else:
    text = row["konten_text_asli"]
    print(f"konten_text_asli: NOT NULL")
    print(f"Panjang karakter: {len(text)}")
    print(f"\n--- MEMUTUSKAN search ---")
    m = re.search(r"MEMUTUSKAN", text, re.IGNORECASE)
    if m:
        print(f"Ditemukan di posisi: {m.start()}")
        start = max(0, m.start() - 100)
        end = min(len(text), m.end() + 300)
        context = text[start:end]
        print(f"\nKonteks (300 karakter setelah):")
        print(repr(context))
    else:
        print("TIDAK ditemukan MEMUTUSKAN")
