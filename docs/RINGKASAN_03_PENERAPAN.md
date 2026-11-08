# RINGKASAN 03 — PENERAPAN KE JDIH ASLI

## 1. Titik Awal: Sumber Scraping

Sumber: `scraping_perda/metadata_perda_final.json` (92 entri) dan `raw_documents_export.csv`.

Field yang ada pada hasil scraping (contoh nilai):
- `id`: 928
- `no_peraturan`: "1"
- `tahun`: "2020"
- `judul`: "Peraturan Daerah Kabupaten Banyumas Nomor 1 Tahun 2020 Tentang Pencabutan..."
- `status`: "Tidak Berlaku"
- `url_detail`: "https://jdih.banyumaskab.go.id/produk-hukum/928/detail"
- `Nomor Peraturan`: "1"
- `Tahun Terbit`: "2020"
- `Tanggal Penetapan`: "10 Februari 2020"
- `Status Peraturan`: "Tidak Berlaku Dicabut PERATURAN DAERAH Nomor 1 Tahun 2020 (...)"
- `Bidang Hukum`: "Hukum Tata Negara"
- `Subjek`: "RETRIBUSI"
- `status_hukum`: "Tidak Berlaku"
- `catatan_relasi`: "Dicabut PERATURAN DAERAH Nomor 1 Tahun 2020 (...)"
- `url_pdf`: "https://jdih.banyumaskab.go.id/downloadprodukhukum/928"
- `status_ekstraksi`: "ok"
- `path_teks`: "text_raw/928.txt"
- `panjang_teks`: 5013
- `jumlah_halaman`: 4
- `ukuran_pdf_kb`: 127.5
- `alasan_gagal`: None (atau alasan jika gagal)

Definisi tabel sumber_scraping = metadata di atas + link PDF; tanpa teks, topik, pasal.

## 2. Pipeline dari Titik Awal sampai Siap Dicari

| Tahap | Input | Proses | Output | Skrip | Pemeriksaan angka |
|---|---|---|---|---|---|
| 1 | metadata JSON + CSV | import dokumen | tabel `documents` (kolom dasar) | `import_real_data.py` [KODE] | jumlah dokumen = jumlah entri scraping |
| 2 | raw_content_export.csv | import teks mentah | `konten_text_asli`, `konten_text` | `import_raw_content.py` [KODE] | jumlah non-NULL = jumlah PDF dengan teks |
| 3 | dokumen + teks | buat tsvector + index | `konten_tsv`, index GIN, trigger | `init_db()` di `app/db.py` [KODE] | COUNT WHERE konten_tsv IS NULL = 0 |
| 4 | teks + topik | kategorisasi topik otomatis (KMeans k=10 pada TF-IDF judul) | `topics`, `document_topics` | `terapkan_topik_otomatis.py` [KODE] | jumlah relasi = jumlah dokumen (469) |


## 3. Tabel Keputusan

| # | Kandidat | Sudah ada? | Fungsi | Kolom kunci | Diisi oleh | Dipakai fitur | Prioritas | Bukti |
|---|---|---|---|---|---|---|---|---|
| a | teks mentah + teks cari + tsvector + nomor_tahun + status_hukum + catatan_relasi | Ya (`documents`) | teks dokumen + indeks + metadata | konten_text_asli, konten_text, konten_tsv, nomor_tahun, status_hukum, catatan_relasi | import_real_data/import_raw_content | pencarian, filter, status | WAJIB | `app/db.py`, `app/routers/documents.py` |
| b | topics + document_topics | Ya | topik + relasi | label_topik, top_keywords, document_id, topic_id | seed/import (diduga) | filter topik, UI | WAJIB | `app/routers/topics.py` |
| c | tabel pasal pra-ekstraksi + tsvector per pasal | Belum | mempercepat pencarian pasal | — | BELUM ADA | Tanya Tata Cara | DISARANKAN skala besar | `_cari_pasal_relevan` panggil `extract_pasal` on-demand |
| d | log ekstraksi per dokumen | Belum | audit (halaman, status, alasan gagal, tanggal) | — | BELUM ADA | monitoring | DISARANKAN | info ada di JSON/CSV scraping |
| e | relasi dokumen terstruktur (mencabut/mengubah) | Belum (hanya kolom catatan_relasi) | relasi antar dokumen | — | BELUM ADA | tampilan relasi | DISARANKAN | `catatan_relasi` text di documents |
| f | tabel sinonim | Belum (di `synonyms.py`) | sinonim keyword | — | BELUM ADA | tsquery tahap 2 | OPSIONAL | `app/synonyms.py` |
| g | log pencarian + set uji | Belum | audit kualitas | — | BELUM ADA | evaluasi | OPSIONAL | tidak ada di kode |
| h | versi skema + riwayat impor | Belum | audit migrasi | — | BELUM ADA | ops | OPSIONAL | tidak ada di kode |

Kandidat lain: tabel `cache_perbup.json` / `errors_perbup.json` (scraping) — sekarang file JSON, bukan tabel; disarankan jadi tabel jika scraping diotomatisasi.

## 4. Usulan Skema (docs/usulan_skema.sql)

File terpisah `docs/usulan_skema.sql` berisi CREATE TABLE untuk tabel yang belum ada (pasal, log_ekstraksi, relasi_dokumen, sinonim, log_pencarian, versi_skema). JANGAN dijalankan (hanya usulan).

## 5. Runbook Penerapan

1. Backup: `pg_dump` database sumber. Titik berhenti: file backup ada.
2. Buat database baru, jalankan `init_db()` (`app/db.py`) → tabel + index + trigger.
3. Import metadata: `import_real_data.py`. Cek: COUNT documents = jumlah entri scraping.
4. Import teks mentah: `import_raw_content.py`. Cek: COUNT konten_text_asli IS NOT NULL.
5. Backfill tsvector: `UPDATE ... WHERE konten_tsv IS NULL`. Cek: COUNT konten_tsv IS NULL = 0.
6. Import topik otomatis: 	erapkan_topik_otomatis.py. Cek: COUNT document_topics = COUNT documents.
7. Jalankan server `uvicorn app.main:app --reload`. Cek: `/api/documents` mengembalikan data.
8. Uji endpoint `/api/documents/tata-cara?q=...`. Titik berhenti: respons ditemukan/tidak_ditemukan sesuai ekspektasi.

## 6. Risiko dan Hal Belum Diuji

- [BELUM DIUJI] Skala: beban pengguna bersamaan, waktu respons pada data penuh.
- [BELUM DIUJI] Kualitas jawaban: akurasi Tanya Tata Cara pada domain nyata.
- Bukti dari data [DB]: 47 dokumen tanpa teks (PDF scanned), 386 Perbup tanpa status_hukum, 0 dokumen tanpa topik (semua 469 terkategori otomatis), cakupan topik hanya 10 topik.
- Risiko [KODE]: `extract_pasal` dipanggil on-demand (tidak ada cache pasal) → beban CPU per request.
- Risiko [KODE]: `potong_penjelasan` memotong berdasarkan penanda; dokumen tanpa penanda dibiarkan apa adanya (22 dokumen pasal terakhir > 5000 chars).
- Risiko [DUGAAN]: sinonim di `synonyms.py` statis, perlu update manual.
