import os
import sys
import random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import init_db, get_db


KABUPATEN = "Banyumas"
BASE_URL = "https://jdih.banyumaskab.go.id"

TOPICS = [
    {
        "label_topik": "Organisasi dan Tata Kerja Perangkat Daerah",
        "top_keywords": "organisasi, tata kerja, struktur, perangkat daerah, SKPD, Dinas, Sekretariat, Bidang"
    },
    {
        "label_topik": "Standar Biaya dan Honorarium",
        "top_keywords": "standar biaya, honorarium, satuan biaya, kegiatan, anggaran, APBD, upah, tantiem"
    },
    {
        "label_topik": "Pengadaan Barang/Jasa",
        "top_keywords": "pengadaan, barang, jasa, LKPP, LPSE, tender, seleksi, kontrak, rekanan"
    },
    {
        "label_topik": "Perencanaan Pembangunan Daerah",
        "top_keywords": "perencanaan, pembangunan, RPJMD, RKPD, musrenbang, program, kegiatan, indikator"
    },
    {
        "label_topik": "Kepegawaian dan Aparatur Sipil Negara",
        "top_keywords": "kepegawaian, PNS, PPPK, jabatan, pangkat, masa kerja, mutasi, promosi, pensiun"
    },
    {
        "label_topik": "Pajak dan Retribusi Daerah",
        "top_keywords": "pajak, retribusi, PBB, PBPHTB, BPHTB, PKB, pendapatan daerah, pajak daerah"
    },
    {
        "label_topik": "Pelayanan Kesehatan",
        "top_keywords": "kesehatan, puskesmas, rumah sakit, JKN, pelayanan, medis, nakes, fasilitas kesehatan"
    },
    {
        "label_topik": "Pendidikan",
        "top_keywords": "pendidikan, sekolah, guru, siswa, kurikulum, BOS, PPDB, PAUD, SD, SMP, SMA"
    },
    {
        "label_topik": "Pertanian dan Lingkungan Hidup",
        "top_keywords": "pertanian, petani, peternak, lingkungan, sampah, limbah, air tanah, hutan, kelautan"
    },
    {
        "label_topik": "Sosial dan Kemasyarakatan",
        "top_keywords": "sosial, bantuan, masyarakat, kemanusiaan, bencana, disabilitas, lansia, anak, perempuan"
    },
]


DINAS_LIST = [
    "Dinas Kesehatan",
    "Dinas Pekerjaan Umum dan Penataan Ruang",
    "Dinas Pendidikan",
    "Dinas Koperasi, Usaha Kecil dan Menengah",
    "Dinas Pertanian dan Ketahanan Pangan",
    "Dinas Perhubungan",
    "Dinas Lingkungan Hidup",
    "Dinas Sosial",
    "Dinas Kependudukan dan Pencatatan Sipil",
    "Dinas Komunikasi dan Informatika",
    "Dinas Kebudayaan dan Pariwisata",
    "Dinas Pemberdayaan Masyarakat dan Desa",
    "Dinas Ketahanan Pangan dan Pertanian",
    "Dinas Tenaga Kerja dan Transmigrasi",
    "Dinas Perindustrian dan Perdagangan",
    "Dinas Arsip dan Perpustakaan",
    "Sekretariat Daerah",
    "Inspektorat",
    "Badan Kepegawaian Daerah",
    "Badan Pendapatan Daerah",
    "Badan Perencanaan Pembangunan Daerah",
    "Badan Pengelolaan Keuangan dan Aset Daerah",
    "Badan Kesatuan Bangsa dan Politik",
    "Badan Penanggulangan Bencana Daerah",
]

