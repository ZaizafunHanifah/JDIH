import urllib.request, urllib.parse, json

BASE = "http://127.0.0.1:8765"

def get(path, params=None, json_ok=True):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as resp:
        body = resp.read().decode()
    if json_ok:
        return resp.status, json.loads(body)
    return resp.status, body

print("=== GET / ===")
s, d = get("/", json_ok=False)
print("status:", s, "(HTML halaman utama, panjang", len(d), "karakter)")

print("\n=== GET /api/documents?q=restoran ===")
s, d = get("/api/documents", {"q": "restoran"})
print("status:", s)
print("total:", d["pagination"]["total"])
for item in d["data"][:3]:
    print(f"  ID {item['id']} | {item['nomor']} | {item['judul'][:60]} | prosedur={'ada' if item.get('prosedur') else 'None'}")

print("\n=== GET /api/documents/922 ===")
s, d = get("/api/documents/922")
print("status:", s)
print("judul:", d["judul"])
print("nomor:", d["nomor"])
print("jenis:", d["jenis_dokumen"])
print("topics:", [t["label_topik"] for t in d["topics"]])

print("\n=== GET /api/documents/922/prosedur ===")
s, d = get("/api/documents/922/prosedur")
print("status:", s)
print("status_field:", d.get("status"))
print("jumlah_pasal_total:", d.get("jumlah_pasal_total"))
for p in d.get("pasal_prosedural", [])[:3]:
    print(f"  Pasal {p['nomor_pasal']}: {p['isi_pasal'][:100]}...")

print("\n=== GET /api/documents/tata-cara?q=cara bayar pajak restoran ===")
s, d = get("/api/documents/tata-cara", {"q": "cara bayar pajak restoran"})
print("status:", s)
print("status_field:", d.get("status"))
print("diperluas_sinonim:", d.get("diperluas_sinonim"))
print("dokumen_perubahan:", d.get("dokumen_perubahan"))
if d.get("dokumen"):
    print("dokumen:", d["dokumen"]["id"], d["dokumen"]["judul"][:60])
if d.get("prosedur"):
    print("jumlah_pasal_relevan:", d["prosedur"]["jumlah_pasal_relevan"])
    for p in d["prosedur"]["pasal_prosedural"][:3]:
        print(f"  Pasal {p['nomor_pasal']}: {p['isi_pasal'][:100]}...")

print("\n=== GET /api/topics ===")
s, d = get("/api/topics")
print("status:", s)
for t in d:
    print(f"  id={t['id']} label={t['label_topik']} jumlah={t['jumlah_dokumen']}")

print("\n=== GET /api/jenis-dokumen ===")
s, d = get("/api/jenis-dokumen")
print("status:", s)
for x in d:
    print(f"  {x['jenis']}: {x['jumlah']}")

print("\n=== GET /api/tahun ===")
s, d = get("/api/tahun")
print("status:", s)
print("tahun:", d)

print("\n=== GET /api/status-hukum ===")
s, d = get("/api/status-hukum")
print("status:", s)
print("total_status:", d["total_status"])
print("data:", d["data"])
