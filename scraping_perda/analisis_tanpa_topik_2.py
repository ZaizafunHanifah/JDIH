"""
Analisis putaran 2: tema yang terlewat di analisis_tanpa_topik.py.
Fokus: APBD/keuangan daerah, BUMD/penyertaan modal, pemilihan,
ketenagakerjaan, pelayanan umum, dll.

Tetap ANALISIS SAJA - tidak mengubah TOPICS.
Jalankan: python analisis_tanpa_topik_2.py
"""
import csv
import io
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PERDA = os.path.join(BASE, "perda_export.csv")

TOPICS = {
    "Organisasi dan Tata Kerja Perangkat Daerah": ["organisasi", "tata kerja", "kedudukan", "susunan", "unit pelaksana teknis", "uptd"],
    "Standar Biaya dan Honorarium": ["standar biaya", "honorarium", "satuan biaya"],
    "Pengadaan Barang/Jasa": ["pengadaan barang", "pengadaan jasa", "lpse"],
    "Perencanaan Pembangunan Daerah": ["rkpd", "rpjmd", "rencana kerja pemerintah daerah", "rencana pembangunan"],
    "Kepegawaian dan Aparatur Sipil Negara": ["pegawai", "pns", "pppk", "aparatur sipil negara", "jabatan fungsional", "tambahan penghasilan"],
    "Pajak dan Retribusi Daerah": ["pajak", "retribusi", "pbb", "bphtb"],
    "Pelayanan Kesehatan": ["kesehatan", "puskesmas", "rumah sakit", "jkn"],
    "Pendidikan": ["pendidikan", "sekolah", "ppdb", "bos"],
    "Pertanian dan Lingkungan Hidup": ["pertanian", "petani", "lingkungan hidup", "sampah", "air tanah"],
    "Sosial dan Kemasyarakatan": ["sosial", "bantuan sosial", "desa", "kemasyarakatan", "disabilitas"],
}

KANDIDAT2 = {
    "APBD dan keuangan daerah": [
        "anggaran pendapatan dan belanja daerah", "apbd",
        "keuangan daerah", "anggaran", "pendapatan", "belanja",
    ],
    "BUMD dan penyertaan modal": [
        "penyertaan modal", "badan usaha milik daerah", "bumn",
        "bpd", "perum", "persero",
    ],
    "pemilihan kepala daerah": [
        "pemilihan bupati", "pemilihan", "kada", "wakil bupati",
    ],
    "ketenagakerjaan": [
        "ketenagakerjaan", "pekerja", "migran", "buruh", "upah",
    ],
    "pelayanan umum dan jalan": [
        "pelayanan", "reklame", "jalan", "parkir", "perhubungan",
    ],
    "kesehatan dan penyakit": [
        "penyakit", "kesehatan", "puskesmas", "rumah sakit",
    ],
    "kebudayaan": [
        "kebudayaan", "budaya", "cagar budaya",
    ],
    "pendidikan": [
        "pesantren", "pendidikan", "sekolah", "siswa", "guru",
    ],
    "lingkungan dan air bersih": [
        "air minum", "air bersih", "lingkungan", "drainase", "sanitasi",
    ],
    "perdagangan dan ekonomi kreatif": [
        "ekonomi kreatif", "perdagangan", "koperasi",
        "umkm", "gudang", "tirta", "satria",
    ],
    "tata ruang dan perumahan": [
        "tata ruang", "perumahan", "permukiman", "kawasan", "rumah susun",
        "gedung", "bangunan",
    ],
    "pariwisata": [
        "pariwisata", "destinasi", "hotel",
    ],
    "pemuda dan olahraga": [
        "pemuda", "olahraga", "ketahora", "karang taruna",
    ],
    "pasar dan brasileño": [
        "pasar", "koperasi", "pedagang", "gudang",
    ],
}


def match_topics(judul):
    j = (judul or "").lower()
    return [l for l, k in TOPICS.items() if any(kw.lower() in j for kw in k)]


def main():
    csv.field_size_limit(100000000)
    with io.open(CSV_PERDA, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    tanpa = [r for r in rows if not match_topics(r["judul"])]

    print("=" * 78)
    print(f"PUTARAN 2 - tema pelengkap untuk {len(tanpa)} dokumen tanpa topik")
    print("=" * 78)

    for tema, kws in KANDIDAT2.items():
        hit = [r for r in tanpa if any(k in r["judul"].lower() for k in kws)]
        if not hit:
            continue
        detail = []
        for kw in kws:
            n = sum(1 for r in tanpa if kw in r["judul"].lower())
            if n:
                detail.append(f"{kw}({n})")
        print(f"\n### {tema.upper()}  -> {len(hit)}/58 judul")
        print("   " + ", ".join(detail))
        for r in hit:
            j = r["judul"].strip()
            j = j[:92] + "..." if len(j) > 92 else j
            print(f"      - [{r['tahun']}] {j}")

    t2 = set()
    for kws in KANDIDAT2.values():
        for r in tanpa:
            if any(k in r["judul"].lower() for k in kws):
                t2.add(r["nomor_tahun"])
    sisa = [r for r in tanpa if r["nomor_tahun"] not in t2]
    print()
    print("=" * 78)
    print(f"MASIH TIDAK TERTANGKAP: {len(sisa)}")
    print("=" * 78)
    for r in sisa:
        j = r["judul"].strip()
        j = j[:100] + "..." if len(j) > 100 else j
        print(f"   [{r['tahun']}] {j}")


if __name__ == "__main__":
    main()
