import sqlite3
conn = sqlite3.connect('jdih.db')

# Year range
min_year = conn.execute("SELECT MIN(strftime('%Y', tanggal_terbit)) FROM documents").fetchone()[0]
max_year = conn.execute("SELECT MAX(strftime('%Y', tanggal_terbit)) FROM documents").fetchone()[0]
print(f'Year range: {min_year} - {max_year}')

# Year distribution
print('\nYear distribution:')
for r in conn.execute("SELECT strftime('%Y', tanggal_terbit) as yr, COUNT(*) FROM documents GROUP BY yr ORDER BY yr"):
    print(f'  {r[0]}: {r[1]}')

# Empty konten_text
empty_count = conn.execute("SELECT COUNT(*) FROM documents WHERE konten_text IS NULL OR TRIM(konten_text) = ''").fetchone()[0]
print(f'\nEmpty konten_text: {empty_count}')

# Total
total = conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
print(f'Total documents: {total}')

# Docs with topics
with_topic = conn.execute('SELECT COUNT(DISTINCT document_id) FROM document_topics').fetchone()[0]
print(f'Documents with at least one topic: {with_topic}')
print(f'Documents without topic: {total - with_topic}')

conn.close()