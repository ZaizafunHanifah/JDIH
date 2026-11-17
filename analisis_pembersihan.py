import os, sys, re
sys.path.insert(0, '.')
import psycopg2
from psycopg2.extras import RealDictCursor
from app.pasal_extractor import (
    extract_pasal, potong_penjelasan, _to_int, _PASAL_PATTERN,
    _LAMPIRAN_RE, _BAB_JUDUL_PATTERN, is_procedural, _MAX_ISI_LENGTH,
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
    """Return text after MEMUTUSKAN, or None if not found."""
    m = re.search(r'MEMUTUSKAN', text, re.IGNORECASE)
    if not m:
        return None
    return text[m.end():]


def extract_anywhere_no_clean(after):
    """_PASAL_PATTERN (anywhere), no bersihkan cleaning."""
    matches = list(_PASAL_PATTERN.finditer(after))
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


def extract_linestart_no_clean(after):
    """_PASAL_JUDUL_PATTERN (line-start), no bersihkan cleaning."""
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


def bersihkan_stats(isi):
    """Return (cleaned_isi, footer_count, paragraf_count)."""
    i2, n1 = _FOOTER_JDIH.subn(' ', isi)
    i3, n2 = _PARAGRAF_AKHIR.subn('', i2)
    return i3.strip(), n1, n2


# Accumulators
stats = {
    'docs': 0,
    'pasals_anywhere': 0,      # _PASAL_PATTERN, no clean
    'pasals_linestart': 0,     # _PASAL_JUDUL_PATTERN, no clean
    'pasals_production': 0,    # _PASAL_JUDUL_PATTERN, with clean (production)
    'chars_anywhere': 0,
    'chars_linestart_no_clean': 0,
    'chars_production': 0,
    'chars_removed_bersihkan': 0,
    'pasals_changed_bersihkan': 0,
    'footer_jdih_deletions': 0,
    'paragraf_akhir_deletions': 0,
    'chars_removed_potong': 0,
    'pasals_removed_potong': 0,
    'missing_pasals': [],      # (doc_id, nomor, context_150, is_real)
    'bersihkan_examples': [],  # (doc_id, nomor, before, after, footer_count, paragraf_count)
}

for r in rows:
    did = r['id']
    text = r['konten_text_asli'] or ''
    stats['docs'] += 1

    after_raw = find_after_memutuskan(text)
    if after_raw is None:
        continue

    cut = potong_penjelasan(text)
    after_cut = find_after_memutuskan(cut)
    if after_cut is None:
        after_cut = ''

    # potong_penjelasan effect: chars removed at doc level
    stats['chars_removed_potong'] += len(text) - len(cut)

    # --- Extraction A: _PASAL_PATTERN (anywhere) on RAW after, no clean ---
    pasals_anywhere = extract_anywhere_no_clean(after_raw)
    stats['pasals_anywhere'] += len(pasals_anywhere)
    stats['chars_anywhere'] += sum(len(p['isi_penuh']) for p in pasals_anywhere)

    # --- Extraction B: _PASAL_JUDUL_PATTERN (line-start) on CUT after, no clean ---
    pasals_linestart = extract_linestart_no_clean(after_cut)
    stats['pasals_linestart'] += len(pasals_linestart)
    stats['chars_linestart_no_clean'] += sum(len(p['isi_penuh']) for p in pasals_linestart)

    # --- Extraction C: production (_PASAL_JUDUL_PATTERN + bersihkan) on CUT after ---
    pasals_production = extract_pasal(cut)
    stats['pasals_production'] += len(pasals_production)
    stats['chars_production'] += sum(len(p['isi_penuh']) for p in pasals_production)

    # --- bersihkan_isi_pasal effect: match B vs C by nomor ---
    linestart_map = {p['nomor_pasal']: p['isi_penuh'] for p in pasals_linestart}
    for p in pasals_production:
        nomor = p['nomor_pasal']
        before = linestart_map.get(nomor, '')
        after = p['isi_penuh']
        if before != after:
            stats['pasals_changed_bersihkan'] += 1
            stats['chars_removed_bersihkan'] += len(before) - len(after)
            _, fcount, pcount = bersihkan_stats(before)
            stats['footer_jdih_deletions'] += fcount
            stats['paragraf_akhir_deletions'] += pcount
            if len(stats['bersihkan_examples']) < 10:
                stats['bersihkan_examples'].append({
                    'doc_id': did, 'pasal': nomor,
                    'before': before[:300], 'after': after[:300],
                    'footer_count': fcount, 'paragraf_count': pcount,
                })

    # --- Missing pasals: in A (_PASAL_PATTERN) but not in B (_PASAL_JUDUL_PATTERN) ---
    anywhere_nomors = {p['nomor_pasal'] for p in pasals_anywhere}
    linestart_nomors = {p['nomor_pasal'] for p in pasals_linestart}
    missing_nomors = anywhere_nomors - linestart_nomors
    for nomor in sorted(missing_nomors):
        # Find context in after_raw
        for p in pasals_anywhere:
            if p['nomor_pasal'] == nomor:
                ctx = p['isi_penuh'][:150]
                # Classify: real pasal vs fake quote
                is_real = _PASAL_JUDUL_PATTERN.search('\n' + p['isi_penuh']) is not None
                stats['missing_pasals'].append({
                    'doc_id': did, 'pasal': nomor,
                    'context': ctx.replace('\n', ' '),
                    'is_real': is_real,
                })
                break

# potong_penjelasan pasal removal: compare pasals from raw vs cut (both _PASAL_JUDUL_PATTERN + clean)
# Re-iterate quickly
pasals_raw_production = 0
pasals_cut_production = 0
chars_raw_production = 0
chars_cut_production = 0
for r in rows:
    text = r['konten_text_asli'] or ''
    after_raw = find_after_memutuskan(text)
    if after_raw is None:
        continue
    cut = potong_penjelasan(text)
    after_cut = find_after_memutuskan(cut) or ''
    pr_raw = extract_pasal(text)  # production on raw (includes potong? NO - extract_pasal doesn't call potong)
    pr_cut = extract_pasal(cut)   # production on cut
    pasals_raw_production += len(pr_raw)
    pasals_cut_production += len(pr_cut)
    chars_raw_production += sum(len(p['isi_penuh']) for p in pr_raw)
    chars_cut_production += sum(len(p['isi_penuh']) for p in pr_cut)

stats['pasals_removed_potong'] = pasals_raw_production - pasals_cut_production

# Print results
print('=== DOCS ===')
print(f"Docs processed: {stats['docs']}")
print()

print('=== PENGARUH potong_penjelasan (bagian Penjelasan) ===')
print(f"Chars removed by potong_penjelasan (doc level): {stats['chars_removed_potong']:,}")
print(f"Pasals removed by potong_penjelasan: {stats['pasals_removed_potong']}")
print(f"  (pasals raw production: {pasals_raw_production} -> cut production: {pasals_cut_production})")
print(f"  (chars raw production: {chars_raw_production:,} -> cut production: {chars_cut_production:,})")
print()

print('=== PENGARUH bersihkan_isi_pasal (footer + judul bagian) ===')
print(f"Pasals changed by bersihkan_isi_pasal: {stats['pasals_changed_bersihkan']}")
print(f"Chars removed by bersihkan_isi_pasal: {stats['chars_removed_bersihkan']:,}")
print(f"  _FOOTER_JDIH deletions: {stats['footer_jdih_deletions']:,}")
print(f"  _PARAGRAF_AKHIR deletions: {stats['paragraf_akhir_deletions']:,}")
print()

print('=== PERBANDINGAN POLA EKSTRAKSI (9.289 -> 9.229) ===')
print(f"_PASAL_PATTERN (anywhere, no clean): {stats['pasals_anywhere']} pasals, {stats['chars_anywhere']:,} chars")
print(f"_PASAL_JUDUL_PATTERN (line-start, no clean): {stats['pasals_linestart']} pasals, {stats['chars_linestart_no_clean']:,} chars")
print(f"Production (_PASAL_JUDUL_PATTERN + bersihkan): {stats['pasals_production']} pasals, {stats['chars_production']:,} chars")
print(f"Selisih pattern (anywhere - linestart): {stats['pasals_anywhere'] - stats['pasals_linestart']}")
print(f"Selisih total (anywhere - production): {stats['pasals_anywhere'] - stats['pasals_production']}")
print()

print('=== PASAL HILANG (dalam _PASAL_PATTERN tapi tidak dalam _PASAL_JUDUL_PATTERN) ===')
print(f"Total missing: {len(stats['missing_pasals'])}")
real_count = sum(1 for m in stats['missing_pasals'] if m['is_real'])
fake_count = len(stats['missing_pasals']) - real_count
print(f"  Real pasal (title di awal baris): {real_count}")
print(f"  Fake quote (referensi tengah kalimat): {fake_count}")
print()

print('=== 10 CONTOH SEBELUM/SESUDAH bersihkan_isi_pasal ===')
for ex in stats['bersihkan_examples']:
    print(f"\nDoc {ex['doc_id']} Pasal {ex['pasal']} (footer={ex['footer_count']}, paragraf={ex['paragraf_count']}):")
    print(f"  BEFORE: {ex['before']}")
    print(f"  AFTER:  {ex['after']}")

print()
print('=== SEMUA PASAL HILANG ===')
print(f"Total missing (unique nomor): {len(stats['missing_pasals'])}")
real_count = sum(1 for m in stats['missing_pasals'] if m['is_real'])
fake_count = len(stats['missing_pasals']) - real_count
print(f"  Real pasal (title di awal baris): {real_count}")
print(f"  Fake quote (referensi tengah kalimat): {fake_count}")
print()
for m in stats['missing_pasals']:
    tipe = 'REAL' if m['is_real'] else 'FAKE-quote'
    print(f"  Doc {m['doc_id']} Pasal {m['pasal']} [{tipe}]: {m['context']}")

c.close()
