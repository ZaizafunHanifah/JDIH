"""DRY RUN - tidak mengubah DB sama sekali.
Menghitung berapa pasal/prosedural yang AKAN didapat bila konten_text_asli
Perbup diisi dari raw_content_export.csv (sumber yang sama dengan
import_raw_content.py), sekaligus mendeteksi dokumen mana yang akan salah
kena karena bentrok nomor Perbup/Perda.
"""
import csv, re, sqlite3, sys
sys.path.insert(0, ".")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from app.pasal_extractor import extract_pasal

csv.field_size_limit(sys.maxsize)
rows = list(csv.reader(open("raw_content_export.csv", newline="", encoding="utf-8",
                            errors="replace")))
header, body = rows[0], rows[1:]

conn = sqlite3.connect("jdih.db")
conn.row_factory = sqlite3.Row

# replica lookup import_raw_content.py persis (tanpa jenis_dokumen)
bentrok = 0
pairs = []
for r in body:
    nt = r[0].strip()
    parts = nt.rsplit("_", 1)
    if len(parts) != 2:
        continue
    nomor, tahun = parts
    d = conn.execute("SELECT id, jenis_dokumen FROM documents WHERE nomor=? "
                     "AND substr(tanggal_terbit,1,4)=?", (nomor, tahun)).fetchone()
    if d and d["jenis_dokumen"] != "Peraturan Bupati":
        bentrok += 1
        pairs.append((nt, d["jenis_dokumen"]))

print("SIMULASI: isi konten_text_asli Perbup dari raw_content_export.csv")
print("=" * 84)
dok = pal = pros = 0
semu = []
for r in body:
    nt = r[0].strip()
    if len(nt.rsplit("_", 1)) != 2:
        continue
    t = r[1] if len(r) > 1 else ""
    if not t.strip():
        continue
    ps = extract_pasal(t)
    if ps:
        dok += 1
    pal += len(ps)
    pros += sum(1 for p in ps if p["is_procedural"])
    semu.append((nt, len(ps), sum(1 for p in ps if p["is_procedural"])))
print(f"  baris CSV diproses      : {len(semu)}")
print(f"  Perbup dengan >=1 pasal : {dok}   (sekarang 0)")
print(f"  total pasal Perbup      : {pal}   (sekarang 0)")
print(f"  prosedural Perbup       : {pros}   (sekarang 0)")
print(f"  0 pasal                 : {len(semu)-dok}")

print("\n  GABUNGAN 469 bila Perbup diisi:")
print(f"    dokumen dengan pasal  : {dok + 80} / 469")
print(f"    total pasal           : {pal + 2774}")
print(f"    total prosedural      : {pros + 1825}")

print("\n  RISIKO import_raw_content.py sekarang:")
print(f"    baris yang lookup-nya jatuh ke dokumen Perda : {bentrok}")
if pairs:
    for nt, j in pairs[:8]:
        print(f"      {nt:<14} -> {j}")
    print("    (karena lookup tidak memfilter jenis_dokumen; urutan id membuat")
    print("     Perbup Supplemental lebih dulu, jadi aman - tapi rapuh)")

# apakah isi raw_content_export cocok dengan loss CSVenb隐蔽 Perbup
print("\n  Cek konsistensi: apakah konten_text Perbup = konten_mentah CSV?")
d = conn.execute("SELECT id,konten_text FROM documents WHERE jenis_dokumen="
                 "'Peraturan Bupati' AND nomor='1' AND substr(tanggal_terbit,1,4)='2020'").fetchone()
raw = next((r[1] for r in body if r[0].strip() == "1_2020"), "")
print(f"    len konten_text DB  : {len(d['konten_text'])}")
print(f"    len konten_mentah CSV: {len(raw)}")
print(f"    sama persis          : {d['konten_text'] == raw}")
