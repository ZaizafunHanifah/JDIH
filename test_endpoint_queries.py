import os, sys
sys.path.insert(0, '.')
os.environ['DB_PASSWORD'] = '123'
from app.routers.documents import (
    _cari_tahap, _extract_main_keywords, bangun_tsquery,
    _keyword_patterns, _MAKS_PASAL_TAMPIL,
)
from app.synonyms import sinonim_dari

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
    print("=" * 80)
    print(f"QUERY: '{q}'")
    print("=" * 80)

    keywords = _extract_main_keywords(q)
    print(f"1. keywords: {keywords}")

    # Kelompok sinonim per keyword (non-expanded)
    print("2. kelompok sinonim (per keyword):")
    for kw in keywords:
        syn = sinonim_dari(kw)
        print(f"   {kw} -> {syn}")

    # tsquery tanpa sinonim (percobaan pertama)
    tsq_no_syn = bangun_tsquery(keywords, pakai_sinonim=False)
    print(f"3. tsquery (tanpa sinonim): {tsq_no_syn}")

    # tsquery dengan sinonim (percobaan kedua)
    tsq_with_syn = bangun_tsquery(keywords, pakai_sinonim=True)
    print(f"4. tsquery (dengan sinonim): {tsq_with_syn}")

    # Jalankan _cari_tahap (sama seperti endpoint /tata-cara)
    hasil = _cari_tahap(q, keywords, pakai_sinonim=False)
    diperluas = False
    mode = "tanpa sinonim"
    if hasil is None:
        hasil = _cari_tahap(q, keywords, pakai_sinonim=True)
        diperluas = hasil is not None
        mode = "dengan sinonim" if diperluas else "tidak ditemukan"

    print(f"5. mode pencarian: {mode}")
    print(f"6. diperluas_sinonim: {diperluas}")

    if hasil is None:
        print("7. STATUS: tidak_ditemukan")
        print("8. dokumen terpilih: -")
        print("9. pasal lolos: -")
    else:
        row, lolos, valid_pasals, dokumen_perubahan = hasil
        print(f"7. STATUS: ditemukan")
        print(f"8. dokumen terpilih: ID {row['id']} | {row['judul']}")
        print(f"   nomor: {row['nomor']}, tanggal: {row['tanggal_terbit']}, jenis: {row['jenis_dokumen']}")
        print(f"   dokumen_perubahan: {dokumen_perubahan}")
        print(f"9. pasal lolos ({len(lolos)} dari {len(valid_pasals)} valid):")
        for p in lolos[:_MAKS_PASAL_TAMPIL]:
            print(f"   - Pasal {p['nomor_pasal']}: {p['isi_pasal'][:100]}")
    print()
