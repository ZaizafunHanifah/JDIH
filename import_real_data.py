import os
import sys
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import init_db, get_db

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw_documents_export.csv")

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


def match_topics(judul: str):
    judul_lower = judul.lower()
    matched = []
    for topic_label, keywords in TOPICS.items():
        for kw in keywords:
            if kw.lower() in judul_lower:
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