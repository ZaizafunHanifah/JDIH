"""
Analisis 58 dokumen Perda yang tidak match topik manapun dari 10 kategori
eksisting. Murni ANALISIS - tidak mengubah TOPICS di import_real_data.py.

Jalankan: python analisis_tanpa_topik.py
"""
import collections
import csv
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PERDA = os.path.join(BASE, "perda_export.csv")
CSV_PERBUP = os.path.join(os.path.dirname(BASE), "raw_documents_export.csv")

# Salinan PERSIS dari import_real_data.py - dipakai untuk menentukan
# dokumen mana yang sudah match, TIDAK diubah di sini.
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


def match_topics(judul):
    j = (judul or "").lower()
    out = []
    for label, kws in TOPICS.items():
        if any(kw.lower() in j for kw in kws):
            out.append(label)
    return out


# Kata/frasa kandidat per tema, dari pembacaan 58 judul.
# Dihitung frekuensinya di dalam 58 judul tanpa-topik saja.
KANDIDAT = {
    "tata ruang": ["tata ruang", "perencanaan wilayah", "kawasan", "permukiman", "zona"],
    "bangunan": ["bangunan", "gedung", "rumah susun"],
    "pariwisata": ["pariwisata", "destinasi", "hotel", "dunia wisata"],
    "lingkungan hidup": ["lingkungan hidup", "lingkungan", "sampah"],
    "kebersihan dan prasarana": ["kebersihan", "kotoran", "sarana", "prasarana"],
    "pasar dan perdagangan": ["pasar", "perdagangan", "pedagang", "umkm", "koperasi"],
    "pertanian": ["pertanian", "petani", "perkebunan", "lumbung"],
    "keluarga dan kependudukan": ["keluarga", "kkk", "penduduk", "kewargaan", "bansos"],
    "pendidikan": ["pendidikan", "sekolah", "siswa", "guru", "kampus"],
    "kesehatan": ["kesehatan", "posyandu", "rumah sakit", "puskesmas"],
    "sumber daya air": ["air tanah", "sumber daya air", "irigasi", "air bersih", "drainase"],
    "transportasi": ["transportasi", "lalu lintas", "parkir", "jalan", "kendaraan"],
    "industri dan usaha": ["industri", "perusahaan", "usaha", "pabrik"],
    "budaya": ["budaya", "seni", "cagar budaya", "warisan"],
    "pemuda dan olahraga": ["pemuda", "olahraga", "ketahora", "ketidra", "karang taruna"],
    "tanah dan pertanahan": ["tanah", "pertanahan", "pers tanah"],
    "permukiman dan perumahan": ["permukiman", "perumahan", "perumnas"],
}


def main():
    csv.field_size_limit(100000000)
    with io.open(CSV_PERDA, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    tanpa = [r for r in rows if not match_topics(r["judul"])]
    dengan = [r for r in rows if match_topics(r["judul"])]

    print("=" * 78)
    print(f"DOKUMEN PERDA TANPA MATCH TOPIK: {len(tanpa)} dari {len(rows)}")
    print("=" * 78)

    # ---------- 1. semua judul ----------
    print()
    print("DAFTAR LENGKAP 58 JUDUL (dipotong 100 karakter):")
    print("-" * 78)
    for i, r in enumerate(tanpa, 1):
        judul = r["judul"].strip()
        if len(judul) > 100:
            judul = judul[:100] + "..."
        th = r["tahun"]
        print(f"{i:>2}. [{th}] {judul}")

    # ---------- 2. kata sering ----------
    print()
    print("=" * 78)
    print("KATA YANG SERING MUNCUL DI 58 JUDUL")
    print("=" * 78)
    stop = {"peraturan", "daerah", "kabupaten", "banyumas", "nomor", "tahun",
            "tentang", "penjelasan", "atas", "dan", "dalam", "untuk", "dari",
            "yang", "dengan", "pada", "ke", "di", "perubahan", "pertama",
            "kedua", "ketiga", "keempat", "kelima"}
    kata = collections.Counter()
    for r in tanpa:
        for w in re.findall(r"[a-z]{4,}", r["judul"].lower()):
            if w not in stop:
                kata[w] += 1
    print("Top 45 kata (tidak termasuk kata umum):")
    for w, c in kata.most_common(45):
        print(f"   {w:<24}: {c}")

    # ---------- 3. frekuensi kandidat per tema ----------
    print()
    print("=" * 78)
    print("FREKUENSI KATA KANDIDAT PER TEMA (dihitung di 58 judul)")
    print("=" * 78)
    tempairs = []
    for tema, kws in KANDIDAT.items():
        hit = []
        for r in tanpa:
            j = r["judul"].lower()
            if any(k in j for k in kws):
                hit.append(r)
        if hit:
            detail = []
            for kw in kws:
                n = sum(1 for r in tanpa if kw in r["judul"].lower())
                if n:
                    detail.append(f"{kw}({n})")
            tempairs.append((tema, len(hit), detail, hit))
    tempairs.sort(key=lambda x: -x[1])
    for tema, n, detail, hit in tempairs:
        print(f"\n{tema.upper()}  -> {n} judul")
        print("   kata: " + ", ".join(detail))
        for r in hit:
            j = r["judul"].strip()
            j = j[:95] + "..." if len(j) > 95 else j
            print(f"      - [{r['tahun']}] {j}")

    # dokumen yang tidak tertangkap kandidat sama sekali
    tertangkap = set()
    for _, _, _, hit in tempairs:
        for r in hit:
            tertangkap.add(r["nomor_tahun"])
    sisa = [r for r in tanpa if r["nomor_tahun"] not in tertangkap]
    print()
    print("=" * 78)
    print(f"DOKUMEN YANG TIDAK TERTANGKAP KANDIDAT APAPUN: {len(sisa)}")
    print("=" * 78)
    for r in sisa:
        j = r["judul"].strip()
        j = j[:100] + "..." if len(j) > 100 else j
        print(f"   [{r['tahun']}] {j}")


if __name__ == "__main__":
    main()