SUBJEK_TEMPLATES = [
    {
        "kategori": "Organisasi dan Tata Kerja Perangkat Daerah",
        "templates": [
            "Organisasi dan Tata Kerja {dinas} pada {kabupaten}",
            "Kedudukan, Susunan Organisasi, Tugas dan Fungsi serta Tata Kerja {dinas}",
            "Pembentukan Unit Pelaksana Teknis Daerah pada {dinas}",
            "Perubahan Kedudukan, Susunan Organisasi, Tugas dan Fungsi {dinas}",
            "Struktur Organisasi dan Tata Kerja {dinas}",
        ],
        "topics": [0],
        "content_fn": lambda dinas, tahun: (
            f"Peraturan ini mengatur struktur organisasi, tata kerja, tugas, fungsi, dan kewenangan {dinas} "
            f"dalam mendukung pelaksanaan urusan pemerintahan di {KABUPATEN} Tahun {tahun}. "
            f"Mencakup pembagian Bidang, Seksi, dan UPTD beserta fungsi masing-masing."
        )
    },
    {
        "kategori": "Standar Biaya dan Honorarium",
        "templates": [
            "Standar Biaya Kegiatan dan Honorarium Tahun Anggaran {tahun}",
            "Penyesuaian Standar Biaya Satuan Kegiatan Perangkat Daerah Tahun {tahun}",
            "Standar Biaya Operasional dan Honorarium Pelaksana Kegiatan {tahun}",
            "Perubahan Atas Peraturan Bupati Tentang Standar Biaya Tahun {tahun_lalu}",
        ],
        "topics": [1],
        "content_fn": lambda dinas, tahun: (
            f"Menetapkan standar biaya satuan kegiatan dan besaran honorarium bagi pelaksana kegiatan "
            f"di lingkungan perangkat daerah {KABUPATEN} Tahun Anggaran {tahun}. "
            f"Berlaku untuk seluruh SKPD sebagai pedoman penganggaran aktivitas rutin dan tidak rutin."
        )
    },
    {
        "kategori": "Pengadaan Barang/Jasa",
        "templates": [
            "Pengadaan Barang dan Jasa Pemerintah di Lingkungan Pemerintah Kabupaten {kabupaten}",
            "Tata Cara Pengadaan Barang/Jasa Menggunakan Sistem Elektronik (LPSE) {kabupaten}",
            "Perubahan Kedua Atas Peraturan Bupati Tentang Pengadaan Barang/Jasa {kabupaten}",
            "Pedoman Teknis Pemilihan Rekanan Pengadaan Barang/Jasa {kabupaten}",
        ],
        "topics": [2],
        "content_fn": lambda dinas, tahun: (
            f"Mengatur tata cara pengadaan barang dan jasa pemerintah di {KABUPATEN} sesuai peraturan LKPP. "
            f"Mencakup metode seleksi, e-purchasing via LPSE, evaluasi penawaran, dan penetapan pemenang. "
            f"Tujuannya memastikan efisiensi, transparansi, dan akuntabilitas pengeluaran APBD."
        )
    },
    {
        "kategori": "Perencanaan Pembangunan Daerah",
        "templates": [
            "Rencana Kerja Pemerintah Daerah (RKPD) Kabupaten {kabupaten} Tahun {tahun}",
            "Rencana Aksi Daerah (RAD) Bidang {bidang} Tahun {tahun}",
            "Perubahan Atas Peraturan Bupati Nomor {nomor_lalu} Tahun {tahun_lalu} Tentang RKPD {tahun_lalu}",
            "Penetapan Indikator Kinerja Program dan Kegiatan Perangkat Daerah Tahun {tahun}",
        ],
        "topics": [3],
        "content_fn": lambda dinas, tahun: (
            f"Menetapkan Rencana Kerja Pemerintah Daerah {KABUPATEN} Tahun {tahun} yang disusun "
            f"berdasarkan RPJMD dan hasil Musrenbang. Memuat program prioritas, target indikator, "
            f"dan alokasi anggaran per perangkat daerah untuk mewujudkan visi misi pembangunan daerah."
        )
    },
    {
        "kategori": "Kepegawaian dan Aparatur Sipil Negara",
        "templates": [
            "Tambahan Penghasilan Pegawai Aparatur Sipil Negara di Lingkungan {kabupaten}",
            "Jabatan Fungsional dan Angka Kredit {kabupaten} Tahun {tahun}",
            "Mutasi, Promosi, dan Pengangkatan Pegawai Negeri Sipil {kabupaten}",
            "Disiplin dan Kode Etik Aparatur Sipil Negara Perangkat Daerah {kabupaten}",
            "Peraturan Pelaksanaan Manajemen ASN {kabupaten}",
        ],
        "topics": [4],
        "content_fn": lambda dinas, tahun: (
            f"Mengatur hak-hak keuangan, jabatan fungsional, angka kredit, mutasi, promosi, dan disiplin "
            f"bagi Pegawai Negeri Sipil (PNS) dan Pegawai Pemerintah dengan Perjanjian Kerja (PPPK) "
            f"di lingkungan perangkat daerah {KABUPATEN}. Berlaku sejak Tahun {tahun}."
        )
    },
    {
        "kategori": "Pajak dan Retribusi Daerah",
        "templates": [
            "Penyelenggaraan Pajak Daerah dan Retribusi {kabupaten}",
            "Tarif Retribusi Jasa Pelayanan Umum {kabupaten} Tahun {tahun}",
            "Pungutan Pajak Bumi dan Bangunan Perdesaan dan Perkotaan {kabupaten}",
            "Insentif dan Sanksi Pajak Daerah {kabupaten}",
            "Perubahan Atas Peraturan Bupati Nomor {nomor_lalu} Tahun {tahun_lalu} Tentang Retribusi",
        ],
        "topics": [5],
        "content_fn": lambda dinas, tahun: (
            f"Mengatur jenis, tarif, cara penghitungan, penyetoran, dan pelaporan pajak daerah serta retribusi "
            f"di {KABUPATEN}. Mencakup PBB-P2, BPHTB, retribusi jasa pelayanan umum, retribusi izin, "
            f"dan insentif pembayaran tepat waktu bagi wajib pajak Tahun {tahun}."
        )
    },
    {
        "kategori": "Pelayanan Kesehatan",
        "templates": [
            "Standar Pelayanan Kesehatan Dasar di {kabupaten}",
            "Pengelolaan Rumah Sakit Umum Daerah (RSUD) {kabupaten}",
            "Jaminan Kesehatan Nasional (JKN) Bagi Masyarakat Miskin {kabupaten}",
            "Pencegahan dan Pengendalian Penyakit Menular {kabupaten} Tahun {tahun}",
            "Standar Mutu Pelayanan Puskesmas {kabupaten}",
        ],
        "topics": [6],
        "content_fn": lambda dinas, tahun: (
            f"Menetapkan standar minimal pelayanan kesehatan di puskesmas dan RSUD {KABUPATEN}, "
            f"termasuk jaminan akses JKN bagi penerima bantuan iuran (PBI), standar mutu medis, "
            f"dan tata kelola fasilitas kesehatan tingkat kabupaten Tahun {tahun}."
        )
    },
    {
        "kategori": "Pendidikan",
        "templates": [
            "Penyelenggaraan Pendidikan Dasar dan Menengah di {kabupaten}",
            "Bantuan Operasional Sekolah (BOS) Daerah {kabupaten} Tahun {tahun}",
            "Penerimaan Peserta Didik Baru (PPDB) Zona {kabupaten} Tahun {tahun}",
            "Perlindungan Anak di Lingkungan Satuan Pendidikan {kabupaten}",
            "Penguatan Karakter dan Pendidikan Agama di Sekolah {kabupaten}",
        ],
        "topics": [7],
        "content_fn": lambda dinas, tahun: (
            f"Mengatur penyelenggaraan pendidikan SD/SMP/SMA/SMK di {KABUPATEN}, mencakup zonasi PPDB, "
            f"bantuan BOS Daerah, perlindungan anak dari kekerasan di sekolah, dan penguatan karakter. "
            f"Berlaku Tahun Pelajaran {tahun}/{tahun+1}."
        )
    },
    {
        "kategori": "Pertanian dan Lingkungan Hidup",
        "templates": [
            "Perlindungan Petani dan Peternak serta Ketahanan Pangan {kabupaten}",
            "Pengelolaan Air Tanah dan Sumber Daya Air {kabupaten}",
            "Pengelolaan Sampah dan Limbah Berbasis 3R {kabupaten}",
            "Pemberian Izin Pengambilan Air Tanah {kabupaten}",
            "Mitigasi Bencana Banjir dan Longsor di Wilayah {kabupaten}",
        ],
        "topics": [8],
        "content_fn": lambda dinas, tahun: (
            f"Mengatur perlindungan petani/peternak, subsidi pupuk, asuransi usaha tani, pengelolaan air tanah, "
            f"sampah berbasis 3R, dan mitigasi bencana banjir/longsor di {KABUPATEN} Tahun {tahun}. "
            f"Bertujuan mewujudkan ketahanan pangan dan lingkungan hidup yang berkelanjutan."
        )
    },
    {
        "kategori": "Sosial dan Kemasyarakatan",
        "templates": [
            "Pelaksanaan Bantuan Sosial (Bansos) Bagi Masyarakat Rentan {kabupaten}",
            "Perlindungan Korban Kekerasan Seksual dan Kekerasan Berbasis Gender {kabupaten}",
            "Pemberdayaan Masyarakat Adat dan Lokal {kabupaten}",
            "Rehabilitasi Sosial Penyandang Disabilitas {kabupaten}",
            "Tanggulangan Kemiskinan dan Ketidakmampuan Ekonomi {kabupaten} Tahun {tahun}",
        ],
        "topics": [9],
        "content_fn": lambda dinas, tahun: (
            f"Mengatur program bantuan sosial, perlindungan perempuan dan anak, pemberdayaan masyarakat adat, "
            f"rehabilitasi sosial disabilitas, dan tanggulangan kemiskinan di {KABUPATEN} Tahun {tahun}. "
            f"Mencakup kriteria penerima, mekanisme pendaftaran, penyaluran, dan pengawasan."
        )
    },
]


