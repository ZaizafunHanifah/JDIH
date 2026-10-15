"""Cek apakah 3 keyword baru benar-benar bekerja (bukan hanya tak terpakai)."""
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
sys.path.insert(0, ROOT)
from import_real_data import TOPICS, match_topics  # noqa: E402

KAT = "Per.encodercancer if False else 'Perencanaan Pembangunan Daerah'"
KAT = "Perencanaan Pembangunan Daerah"

def trig(judul, kat):
    jl = (judul or "").lower()
    return [kw for kw in TOPICS[kat]
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", jl)]

print("TEST 1: keyword 'perseroan' (ganti 'persero')")
for t in ["perseroan", "perseroan terbatas", "perseroda", "PT Persero"]:
    jl = t.lower()
    lama = re.search(r"\bpersero\b", jl) is not None
    baru = re.search(r"\bperseroan\b", jl) is not None
    print(f"  {t!r:26} \bpersero\b={lama!s:<6} \bperseroan\b={baru}")

print()
print("TEST 2: keyword 'perumdam'")
for t in ["perumdam", "perumda", "perumda bpd"]:
    jl = t.lower()
    print(f"  {t!r:26} \bperumdam\b="
          f"{re.search(r'perumdam', jl) is not None}"
          f"  \bperumda\b={re.search(r'perumda', jl) is not None}")

print()
print("=" * 78)
print("DOKUMEN PERDA YANG MENGANDUNG 'perseroan' / 'perumdam'")
print("=" * 78)
import csv
csv.field_size_limit(100000000)
with io.open(os.path.join(BASE, "perda_export.csv"), encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

for r in rows:
    jl = r["judul"].lower()
    if re.search(r"perseroan|perumdam|persero|perumda", jl):
        print(f"\n  [{r['nomor_tahun']}] {r['judul'].strip()[:88]}")
        print(f"     keyword match: {trig(r['judul'], KAT)}")
        print(f"     kategori    : {match_topics(r['judul'])}")
        print(f"     kolom topik di CSV (lama): {r.get('topik','')!r}")

print()
print("=" * 78)
print("PERBUP: cek juga (baca dari DB read-only)")
print("=" * 78)
import sqlite3
DB = os.path.join(ROOT, "jdih.db")
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
for r in conn.execute("SELECT nomor, substr(tanggal_terbit,1,4) th, judul FROM documents"):
    jl = (r["judul"] or "").lower()
    if re.search(r"perseroan|perumdam|persero|perumda", jl):
        nt = f"{str(r['nomor']).strip()}_{r['th'].strip()}"
        print(f"  [{nt}] {r['judul'].strip()[:80]}")
        print(f"     keyword: {trig(r['judul'], KAT)}  ->  {match_topics(r['judul'])}")
conn.close()
