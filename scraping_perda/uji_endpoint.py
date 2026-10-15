import json, urllib.request

base = "http://127.0.0.1:8765"


def get(u):
    with urllib.request.urlopen(u) as r:
        return json.loads(r.read().decode())


print("=== (4a) /api/documents?q=Janggolan ===")
d = get(base + "/api/documents?q=Janggolan")
print("total =", d["pagination"]["total"], "(harus 2)")
for row in d["data"]:
    pr = row.get("prosedur")
    if pr is None:
        print("  NULL - GAGAL")
        continue
    th = row.get("tahun") or (row.get("tanggal_terbit") or "")[:4]
    print(f"  id={row['id']} nomor={row['nomor']} th={th} "
          f"prosedur.status={pr.get('status')}")

print()
print("=== (4b) /api/documents?q=penghasilan ===")
d = get(base + "/api/documents?q=penghasilan")
print("total =", d["pagination"]["total"], "(harus >3)")
n_null = sum(1 for r in d["data"] if r.get("prosedur") is None)
n_obj = sum(1 for r in d["data"] if r.get("prosedur") is not None)
print(f"prosedur=null: {n_null}, prosedur=objek: {n_obj}  "
      f"(harus null={len(d['data'])}, objek=0)")

print()
print("=== (4c) /api/documents/tata-cara?q=cara bayar pajak restoran ===")
d = get(base + "/api/documents/tata-cara?q=cara+bayar+pajak+restoran")
print("status =", d.get("status"))
doc = d.get("dokumen", {})
print("id =", doc.get("id"), "nomor =", doc.get("nomor"), "tahun =", doc.get("tahun"))
ps = d.get("prosedur", {})
print("jumlah_pasal_total =", ps.get("jumlah_pasal_total"))
print("jumlah_pasal_relevan =", ps.get("jumlah_pasal_relevan"))
for p in ps.get("pasal_prosedural", []):
    print(f"  Pasal {p['nomor_pasal']}: skor={p['skor_keyword']} terpotong={p['terpotong']}")
    print(f"    {p['isi_pasal'][:120]}")

print()
print("=== (4d) field konten_text/konten_text_asli tidak ada di /api/documents ===")
d = get(base + "/api/documents?jenis=Peraturan+Daerah")
k = sorted(d["data"][0].keys())
print("keys:", k)
print("konten_text ada?", "konten_text" in k)
print("konten_text_asli ada?", "konten_text_asli" in k)
print("status_hukum ada?", "status_hukum" in k)
print("catatan_relasi ada?", "catatan_relasi" in k)