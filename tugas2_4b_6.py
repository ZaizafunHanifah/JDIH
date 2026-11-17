import os, sys, re
sys.path.insert(0, '.')
import psycopg2
from psycopg2.extras import RealDictCursor
from app.pasal_extractor import (
    extract_pasal, potong_penjelasan, _to_int, _PASAL_PATTERN,
    _LAMPIRAN_RE, _BAB_JUDUL_PATTERN, _MAX_ISI_LENGTH,
    bersihkan_isi_pasal, _PASAL_JUDUL_PATTERN, _MAX_LONJAT_NOMOR,
    _FOOTER_JDIH, _PARAGRAF_AKHIR, is_procedural,
)
from app.routers.documents import _keyword_patterns, _pasal_memenuhi_keyword, _is_pasal_definisi
from app.synonyms import sinonim_dari

DB_PASSWORD = os.environ.get('DB_PASSWORD')
c = psycopg2.connect(host='localhost', port=5432, dbname='jdih',
                     user='postgres', password=DB_PASSWORD, cursor_factory=RealDictCursor)
cur = c.cursor()

print('=== TASK 4b (fixed): DOKUMEN 1164 - TIAP PASAL DAN ALASAN GUGUR ===')
cur.execute("SELECT id, judul, nomor, konten_text_asli FROM documents WHERE id = 1164")
r = cur.fetchone()
print(f"Judul: {r['judul']}")
text = r['konten_text_asli']
cut = potong_penjelasan(text)
valid_pasals = extract_pasal(cut)
keywords = ['syarat', 'izin', 'usaha']
keyword_pats = [(kw, _keyword_patterns(kw, pakai_sinonim=True)) for kw in keywords]
print(f"Total valid pasals: {len(valid_pasals)}\n")
for p in valid_pasals:
    ok, found, missing = _pasal_memenuhi_keyword(keyword_pats, p['isi_penuh'])
    proc = is_procedural(p['isi_penuh'])
    defn = _is_pasal_definisi(p)
    print(f"Pasal {p['nomor_pasal']}: lolos={ok}, definisi={defn}, procedural={proc['is_procedural']}")
    print(f"   found={found}, missing={missing}")
    print(f"   isi (150 char): {p['isi_penuh'][:150]!r}")
    print()

print('=== TASK 2: potong_penjelasan pada doc 888 dan 922 ===')
for did in [888, 922]:
    cur.execute("SELECT id, judul, konten_text_asli FROM documents WHERE id = %s", (did,))
    rr = cur.fetchone()
    text = rr['konten_text_asli']
    low = text.lower()
    print(f"\n--- Doc {did}: {rr['judul'][:60]} ---")
    print(f"  panjang teks: {len(text)}")
    print(f"  mengandung 'PENJELASAN': {'PENJELASAN' in text or 'penjelasan' in low}")
    print(f"  mengandung 'mulai berlaku': {'mulai berlaku' in low}")
    print(f"  mengandung 'diundangkan': {'diundangkan' in low}")
    
    # Current (broken) regex: r'pasal\\s+\\d+'
    cur_regex = r'pasal\\s+\\d+'
    fixed_regex = r'pasal\s+\d+'
    
    def find_cut(teks, regex_pattern):
        low2 = teks.lower()
        last_boundary = -1
        for m in re.finditer(regex_pattern, low2):
            seg = low2[m.start():m.start() + 2000]
            if 'mulai berlaku' in seg or 'diundangkan' in seg:
                last_boundary = m.start()
        if last_boundary < 0:
            return None, -1
        p1 = low2.find('pasal 1')
        if p1 < 0 or last_boundary <= p1:
            return None, -1
        _MARKERS_PENJELASAN = ['PENJELASAN ATAS', 'PENJELASAN', 'TAMBAHAN LEMBARAN DAERAH', 'TAMBAHAN BERITA DAERAH', 'I. UMUM', 'II. PASAL DEMI PASAL']
        earliest = None
        for mark in _MARKERS_PENJELASAN:
            i = low2.find(mark.lower(), last_boundary + 1)
            if i >= 0 and (earliest is None or i < earliest):
                earliest = i
        if earliest is None:
            return None, -1
        return earliest, last_boundary

    pos_cur, boundary_cur = find_cut(text, cur_regex)
    pos_fix, boundary_fix = find_cut(text, fixed_regex)
    print(f"  [BROKEN regex] last_boundary(pasal N dengan mulai berlaku/diundangkan): {boundary_cur}, cut position: {pos_cur}")
    print(f"  [FIXED regex]  last_boundary: {boundary_fix}, cut position: {pos_fix}")
    if pos_cur is not None:
        print(f"  [BROKEN] teks setelah potong (awal 100): {text[:pos_cur][:100]!r}")
    if pos_fix is not None:
        print(f"  [FIXED]  teks setelah potong (awal 100): {text[:pos_fix][:100]!r}")

print()
print('=== TASK 6: CEK ENTRI "mengaju" DAN POTONGAN KATA DI TEKS ===')
# Cek apakah "mengaju" muncul sebagai kata utuh atau bagian kata
for kata in ['mengaju', 'mengurus', 'mengajukan', 'memohon']:
    cur.execute("SELECT COUNT(*) AS jml FROM documents WHERE konten_text_asli ~* %s", (r'\m' + kata + r'\M',))
    rr = cur.fetchone()
    print(f"  '{kata}' sebagai kata utuh (word boundary): {rr['jml']} dokumen")
    cur.execute("SELECT COUNT(*) AS jml FROM documents WHERE konten_text_asli ILIKE %s", (f'%{kata}%',))
    rr = cur.fetchone()
    print(f"  '{kata}' sebagai substring (ILIKE): {rr['jml']} dokumen")

# Tampilkan semua entri sinonim dan apakah berupa potongan
print("\nSemua entri SINONIM:")
for k, v in __import__('app.synonyms', fromlist=['SINONIM']).SINONIM.items():
    print(f"  {k} -> {v}")

c.close()