def generate_documents(jenis_dokumen, num_docs, seed=42):
    random.seed(seed)
    documents = []
    
    # Distribusi tahun: lebih banyak di tahun recent
    year_weights = {
        2011: 3, 2012: 3, 2013: 3, 2014: 3, 2015: 3,
        2016: 5, 2017: 5, 2018: 5, 2019: 5, 2020: 5,
        2021: 8, 2022: 8, 2023: 10, 2024: 12, 2025: 12, 2026: 10,
    }
    
    total_weight = sum(year_weights.values())
    year_counts = {y: max(1, round(w * num_docs / total_weight)) for y, w in year_weights.items()}
    diff = num_docs - sum(year_counts.values())
    years = list(year_weights.keys())
    for i in range(abs(diff)):
        year_counts[years[i % len(years)]] += 1 if diff > 0 else -1
    
    # cat_weights per jenis dokumen
    CAT_WEIGHTS = {
        "Peraturan Bupati": [15, 15, 8, 8, 10, 8, 8, 8, 10, 10],
        "Peraturan Daerah": [15, 15, 8, 8, 10, 8, 8, 8, 10, 10],
        "Surat Keputusan": [30, 5, 20, 5, 25, 5, 5, 5, 0, 0],
        "Surat Edaran": [10, 5, 5, 5, 10, 5, 20, 20, 10, 10],
        "Peraturan Desa": [5, 5, 5, 10, 5, 5, 10, 10, 20, 25],
    }
    cat_weights = CAT_WEIGHTS.get(jenis_dokumen, CAT_WEIGHTS["Peraturan Bupati"])
    
    # judul & nomor format per jenis
    def make_judul(nomor_seq, year, judul_template):
        formats = {
            "Peraturan Bupati": f"Peraturan Bupati {KABUPATEN} Nomor {nomor_seq} Tahun {year} Tentang {judul_template}",
            "Peraturan Daerah": f"Peraturan Daerah Kabupaten {KABUPATEN} Nomor {nomor_seq} Tahun {year} Tentang {judul_template}",
            "Surat Keputusan": f"Keputusan Bupati {KABUPATEN} Nomor {nomor_seq} Tahun {year} Tentang {judul_template}",
            "Surat Edaran": f"Surat Edaran Bupati {KABUPATEN} Nomor {nomor_seq} Tahun {year} Tentang {judul_template}",
            "Peraturan Desa": f"Peraturan Desa Nomor {nomor_seq} Tahun {year} Tentang {judul_template}",
        }
        return formats.get(jenis_dokumen, formats["Peraturan Bupati"])
    
    def make_nomor(nomor_seq, year):
        formats = {
            "Peraturan Bupati": f"{nomor_seq}/{year}",
            "Peraturan Daerah": f"Perda No. {nomor_seq} Tahun {year}",
            "Surat Keputusan": f"SK No. {nomor_seq}/{year}",
            "Surat Edaran": f"SE No. {nomor_seq}/{year}",
            "Peraturan Desa": f"Perdes No. {nomor_seq} Tahun {year}",
        }
        return formats.get(jenis_dokumen, formats["Peraturan Bupati"])
    
    def make_url(nomor_seq, year):
        slug = jenis_dokumen.lower().replace(" ", "-").replace("peraturan-", "").replace("kabupaten-", "")
        return f"{BASE_URL}/{slug}-{nomor_seq}-{year}.pdf"
    
    for year in range(2011, 2027):
        count = year_counts.get(year, 0)
        nomor_seq = 0
        
        for _ in range(count):
            nomor_seq += 1
            
            cat_idx = random.choices(range(len(SUBJEK_TEMPLATES)), weights=cat_weights, k=1)[0]
            cat = SUBJEK_TEMPLATES[cat_idx]
            
            template = random.choice(cat["templates"])
            dinas = random.choice(DINAS_LIST)
            bidang = random.choice(["Pendidikan", "Kesehatan", "Pertanian", "Pekerjaan Umum", "Sosial", "Ekonomi"])
            
            judul_template = template.format(
                dinas=dinas,
                kabupaten=KABUPATEN,
                tahun=year,
                tahun_lalu=year-1,
                nomor_lalu=nomor_seq-1 if nomor_seq > 1 else 1,
                bidang=bidang,
            )
            
            judul = make_judul(nomor_seq, year, judul_template)
            nomor = make_nomor(nomor_seq, year)
            
            start_of_year = date(year, 1, 1)
            random_day = random.randint(0, 364)
            tanggal_terbit = (start_of_year + timedelta(days=random_day)).isoformat()
            
            url_pdf = make_url(nomor_seq, year)
            konten_text = cat["content_fn"](dinas, year)
            
            primary_topics = cat["topics"]
            if random.random() < 0.3 and len(primary_topics) < 2:
                secondary_options = [i for i in range(len(TOPICS)) if i not in primary_topics]
                if secondary_options:
                    primary_topics = primary_topics + [random.choice(secondary_options)]
            
            documents.append({
                "judul": judul,
                "nomor": nomor,
                "tanggal_terbit": tanggal_terbit,
                "jenis_dokumen": jenis_dokumen,
                "url_pdf": url_pdf,
                "konten_text": konten_text,
                "topic_indices": primary_topics,
            })
    
    return documents


