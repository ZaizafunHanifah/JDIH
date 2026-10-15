"""
TUGAS VERIFIKASI - read-only, tidak mengubah file apa pun.
  1. 24 dokumen Perbup kategori "berubah lainnya" (lengkap)
  2. Kasus 10_2023, 45_2020, 20_2021 - jawaban berbasis data
  3. 17 keyword yang tidak pernah match
Jalankan: python verifikasi_rinci.py
"""
import collections
import csv
import io
import os
import re
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DB = os.path.join(ROOT, "jdih.db")

sys.path.insert(0, ROOT)
from import_real_data import TOPICS, match_topics  # noqa: E402

csv.field_size_limit(100000000)

# ---------------- muat data ----------------
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
db_rows = conn.execute("""
    SELECT d.id, d.nomor, d.tanggal_terbit, d.judul, d.konten_text,
           GROUP_CONCAT(t.label_topik, '||') AS kat
    FROM documents d
    LEFT JOIN document_topics dt ON dt.document_id = d.id
    LEFT JOIN topics t ON t.id = dt.topic_id
    GROUP BY d.id
""").fetchall()

def nt_of(r):
    return f"{str(r['nomor']).strip()}_{str(r['tanggal_terbit'])[:4].strip()}"

perbup = []
for r in db_rows:
    perbup.append({
        "nt": nt_of(r), "judul": r["judul"] or "", "teks": r["konten_text"] or "",
        "db": set((r["kat"] or "").split("||")) - {""},
        "baru": set(match_topics(r["judul"])),
    })

def kelas(p):
    if p["db"] and not p["baru"]:
        return "hilang"
    if p["baru"] and not p["db"]:
        return "dapat"
    if p["db"] and p["baru"] and p["db"] != p["baru"]:
        return "berubah"
    return "sama"

berubah = [p for p in perbup if kelas(p) == "berubah"]

# ---------------- 1. 24 dokumen ----------------
print("=" * 110)
print("1. LENGKAP: 24 DOKUMEN PERBUP KATEGORI 'BERUBAH'")
print("=" * 110)
print(f"{'nomor_tahun':<12}{'kategori lama':<44}{'kategori baru':<44}")
print("-" * 110)
for i, p in enumerate(berubah, 1):
    lama = ", ".join(sorted(p["db"]))
    baru = ", ".join(sorted(p["baru"]))
    print(f"{i:>2}. {p['nt']:<9}")
    print(f"    judul : {p['judul'].strip()[:60]}")
    print(f"    LAMA  : {lama}")
    print(f"    BARU  : {baru}")
    print()

# pola perubahan
print("=" * 110)
print("POLA PERUBAHAN (kategori mana yang hilang / muncul)")
print("=" * 110)
hilang_pola = collections.Counter()
muncul_pola = collections.Counter()
for p in berubah:
    for t in p["db"] - p["baru"]:
        hilang_pola[t] += 1
    for t in p["baru"] - p["db"]:
        muncul_pola[t] += 1
print("Kategori yang HILANG:")
for t, n in hilang_pola.most_common():
    print(f"   {t:<46}: {n}")
print("Kategori yang MUNCUL:")
for t, n in muncul_pola.most_common():
    print(f"   {t:<46}: {n}")

# ---------------- 2. tiga kasus ----------------
def cari(nt):
    return next((p for p in perbup if p["nt"] == nt), None)

