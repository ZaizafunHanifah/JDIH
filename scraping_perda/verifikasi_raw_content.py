"""Verifikasi setelah import_raw_content.py (dengan filter jenis_dokumen)."""
import hashlib, os, sqlite3, sys
BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
sys.path.insert(0, ROOT)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from app.pasal_extractor import extract_pasal

gagal = []
def cek(nama, got, exp):
    ok = got == exp
    if not ok:
        gagal.append(nama)
    print(f"  {nama:<52}{got:>6}  (harus {exp})  {'OK' if ok else 'GAGAL'}")

conn = sqlite3.connect(os.path.join(ROOT, "jdih.db"))
conn.row_factory = sqlite3.Row

print("=" * 84)
print("1. KONTEN_TEXT_ASLI PERBUP")
print("=" * 84)
n = conn.execute("SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Bupati'").fetchone()[0]
cek("total Perbup", n, 386)
cek("Perbup konten_text_asli terisi", conn.execute(
    "SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Bupati' "
    "AND konten_text_asli IS NOT NULL AND TRIM(konten_text_asli)<>''").fetchone()[0], 339)
cek("Perbup konten_text_asli kosong (47, tak ada di CSV)", conn.execute(
    "SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Bupati' "
    "AND (konten_text_asli IS NULL OR TRIM(konten_text_asli)='')").fetchone()[0], 47)
cek("Perbup terisi yang punya MEMUTUSKAN", conn.execute(
    "SELECT COUNT(*) FROM documents WHERE jenis_dokumen='Peraturan Bupati' "
    "AND konten_text_asli IS NOT NULL AND LOWER(konten_text_asli) LIKE '%memutuskan%'"
    ).fetchone()[0], 328)

print()
print("=" * 84)
print("2. PERDA TIDAK TERTIMPA")
print("=" * 84)
rows = conn.execute("""SELECT id, nomor_tahun, konten_text_asli FROM documents
                       WHERE jenis_dokumen='Peraturan Daerah' ORDER BY nomor_tahun""").fetchall()
def fp(t):
    return "NULL" if t is None else f"{len(t)}:{hashlib.sha256(t.encode()).hexdigest()[:16]}"
def baca(jalur):
    d = {}
    for baris in open(os.path.join(BASE, jalur), encoding="utf-8"):
        i, nt, f = baris.rstrip("\n").split("\t")
        d[i] = (nt, f)
    return d
seb, ses = baca("sidik_perda_sebelum.txt"), baca("sidik_perda_sesudah.txt")
cek("jumlah Perda", len(rows), 83)
cek("Perda konten_text_asli terisi", sum(1 for r in rows if r["konten_text_asli"]), 83)
beda = [i for i in seb if seb[i] != ses.get(i)]
cek("baris Perda yang berubah", len(beda), 0)
cek("Perda dengan sidik jari persis sama", sum(1 for i in seb if fp(
    next(r["konten_text_asli"] for r in rows if str(r["id"]) == i)) == seb[i][1]), 83)

print()
print("=" * 84)
print("3. ANALISIS PASAL ULANG (extract_pasal v2, apa adanya)")
print("=" * 84)
stat = {}
for jenis in ("Peraturan Bupati", "Peraturan Daerah"):
    sub = conn.execute("SELECT id, konten_text_asli FROM documents WHERE jenis_dokumen=?",
                       (jenis,)).fetchall()
    dok = pal = pros = 0
    for r in sub:
        ps = extract_pasal(r["konten_text_asli"] or "")
        if ps:
            dok += 1
        pal += len(ps)
        pros += sum(1 for p in ps if p["is_procedural"])
    stat[jenis] = (len(sub), dok, pal, pros)
    print(f"  {jenis:<18} n={len(sub):>4}  dengan_pasal={dok:>4}  pasal={pal:>6}  prosedural={pros:>6}")

print()
cek("Perbup dengan >=1 pasal", stat["Peraturan Bupati"][1], 327)
cek("Perbup total pasal", stat["Peraturan Bupati"][2], 6455)
cek("Perbup total prosedural", stat["Peraturan Bupati"][3], 3337)
cek("Perda dengan >=1 pasal", stat["Peraturan Daerah"][1], 80)
cek("Perda total pasal", stat["Peraturan Daerah"][2], 2774)
cek("Perda total prosedural", stat["Peraturan Daerah"][3], 1825)

print()
print("=" * 84)
print("4. GABUNGAN 469 DOKUMEN")
print("=" * 84)
tot = [sum(stat[j][i] for j in stat) for i in range(4)]
cek("total dokumen", tot[0], 469)
cek("dokumen dengan >=1 pasal", tot[1], 407)
cek("dokumen 0 pasal", tot[0] - tot[1], 62)
cek("total pasal", tot[2], 9229)
cek("total prosedural", tot[3], 5162)
cek("cek silang 327+80", 327 + 80, 407)
cek("cek silang 6455+2774", 6455 + 2774, 9229)
cek("cek silang 3337+1825", 3337 + 1825, 5162)
cek("total dokumen DB", conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0], 469)
cek("FTS5 rows", conn.execute("SELECT COUNT(*) FROM documents_fts").fetchone()[0], 469)

print()
print("=" * 84)
print("SEMUA CEK LULUS" if not gagal else f"{len(gagal)} CEK GAGAL: {gagal}")
print("=" * 84)