def seed_database():
    init_db()
    documents = []
    documents += generate_documents("Peraturan Bupati", 60, seed=42)
    documents += generate_documents("Peraturan Daerah", 20, seed=43)
    documents += generate_documents("Surat Keputusan", 40, seed=44)
    documents += generate_documents("Surat Edaran", 20, seed=45)
    documents += generate_documents("Peraturan Desa", 10, seed=46)
    
    with get_db() as conn:
        conn.execute("DELETE FROM document_topics")
        conn.execute("DELETE FROM documents")
        conn.execute("DELETE FROM topics")
        conn.commit()

        topic_ids = {}
        for topic in TOPICS:
            cur = conn.execute(
                "INSERT INTO topics (label_topik, top_keywords) VALUES (?, ?)",
                (topic["label_topik"], topic["top_keywords"])
            )
            topic_ids[topic["label_topik"]] = cur.lastrowid

        doc_ids = []
        for doc in documents:
            cur = conn.execute(
                """INSERT INTO documents (judul, nomor, tanggal_terbit, jenis_dokumen, url_pdf, konten_text)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (doc["judul"], doc["nomor"], doc["tanggal_terbit"], doc["jenis_dokumen"], doc["url_pdf"], doc["konten_text"])
            )
            doc_ids.append(cur.lastrowid)

        for i, doc in enumerate(documents):
            doc_id = doc_ids[i]
            for topic_idx in doc["topic_indices"]:
                topic_label = TOPICS[topic_idx]["label_topik"]
                topic_id = topic_ids[topic_label]
                conn.execute(
                    "INSERT INTO document_topics (document_id, topic_id) VALUES (?, ?)",
                    (doc_id, topic_id)
                )

        conn.commit()
        print(f"Seeded {len(doc_ids)} documents, {len(topic_ids)} topics.")
        print(f"Total document-topic relations: {sum(len(d['topic_indices']) for d in documents)}")


if __name__ == "__main__":
    seed_database()