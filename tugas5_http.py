import urllib.request, urllib.parse, json

queries = [
    "cara daftar sekolah dasar",
    "cara bayar pajak restoran",
    "syarat izin usaha",
    "resep nasi goreng",
    "mengurus tambahan penghasilan",
    "gimana cara bikin KTP",
    "mau urus izin usaha",
]

for q in queries:
    url = "http://127.0.0.1:8765/api/documents/tata-cara?" + urllib.parse.urlencode({"q": q})
    print("=" * 80)
    print(f"HTTP ENDPOINT: GET /api/documents/tata-cara?q={q!r}")
    print("=" * 80)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        print(f"Status HTTP: 200")
        print(f"status: {data.get('status')}")
        print(f"diperluas_sinonim: {data.get('diperluas_sinonim')}")
        print(f"dokumen_perubahan: {data.get('dokumen_perubahan')}")
        doc = data.get('dokumen')
        if doc:
            print(f"dokumen terpilih: ID {doc['id']} | {doc['judul']}")
            print(f"   nomor: {doc['nomor']}, tahun: {doc['tahun']}")
        prosedur = data.get('prosedur')
        if prosedur:
            print(f"jumlah_pasal_total: {prosedur.get('jumlah_pasal_total')}")
            print(f"jumlah_pasal_relevan: {prosedur.get('jumlah_pasal_relevan')}")
            for p in prosedur.get('pasal_prosedural', []):
                print(f"   - Pasal {p['nomor_pasal']}: {p['isi_pasal'][:100]!r}")
        print(f"pesan: {data.get('pesan')}")
    except Exception as e:
        print(f"ERROR: {e}")
    print()