def konteks_kata(teks, kata, lebar=260, maks=3):
    """Kembalikan potongan teks di sekitar setiap kemunculan kata."""
    out = []
    for m in re.finditer(re.escape(kata), teks, re.I):
        a = max(0, m.start() - lebar // 2)
        b = min(len(teks), m.end() + lebar // 2)
        out.append(" ".join(teks[a:b].split()))
        if len(out) >= maks:
            break
    return out

def keyword_yang_match(judul, kategori):
    """Kembalikan daftar keyword yang benar-benar memicu, persis."""
    jl = (judul or "").lower()
    return [kw for kw in TOPICS[kategori]
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", jl)]

print()
print("=" * 110)
print("2. PEMERIKSAAN 3 KASUS RAGU")
print("=" * 110)

# --- 2a. 10_2023 ---
print()
print("#" * 110)
print("2a. 10_2023 - apakah BENAR tidak berhubungan dengan sampah?")
print("#" * 110)
p = cari("10_2023")
if p:
    print("Judul lengkap:")
    print(f"   {p['judul'].strip()}")
    print()
    print("Kategori DB   :", sorted(p["db"]))
    print("Kategori baru :", sorted(p["baru"]))
    print()
    print("Keyword 'Pertanian dan Lingkungan Hidup' yang match di JUDUL:")
    print("   ", keyword_yang_match(p["judul"], "Pertanian dan Lingkungan Hidup") or "(TIDAK ADA)")
    print()
    print("Keyword Penc triggering kategori LAIN di judul:")
    for kat in TOPICS:
        km = keyword_yang_match(p["judul"], kat)
        if km:
            print(f"   {kat}: {km}")
    print()
    n_sampah = len(re.findall(r"sampah", p["teks"], re.I))
    n_persampahan = len(re.findall(r"persampahan", p["teks"], re.I))
    print(f"Kemunculan 'sampah' di konten_text : {n_sampah}")
    print(f"Kemunculan 'persampahan' di konten : {n_persampahan}")
    print(f"Kemunculan 'lingkungan'            : {len(re.findall(r'lingkungan', p['teks'], re.I))}")
    print(f"Kemunculan 'air tanah'             : {len(re.findall(r'air tanah', p['teks'], re.I))}")
    print(f"Kemunculan 'pertanian'/'petani'    : {len(re.findall(r'pertanian|petani', p['teks'], re.I))}")
    print()
    if n_sampah:
        print("Konteks 'sampah' di konten_text:")
        for c in konteks_kata(p["teks"], "sampah", 300, 3):
            print(f"   ...{c}...")
    else:
        print("KONTEN_TEXT TIDAK PERNAH memuat kata 'sampah' sama sekali.")
    print()
    print("200 karakter pertama konten_text:")
    print("   ", " ".join(p["teks"][:200].split()))
else:
    print("tidak ditemukan")

# --- 2b. 45_2020 ---
print()
print("#" * 110)
print("2b. 45_2020 - apakah 'penyakit' muncul dalam konteks kesehatan?")
print("#" * 110)
p = cari("45_2020")
if p:
    print("Judul lengkap:")
    print(f"   {p['judul'].strip()}")
    print()
    print("Kategori DB   :", sorted(p["db"]))
    print("Kategori baru :", sorted(p["baru"]))
    print()
    print("Keyword match di JUDUL per kategori:")
    for kat in TOPICS:
        km = keyword_yang_match(p["judul"], kat)
        if km:
            print(f"   {kat}: {km}")
    print()
    n_p = len(re.findall(r"penyakit", p["teks"], re.I))
    print(f"Kemunculan 'penyakit' di konten_text : {n_p}")
    print()
    if n_p:
        print("Semua konteks 'penyakit' (maks 5):")
        for c in konteks_kata(p["teks"], "penyakit", 300, 5):
            print(f"   ...{c}...")
    else:
        print("KONTEN_TEXT TIDAK memuat kata 'penyakit'.")
    print()
    print("300 karakter pertama konten_text:")
    print("   ", " ".join(p["teks"][:300].split()))
    print()
    for kw in ("kesehatan", "penyakit menular", "pandemi", "covid", "karantina"):
        n = len(re.findall(re.escape(kw), p["teks"], re.I))
        print(f"   '{kw}' muncul {n}x")
else:
    print("tidak ditemukan")

# --- 2c. 20_2021 ---
print()
print("#" * 110)
print("2c. 20_2021 - keyword PERSIS yang match")
print("#" * 110)
p = cari("20_2021")
if p:
    print("Judul lengkap:")
    print(f"   {p['judul'].strip()}")
    print()
    print("Kategori DB   :", sorted(p["db"]))
    print("Kategori baru :", sorted(p["baru"]))
    print()
    print("SEMUA keyword yang match per kategori (persis, hasil \\\\b regex):")
    for kat in TOPICS:
        km = keyword_yang_match(p["judul"], kat)
        if km:
            print(f"   {kat}")
            print(f"      -> {km}")
    print()
    print("Kata kunci BARU mana yang tidak ada di versi lama:")
    print("   'air minum' :", bool(re.search(r"\bair minum\b", p["judul"], re.I)))
    print("   'penyakit' :", bool(re.search(r"\bpenyakit\b", p["judul"], re.I)))
    print("   frasa 'air tanah' :", bool(re.search(r"\bair tanah\b", p["judul"], re.I)))
    print()
    print("Konteks di KONTEN_TEXT untuk tiap keyword yang match:")
    for kat in TOPICS:
        for kw in keyword_yang_match(p["judul"], kat):
            print(f"   '{kw}':")
            for c in konteks_kata(p["teks"], kw, 300, 2):
                print(f"      ...{c}...")
    print()
    print("300 karakter pertama konten_text:")
    print("   ", " ".join(p["teks"][:300].split()))
else:
    print("tidak ditemukan")

# ---------------- 3. keyword tanpa match ----------------
print()
print("=" * 110)
print("3. KEYWORD YANG TIDAK PERNAH MATCH DI 469 DOKUMEN")
print("=" * 110)
perda_csv = os.path.join(BASE, "perda_export.csv")
semua_judul = [p["judul"] for p in perbup]
with io.open(perda_csv, encoding="utf-8") as f:
    semua_judul += [r["judul"] or "" for r in csv.DictReader(f)]

nol = []
for kat, kws in TOPICS.items():
    for kw in kws:
        n = sum(1 for j in semua_judul
                if re.search(r"\b" + re.escape(kw.lower()) + r"\b", j.lower()))
        if n == 0:
            nol.append((kat, kw))
print(f"Total judul diperiksa : {len(semua_judul)}")
print(f"Keyword tanpa match   : {len(nol)}\n")
for kat, kw in nol:
    print(f"   {kw:<30} ({kat})")

conn.close()
print("\n(tidak ada file yang diubah; DB ditutup read-only)")
