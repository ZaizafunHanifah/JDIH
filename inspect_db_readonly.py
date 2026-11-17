import os, sys
sys.path.insert(0, '.')
import psycopg2
from psycopg2.extras import RealDictCursor
c = psycopg2.connect(host='localhost', port=5432, dbname='jdih',
                     user='postgres', password=os.environ['DB_PASSWORD'],
                     cursor_factory=RealDictCursor)
cur = c.cursor()
print('=== TABEL SEMUA ===')
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
tables = [r['table_name'] for r in cur.fetchall()]
for t in tables:
    print(f"  {t}")

print()
for t in tables:
    print(f'=== TABEL: {t} ===')
    cur.execute(f"SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns WHERE table_name='{t}' ORDER BY ordinal_position")
    cols = cur.fetchall()
    for col in cols:
        print(f"  {col['column_name']} | {col['data_type']} | nullable={col['is_nullable']} | default={col['column_default']}")
    cur.execute(f"SELECT COUNT(*) AS jml FROM {t}")
    cnt = cur.fetchone()
    print(f"  JUMLAH BARIS: {cnt['jml']}")
    print()

print('=== INDEX ===')
cur.execute("SELECT indexname, tablename, indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename, indexname")
for r in cur.fetchall():
    print(f"  {r['tablename']}: {r['indexname']} ({r['indexdef']})")

print()
print('=== TRIGGER ===')
cur.execute("SELECT trigger_name, event_object_table, action_timing, event_manipulation, action_statement FROM information_schema.triggers WHERE trigger_schema='public'")
for r in cur.fetchall():
    print(f"  {r['trigger_name']} ON {r['event_object_table']} {r['action_timing']} {r['event_manipulation']}")
    print(f"    -> {r['action_statement'][:120]}")

print()
print('=== FUNGSI ===')
cur.execute("SELECT routine_name, routine_type FROM information_schema.routines WHERE routine_schema='public'")
for r in cur.fetchall():
    print(f"  {r['routine_name']} ({r['routine_type']})")

c.close()
