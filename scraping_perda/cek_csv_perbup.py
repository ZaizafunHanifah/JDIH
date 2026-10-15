"""Cek konvensi identifier pada CSV Perbup yang sudah ada."""
import csv
import io
import os

csv.field_size_limit(100000000)

p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "raw_documents_export.csv")
print("path :", p)
print("ada? :", os.path.exists(p))

if os.path.exists(p):
    with io.open(p, encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = list(r)
        kolom = r.fieldnames
    print("kolom:", kolom)
    print("baris:", len(rows))
    print()
    for x in rows[:3]:
        print({k: (str(v)[:45] if v else v) for k, v in x.items()})
    print()
    nt = [f"{x['nomor']}_{x['tahun']}" for x in rows]
    print("contoh nomor_tahun:", nt[:8])
    print("duplikat nomor_tahun:", len(nt) - len(set(nt)))
    print("tahun unik:", sorted(set(x["tahun"] for x in rows)))
    print("nomor kosong:", sum(1 for x in rows if not x["nomor"]))
