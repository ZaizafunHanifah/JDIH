"""
Jalankan extract_pasal() (v2, apa adanya) pada 83 Perda.
Diagnosa dokumen 0 pasal: MEMUTUSKAN hilang? pola 'Pasal N' sendiri di baris
tidak cocok? loncat nomor > MAX_LONJAT_NOMOR?
Tidak mengubah app/pasal_extractor.py sama sekali.
Jalankan: python scraping_perda/ekstrak_pasal_perda.py
"""
import collections
import os
import re
import sqlite3
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
sys.path.insert(0, ROOT)
sys.path.insert(0, BASE)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.pasal_extractor import (
    extract_pasal, _PASAL_JUDUL_PATTERN, _PASAL_PATTERN, _MAX_LONJAT_NOMOR, _to_int,
)

DB = os.path.join(ROOT, "jdih.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT id, nomor_tahun, judul, konten_text_asli FROM documents
    WHERE jenis_dokumen = 'Peraturan Daerah' ORDER BY nomor_tahun
""").fetchall()

print(f"Dokumen Perda   : {len(rows)}")
print(f"Fungsi dipakai  : extract_pasal (= extract_pasal_v2)")
print(f"Pola v2         : {_PASAL_JUDUL_PATTERN.pattern}")
print(f"MAX_LONJAT_NOMOR: {_MAX_LONJAT_NOMOR}")
print("=" * 96)

hasil = []          # (row, pasals)
nol = []
alasan = collections.Counter()

for r in rows:
    teks = r["konten_text_asli"] or ""
    ps = extract_pasal(teks)
    hasil.append((r, ps))
    if ps:
        continue

    # --- diagnosis kenapa 0 pasal ---
    ada_memutusukan = bool(re.search(r"MEMUTUSKAN", teks, re.IGNORECASE))
    if not ada_memutusukan:
        alasan["tidak ada kata MEMUTUSKAN"] += 1
        nol.append((r, "tidak ada MEMUTUSKAN"))
        continue

    after = teks[re.search(r"MEMUTUSKAN", teks, re.IGNORECASE).end():]
    m_v2 = list(_PASAL_JUDUL_PATTERN.finditer(after))
    m_v1 = list(_PASAL_PATTERN.finditer(after))
    if not m_v2:
        if m_v1:
            contoh = [m.group(0).strip() for m in m_v1[:4]]
            alasan["MEMUTUSKAN ada, 'Pasal N' tidak pernah berdiri sendiri di baris"] += 1
            nol.append((r, f"pola v2 tidak cocok (v1 dapat {m_v1[0].group(0)!r})"))
        else:
            alasan["MEMUTUSKAN ada, tapi tidak ada kemunculan 'Pasal' sama sekali"] += 1
            nol.append((r, "tidak ada kata 'Pasal' setelah MEMUTUSKAN"))
    else:
        # ada match v2 tapi semua ditolak filter loncat
        nums = [_to_int(m.group(1)) for m in m_v2]
        last = 0
        diterima = 0
        for n in nums:
            if n > last and (n - last) <= _MAX_LONJAT_NOMOR:
                diterima += 1
                last = n
        if nums[0] != 1:
            alasan[f"pasal pertama bukan 1 (mulai {nums[0]}), ditolak filter lonjat"] += 1
            nol.append((r, f"pasal pertama = {nums[0]}, bukan 1"))
        elif diterima == 0:
            alasan["semua nomor ditolak filter loncat >5"] += 1
            nol.append((r, f"loncat nomor: {nums[:6]}"))
        else:
            alasan["lainnya"] += 1
            nol.append((r, "lainnya"))

# ---------------- 1 ----------------
print("\n1. COVERAGE EKSTRAKSI PASAL (83 PERDA)")
print("=" * 96)
bert = [h for h in hasil if h[1]]
kosong = [h for h in hasil if not h[1]]
print(f"  berhasil ekstrak >=1 pasal : {len(bert)}")
print(f"  0 pasal                    : {len(kosong)}")
print(f"  tingkat keberhasilan       : {len(bert)/len(rows)*100:.1f}%")
print("\n  Penyebab 0 pasal:")
for a, n in alasan.most_common():
    print(f"    {n:>3}  {a}")

if kosong:
    print("\n  Daftar dokumen 0 pasal (20 pertama):")
    for r, why in nol[:20]:
        print(f"    {r['nomor_tahun']:<15} {why:<52}")
        print(f"      {r['judul'].strip()[:88]}")

# ---------------- 2 ----------------
print("\n2. TOTAL PASAL PERDA")
print("=" * 96)
total_pasal = sum(len(h[1]) for h in hasil)
total_pros = sum(1 for h in hasil for p in h[1] if p["is_procedural"])
total_terpotong = sum(1 for h in hasil for p in h[1] if p["terpotong"])
print(f"  total pasal terekstrak   : {total_pasal}")
print(f"  is_procedural = True     : {total_pros}")
print(f"  terpotong (600 karakter) : {total_terpotong}")
print(f"  rasio prosedural         : {total_pros/total_pasal*100:.1f}%" if total_pasal else "")
print("\n  Distribusi jumlah pasal per dokumen:")
dist = collections.Counter(len(h[1]) for h in hasil)
for n in sorted(dist):
    print(f"    {n:>3} pasal : {dist[n]:>3} dokumen")

# ---------------- 3 ----------------
print("\n3. GABUNGAN SEMUA 469 DOKUMEN")
print("=" * 96)
semua = conn.execute("SELECT id, jenis_dokumen, konten_text_asli FROM documents").fetchall()
per_b = []
for r in semua:
    ps = extract_pasal(r["konten_text_asli"] or "")
    per_b.append((r, ps))
dok_dengan_pasal = sum(1 for r, ps in per_b if ps)
tot_pasal_all = sum(len(ps) for r, ps in per_b)
tot_pros_all = sum(1 for r, ps in per_b for p in ps if p["is_procedural"])
print(f"  total dokumen            : {len(per_b)}")
print(f"  dokumen dengan >=1 pasal : {dok_dengan_pasal}")
print(f"  dokumen 0 pasal          : {len(per_b)-dok_dengan_pasal}")
print(f"  total pasal              : {tot_pasal_all}")
print(f"  total prosedural         : {tot_pros_all}")
print()
for jenis in ("Peraturan Bupati", "Peraturan Daerah"):
    sub = [(r, ps) for r, ps in per_b if r["jenis_dokumen"] == jenis]
    print(f"  {jenis:<20} dokumen={len(sub):>4}  "
          f"dengan_pasal={sum(1 for _, ps in sub if ps):>4}  "
          f"pasal={sum(len(ps) for _, ps in sub):>5}  "
          f"prosedural={sum(1 for _, ps in sub for p in ps if p['is_procedural']):>5}")

# ---------------- 4 ----------------
print("\n4. CONTOH PERDA PROSEDURAL")
print("=" * 96)
kandidat = None
for r, ps in hasil:
    for p in ps:
        if p["is_procedural"] and len(p["isi_penuh"]) > 150:
            kandidat = (r, p)
            break
    if kandidat:
        break
if kandidat:
    r, p = kandidat
    print(f"  Judul      : {r['judul'].strip()}")
    print(f"  identifier : {r['nomor_tahun']}")
    print(f"  Pasal ke   : {p['nomor_pasal']}")
    print(f"  prosedural : {p['is_procedural']}  (skor_keyword={p['skor_keyword']}, "
          f"ada_penomoran_ayat={p['ada_penomoran_ayat']})")
    print(f"  terpotong  : {p['terpotong']}")
    isi = re.sub(r"\s+", " ", p["isi_penuh"])
    print(f"  isi (200 karakter pertama):")
    print(f"  {isi[:200]}")
    print(f"\n  [isi_penuh total {len(p['isi_penuh'])} karakter]")
else:
    print("  TIDAK ADA Perda dengan pasal prosedural.")

conn.close()
