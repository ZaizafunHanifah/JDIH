import os, sys, re
sys.path.insert(0, '.')
import psycopg2
from psycopg2.extras import RealDictCursor
from app.pasal_extractor import (
    extract_pasal, potong_penjelasan, _to_int, _PASAL_PATTERN,
    _LAMPIRAN_RE, _BAB_JUDUL_PATTERN, _MAX_ISI_LENGTH,
    bersihkan_isi_pasal, _PASAL_JUDUL_PATTERN, _MAX_LONJAT_NOMOR,
    _FOOTER_JDIH, _PARAGRAF_AKHIR,
)

DB_PASSWORD = os.environ.get('DB_PASSWORD')
c = psycopg2.connect(host='localhost', port=5432, dbname='jdih',
                     user='postgres', password=DB_PASSWORD, cursor_factory=RealDictCursor)
cur = c.cursor()
cur.execute("SELECT id, konten_text_asli FROM documents WHERE konten_text_asli IS NOT NULL ORDER BY id")
rows = cur.fetchall()


def find_after_memutuskan(text):
    m = re.search(r'MEMUTUSKAN', text, re.IGNORECASE)
    if not m:
        return None
    return text[m.end():]


def extract_linestart_no_clean(after):
    matches = list(_PASAL_JUDUL_PATTERN.finditer(after))
    if not matches:
        return []
    valid = []
    last_num = 0
    for m in matches:
        num = _to_int(m.group(1))
        if num > last_num and (num - last_num) <= _MAX_LONJAT_NOMOR:
            valid.append(m)
            last_num = num
    result = []
    for i, m in enumerate(valid):
        nomor = _to_int(m.group(1))
        start = m.end()
        end = valid[i + 1].start() if i + 1 < len(valid) else len(after)
        isi = after[start:end].strip()
        result.append({'nomor_pasal': nomor, 'isi_penuh': isi})
    return result


print('=== TASK 1b: 10 PASAL PENGURANGAN TERBESAR (bersihkan_isi_pasal) ===')
reductions = []
for r in rows:
    did = r['id']
    text = r['konten_text_asli'] or ''
    after_raw = find_after_memutuskan(text)
    if after_raw is None:
        continue
    cut = potong_penjelasan(text)
    after_cut = find_after_memutuskan(cut) or ''
    pasals_linestart = extract_linestart_no_clean(after_cut)
    pasals_production = extract_pasal(cut)
    linestart_map = {p['nomor_pasal']: p['isi_penuh'] for p in pasals_linestart}
    for p in pasals_production:
        nomor = p['nomor_pasal']
        before = linestart_map.get(nomor, '')
        after = p['isi_penuh']
        if before != after:
            reductions.append({
                'doc_id': did, 'pasal': nomor,
                'before_len': len(before), 'after_len': len(after),
                'removed': len(before) - len(after),
                'before': before, 'after': after,
            })

reductions.sort(key=lambda x: x['removed'], reverse=True)
print(f"Total pasal yang dikurangi: {len(reductions)}")
print(f"Top 10 pengurangan terbesar:\n")
for i, red in enumerate(reductions[:10], 1):
    print(f"--- #{i} Doc {red['doc_id']} Pasal {red['pasal']} (dihapus {red['removed']:,} char) ---")
    b = red['before']
    a = red['after']
    print(f"  AWAL  sebelum ({red['before_len']} char): {b[:200]!r}")
    print(f"  AKHIR sebelum ({red['before_len']} char): {b[-200:]!r}")
    print(f"  AWAL  sesudah ({red['after_len']} char):   {a[:200]!r}")
    print(f"  AKHIR sesudah ({red['after_len']} char):   {a[-200:]!r}")
    print()

print('=== TASK 4b: DOKUMEN 1164 - TIAP PASAL DAN ALASAN GUGUR ===')
from app.routers.documents import _keyword_patterns, _pasal_memenuhi_keyword, _is_pasal_definisi, is_procedural

cur.execute("SELECT id, konten_text_asli FROM documents WHERE id = 1164")
r = cur.fetchone()
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

c.close()
