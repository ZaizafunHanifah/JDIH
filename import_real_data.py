import os
import re
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import init_db, get_db

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw_documents_export.csv")

TOPICS = {
    "Organisasi dan Tata Kerja Perangkat Daerah": ["organisasi", "tata kerja", "kedudukan", "susunan", "unit pelaksana teknis", "uptd"],
    "Standar Biaya dan Honorarium": ["standar biaya", "honorarium", "satuan biaya"],
    "Pengadaan Barang/Jasa": ["pengadaan barang", "pengadaan jasa", "lpse"],
    "Perencanaan Pembangunan Daerah": ["rkpd", "rpjmd", "rencana kerja pemerintah daerah", "rencana pembangunan", "penyertaan modal", "bumd", "badan usaha milik daerah", "perumda", "perumdam", "perseroan", "tata ruang", "perumahan", "permukiman", "kawasan", "rumah susun", "bangunan gedung"],
    "Kepegawaian dan Aparatur Sipil Negara": ["pegawai", "pns", "pppk", "aparatur sipil negara", "jabatan fungsional", "tambahan penghasilan"],
    "Pajak dan Retribusi Daerah": ["pajak", "retribusi", "pbb", "bphtb"],
    "Pelayanan Kesehatan": ["kesehatan", "puskesmas", "rumah sakit", "jkn", "penyakit"],
    "Pendidikan": ["pendidikan", "sekolah", "ppdb", "bos"],
    "Pertanian dan Lingkungan Hidup": ["pertanian", "petani", "lingkungan hidup", "sampah", "persampahan", "air tanah", "air minum"],
    "Sosial dan Kemasyarakatan": ["sosial", "bantuan sosial", "desa", "kemasyarakatan", "disabilitas"],
}


def match_topics(judul: str):
    """
    Cocokkan kata kunci topik ke judul memakai WORD BOUNDARY (\\b).

    Fungsi ini adalah SATU-SATUNYA sumber kebenaran pencocokan topik,
    dipakai bersama oleh import_real_data.py (Perbup) dan
    scraping_perda/kategorisasi_ulang.py (Perda).

    Kenapa harus \\b, bukan substring biasa:
      "bangunan" in "...pembangunan..."  -> True  (SALAH, 'bangunan'
                                           bukan kata utuh)
      "desa" in "...perdesaan..."        -> True  (SALAH)
      "pegawai" in "...kepegawaian..."   -> True  (SALAH)
    Dengan \\b hanya yang benar-benar berdiri sebagai kata utuh yang cocok.
    Case-insensitive. Diawali/followed oleh non-karakter [\\w] dianggap batas.
    """
    if not judul:
        return []
    judul_lower = judul.lower()
    matched = []
    for topic_label, keywords in TOPICS.items():
        for kw in keywords:
            # \b hanya berlaku di sekitar kata berhuruf; frasa dengan spasi
            # seperti "tata kerja" tetap aman karena \b menempel di ujungnya.
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", judul_lower):
                matched.append(topic_label)
                break
    return matched


def import_data():
    init_db()

    print("Membaca CSV...")
    csv.field_size_limit(10000000)
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Total baris data: {len(rows)}")
    print("Keterbatasan: Data asli hanya memiliki kolom 'tahun', tidak ada tanggal lengkap.")
    print("Menggunakan placeholder tanggal_terbit = '{tahun}-01-01' untuk semua dokumen.")

    with get_db() as conn:
        # PENGGAMAN: script ini menghapus SELURUH isi documents. Kalau ada
        # dokumen selain Peraturan Bupati (mis. Peraturan Daerah hasil
        # import_perda.py), hentikan - jangan ada DELETE yang dieksekusi.
        bocor = conn.execute(
            "SELECT jenis_dokumen, COUNT(*) FROM documents "
            "WHERE jenis_dokumen IS NULL OR jenis_dokumen <> ? "
            "GROUP BY jenis_dokumen",
            ("Peraturan Bupati",),
        ).fetchall()
        if bocor:
            print("=" * 78, file=sys.stderr)
            print("ERROR: import dibatalkan, tidak ada data yang dihapus.", file=sys.stderr)
            print("=" * 78, file=sys.stderr)
            for jenis, n in bocor:
                print(f"  - {jenis}: {n} dokumen", file=sys.stderr)
            print(
                "Database berisi dokumen selain Peraturan Bupati (kemungkinan "
                "Peraturan Daerah). Menjalankan script ini akan MENGHAPUS data "
                "tersebut. Batalkan, atau hapus manual pengaman ini jika memang "
                "disengaja.",
                file=sys.stderr,
            )
            print("=" * 78, file=sys.stderr)
            sys.exit(1)

        print("Menghapus data lama...")
        conn.execute("DELETE FROM document_topics")
        conn.execute("DELETE FROM documents")
        conn.execute("DELETE FROM topics")
        conn.commit()

        print("Insert topics...")
        topic_ids = {}
        for label, keywords in TOPICS.items():
            keywords_str = ", ".join(keywords)
            cur = conn.execute(
                "INSERT INTO topics (label_topik, top_keywords) VALUES (?, ?)",
                (label, keywords_str)
            )
            topic_ids[label] = cur.lastrowid
        print(f"  {len(topic_ids)} topik diinsert.")

        print("Insert documents...")
        doc_ids = []
        doc_topics_map = {}
        no_match_count = 0

        for row in rows:
            nomor = row["nomor"]
            tahun = row["tahun"]
            judul = row["judul"]
            url_pdf = row["url_pdf"]
            konten_text = row["konten_text"]

            tanggal_terbit = f"{tahun}-01-01"
            jenis_dokumen = "Peraturan Bupati"

            cur = conn.execute(
                """INSERT INTO documents (judul, nomor, tanggal_terbit, jenis_dokumen, url_pdf, konten_text)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (judul, nomor, tanggal_terbit, jenis_dokumen, url_pdf, konten_text)
            )
            doc_id = cur.lastrowid
            doc_ids.append(doc_id)

            matched_topics = match_topics(judul)
            if matched_topics:
                doc_topics_map[doc_id] = matched_topics
            else:
                no_match_count += 1

        conn.commit()
        print(f"  {len(doc_ids)} dokumen diinsert.")
        print(f"  Dokumen tanpa match topik: {no_match_count}")

        print("Insert document-topics relations...")
        rel_count = 0
        for doc_id, topic_labels in doc_topics_map.items():
            for label in topic_labels:
                topic_id = topic_ids[label]
                conn.execute(
                    "INSERT INTO document_topics (document_id, topic_id) VALUES (?, ?)",
                    (doc_id, topic_id)
                )
                rel_count += 1
        conn.commit()
        print(f"  {rel_count} relasi document-topics diinsert.")

    print("\n=== RINGKASAN ===")
    print(f"Total dokumen diimpor: {len(doc_ids)}")
    print(f"Dokumen tanpa match topik: {no_match_count}")

    with get_db() as conn:
        print("\nJumlah dokumen per topik:")
        for label, topic_id in topic_ids.items():
            count = conn.execute(
                "SELECT COUNT(*) FROM document_topics WHERE topic_id = ?", (topic_id,)
            ).fetchone()[0]
            print(f"  {label}: {count}")


if __name__ == "__main__":
    import_data()