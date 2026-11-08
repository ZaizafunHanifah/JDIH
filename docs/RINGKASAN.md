# RINGKASAN APLIKASI JDIH FITUR TAMBAHAN

## Daftar Isi

1. RINGKASAN_01_ALUR.md — Alur Aplikasi (bagian A-H)
2. RINGKASAN_02_DATABASE.md — Database PostgreSQL (bagian A-I)
3. RINGKASAN_03_PENERAPAN.md — Penerapan ke JDIH Asli (bagian 1-6)

## Glosarium (15 istilah)

- FTS (Full-Text Search): pencarian teks lengkap di PostgreSQL.
- tsvector: tipe data PostgreSQL untuk indeks teks.
- GIN: jenis indeks untuk pencarian cepat pada tsvector.
- trigger: fungsi otomatis yang berjalan saat INSERT/UPDATE.
- regex: pola pencocokan teks.
- endpoint: URL API yang bisa dipanggil.
- pool koneksi: kumpulan koneksi database yang digunakan ulang.
- ekstraksi: proses mengambil teks dari PDF.
- tsquery: query pencarian PostgreSQL.
- ts_rank: skor relevansi PostgreSQL.
- pasal: bagian bernomor dalam peraturan.
- sinonim: kata pengganti untuk perluasan pencarian.
- topik: kategori dokumen.
- konten_tsv: kolom tsvector untuk pencarian.
- potong_penjelasan: fungsi pemotong bagian Penjelasan.

## Tabel Terbukti vs Belum Terbukti

| Klaim | Label | Sumber |
|---|---|---|
| 469 dokumen (386 Perbup + 83 Perda) | [DB] | COUNT documents |
| 47 dokumen tanpa teks (PDF scanned) | [DB] | COUNT konten_text_asli IS NULL |
| 386 Perbup tanpa status_hukum | [DB] | COUNT status_hukum IS NULL |
| 0 dokumen tanpa topik (semua 469 terkategori otomatis) | [DB] | COUNT NOT EXISTS document_topics |
| performa query pada data penuh | [BELUM DIUJI] | tidak diukur |
| kualitas jawaban Tanya Tata Cara | [BELUM DIUJI] | tidak diuji |
| beban pengguna bersamaan | [BELUM DIUJI] | tidak diukur |
| sinonim statis perlu update manual | [DUGAAN] | app/synonyms.py statis |
| skrip pengisi topik = terapkan_topik_otomatis.py | [DUGAAN] | tidak diverifikasi eksekusi |
| skrip ekstraksi pasal on-demand | [KODE] | app/pasal_extractor.py dipanggil di documents.py |

---

# RINGKASAN 01 — ALUR APLIKASI JDIH FITUR TAMBAHAN

## A. Gambaran Umum

Aplikasi web untuk pencarian dokumen hukum (Peraturan Bupati dan Peraturan Daerah Kabupaten Banyumas) yang dilengkapi fitur "Tanya Tata Cara" (pencarian prosedur dalam teks dokumen).

- Tech stack [KODE]: FastAPI (`app/main.py`), Jinja2 templates (`templates/index.html`), static files (`static/`), PostgreSQL (konfigurasi di `app/db.py`, password (disembunyikan)), Python 3.13.
- Database [DB]: tabel `documents` (id, judul, nomor, tanggal_terbit, url_pdf, konten_text, konten_text_asli, jenis_dokumen, status_hukum, catatan_relasi, nomor_tahun, konten_tsv), `topics`, `document_topics`.
- Entri dokumen [DB]: 469 total (386 Perbup + 83 Perda).

## B. Peta File per Tahap

- `app/main.py` [KODE]: inisialisasi FastAPI, mount static, include router, startup `init_db()`.
- `app/db.py` [KODE]: koneksi PostgreSQL, `init_db()` (buat tabel + index tsvector), `get_db()`.
- `app/routers/documents.py` [KODE]: endpoint dokumen, `_cari_tahap`, `_cari_pasal_relevan`, `_extract_main_keywords`, `bangun_tsquery`, `potong_penjelasan` (import).
- `app/routers/topics.py`, `metadata.py`, `status.py` [KODE]: endpoint topik, jenis dokumen, status hukum.
- `app/pasal_extractor.py` [KODE]: `extract_pasal`, `_is_pasal_definisi`, `potong_penjelasan`.
- `app/synonyms.py` [KODE]: `sinonim_dari`.
- `static/app.js`, `templates/index.html` [KODE]: frontend.
- `import_real_data.py`, `import_raw_content.py` [KODE]: import data SQLite→Postgres dan teks mentah.

## C. Alur Menyalakan Server

1. `python -m venv venv` lalu install `requirements.txt` (fastapi, uvicorn, jinja2).
2. Set env `DB_PASSWORD` (disembunyikan).
3. `uvicorn app.main:app --reload` → server di `http://localhost:8000`.
4. Startup menjalankan `init_db()` yang membuat tabel/index tsvector (PostgreSQL native, pengganti FTS5 SQLite).

Pencarian full-text memakai `to_tsvector('simple', ...)` + `to_tsquery('simple', ...)` + `ts_rank` (lihat `app/routers/documents.py` fungsi `bangun_tsquery` dan `_cari_tahap`).

## D. Tabel Endpoint

| Method | Path | Fungsi (file:baris) |
|---|---|---|
| GET | `/` | index (`app/main.py`) |
| GET | `/api/documents` | get_documents (`documents.py:260`) |
| GET | `/api/documents/{doc_id}` | get_document (`documents.py:473`) |
| GET | `/api/documents/{doc_id}/prosedur` | get_document_prosedur (`documents.py:354`) |
| GET | `/api/documents/tata-cara?q=` | tata_cara (`documents.py:371`) |
| GET | `/api/topics` | get_topics (`topics.py`) |
| GET | `/api/jenis-dokumen` | get_jenis_dokumen (`metadata.py`) |
| GET | `/api/tahun` | get_tahun (`metadata.py`) |
| GET | `/api/status-hukum` | daftar_status_hukum (`status.py`) |

## E. Alur "Tanya Tata Cara" (contoh nyata)

Query: `cara bayar pajak restoran` (dijalankan read-only lewat fungsi aplikasi).

1. `_extract_main_keywords(q)` (`documents.py`) → `['bayar', 'pajak', 'restoran']` (kata "cara" dibuang oleh `_COMMON_WORDS` di `documents.py:57`).
2. Tahap 1 (strik): `bangun_tsquery(keywords, False)` → `bayar & pajak & restoran`. Kandidat dari `konten_tsv @@ to_tsquery`. Untuk tiap kandidat (top 10 by ts_rank), `_cari_pasal_relevan` memanggil `potong_penjelasan` lalu `extract_pasal`, lalu filter: `is_procedural=True`, bukan definisi, dan memenuhi SEMUA keyword (`_pasal_memenuhi_keyword`, threshold 1.0 untuk ≤3 keyword).
3. Hasil [DB]: dokumen id 922, Perbup 48/2020, non-perubahan, 18 pasal relevan. `pencocokan=strik`.
4. Jika tahap 1 tidak menghasilkan non-perubahan dengan pasal lolos, tahap 2 (longgar) dijalankan sebagai cadangan: pasal lolos bila skor >= 1 (minimal satu grup keyword).

## F. Pipeline Data Masuk

1. `import_real_data.py`: import dokumen dari SQLite `jdih.db` → PostgreSQL `documents` (konten_text_asli sengaja NULL).
2. `import_raw_content.py`: isi `konten_text_asli` dari `raw_content_export.csv` (kolom `konten_mentah`).
3. `init_db()` (`app/db.py`): buat kolom `konten_tsv` (tsvector) + index GIN + trigger `documents_tsv_update` + backfill.
4. `potong_penjelasan` (`pasal_extractor.py`): potong bagian Penjelasan sebelum `extract_pasal` (marker setelah pasal terakhir dengan "mulai berlaku"/"diundangkan").

## G. Frontend

- `templates/index.html` + `static/app.js`: halaman pencarian, filter jenis/tahun/status, pagination, tampil prosedur per dokumen.
- Panggilan API ke `/api/documents` dan `/api/documents/tata-cara`.

## H. Keadaan Sekarang (terbukti dari kode)

- Database [DB]: 469 dokumen (386 Perbup, 83 Perda); 47 Perbup punya `konten_text_asli` NULL (PDF scanned).
- Pencarian [KODE]: PostgreSQL tsvector + ts_rank + sinonim (`app/synonyms.py`).
- Pemotongan Penjelasan [KODE]: `potong_penjelasan` di `pasal_extractor.py` dipanggil di `documents.py:195` dan `documents.py:227`.
- Lapis 2 (longgar) [KODE]: tidak ada di working tree saat ini (dihapus).
- Hal yang tidak bisa diverifikasi: performa query pada data penuh (tidak diukur sekarang), status hukum Perbup (semua NULL di DB).


---

# RINGKASAN 02 — DATABASE POSTGRESQL

## A. Koneksi

- Nama database [DB]: `jdih` (konfigurasi di `app/db.py`, kredensial (disembunyikan)).
- Versi [DB]: PostgreSQL 18.6, encoding UTF8, ekstensi terpasang: `plpgsql`.
- Ukuran total tabel [DB]: documents ~83 MB, topics ~48 KB, document_topics ~56 KB.

## B. Tabel `documents`

Fungsi: menyimpan satu dokumen hukum (Perbup/Perda) beserta teks asli, teks bersih, status, dan indeks full-text.

| Kolom | Tipe | NULL | Default | Arti |
|---|---|---|---|---|
| id | integer | tidak | sequence | Primary key |
| judul | text | tidak | — | Judul dokumen |
| nomor | text | ya | — | Nomor peraturan |
| tanggal_terbit | text | ya | — | Tanggal terbit (YYYY-MM-DD) |
| url_pdf | text | ya | — | URL PDF di JDIH |
| konten_text | text | ya | — | Teks bersih (whitespace dinormalisasi) |
| jenis_dokumen | text | ya | — | "Peraturan Bupati" / "Peraturan Daerah" |
| konten_text_asli | text | ya | — | Teks mentah dari PDF |
| status_hukum | text | ya | — | Status (Berlaku/Tidak Berlaku/...) |
| catatan_relasi | text | ya | — | Catatan relasi |
| nomor_tahun | text | ya | — | "nomor_tahun" gabungan |
| konten_tsv | tsvector | ya | — | Indeks full-text (GIN) |

- PK: `id` (btree). Index: `idx_documents_tsv` (GIN pada konten_tsv). Trigger: `trg_documents_tsv` (BEFORE INSERT/UPDATE) → fungsi `documents_tsv_update()` mengisi `konten_tsv` dari judul + konten_text_asli + konten_text dengan `to_tsvector('simple', ...)`.
- Jumlah baris [DB]: 469. Ukuran [DB]: 87.384.064 bytes.
- Diisi oleh [KODE]: `import_real_data.py`, `import_raw_content.py`. Dibaca oleh [KODE]: `app/routers/documents.py`.

## C. Tabel `topics`

Fungsi: daftar topik hukum (label + keyword) untuk pengelompokan dokumen.

| Kolom | Tipe | NULL | Default | Arti |
|---|---|---|---|---|
| id | integer | tidak | sequence | PK |
| label_topik | text | tidak | — | Nama topik (unik) |
| top_keywords | text | ya | — | Keyword topik (koma) |

- PK: `id`. Index unik: `topics_label_topik_key`. Jumlah baris [DB]: 10. Ukuran [DB]: 49.152 bytes.
- Diisi oleh [KODE]: `seed.py` (diduga). Dibaca oleh [KODE]: `app/routers/topics.py`.

## D. Tabel `document_topics`

Fungsi: relasi many-to-many antara dokumen dan topik.

| Kolom | Tipe | NULL | Default | Arti |
|---|---|---|---|---|
| document_id | integer | tidak | — | FK → documents.id |
| topic_id | integer | tidak | — | FK → topics.id |

- PK komposit: (document_id, topic_id). FK: document_id→documents.id, topic_id→topics.id. Jumlah baris [DB]: 353. Ukuran [DB]: 57.344 bytes.
- Diisi oleh [KODE]: `import_perda.py` (diduga). Dibaca oleh [KODE]: `app/routers/documents.py` (`_fetch_document_topics`).

## E. Diagram Relasi (ASCII)

```
documents (id PK)
   1──N  document_topics (document_id FK, topic_id FK)  N──1  topics (id PK)
```

## F. Contoh Nyata

- Dokumen [DB]: id 877, judul "Peraturan Bupati Banyumas Nomor 1 Tahun 2020 Tentang Perubahan Atas Peraturan Bupati Banyumas Nomor 5 Tahun 2019 Tentang Penghasilan Tetap, Tunjangan, Tambahan Penghasilan Dan Penghargaan Kepada Kepala Desa Dan Perangkat Desa Di Kabupaten Banyumas", nomor 1, tanggal_terbit 2020-01-01, jenis "Peraturan Bupati", status_hukum NULL.
- Topik [DB]: id 21, label "Organisasi dan Tata Kerja Perangkat Daerah", top_keywords "organisasi, tata kerja, kedudukan, susunan, unit pelaksana teknis, uptd".
- Relasi [DB]: document_id 877, topic_id 25.

## G. Matriks Fitur × Kolom

| Fitur | Kolom wajib | Jika NULL |
|---|---|---|
| Pencarian teks (tsquery) | konten_tsv (atau konten_text_asli) | dokumen tidak muncul di hasil |
| Filter jenis | jenis_dokumen | tidak terfilter |
| Filter tahun | tanggal_terbit | tidak terfilter |
| Filter status hukum | status_hukum | tidak terhitung di `/api/status-hukum` |
| Filter topik | document_topics | dokumen tidak punya topik |
| Tanya Tata Cara | konten_text_asli + is_procedural pasal | status "tidak_ada_teks" / "tidak_ditemukan" |

## H. Kualitas Data [DB]

- `konten_text` NULL: 0 (empty: 47).
- `konten_text_asli` NULL: 47 (semua PDF scanned, teks tidak bisa diekstrak).
- `status_hukum` NULL: 386 (semua Perbup; 83 Perda punya nilai).
- `catatan_relasi` NULL: 423.
- `tanggal_terbit` NULL: 0.
- Dokumen tanpa topik: 183.
- Per jenis: Peraturan Bupati 386, Peraturan Daerah 83.

## I. Kolom `konten_tsv` [DB]

- Dibuat dari [KODE]: `to_tsvector('simple', coalesce(judul,'') || ' ' || coalesce(konten_text_asli,'') || ' ' || coalesce(konten_text,''))`.
- Konfigurasi bahasa: `simple` (tidak stemming, case-insensitive).
- Diperbarui oleh trigger `trg_documents_tsv` (BEFORE INSERT/UPDATE) dan backfill `WHERE konten_tsv IS NULL`.
- Ukuran rata-rata [DB]: ~57.334 karakter (text representation).


---

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
| 5 | teks | ekstrak pasal | dipakai on-demand di `_cari_pasal_relevan` | `app/pasal_extractor.py` [KODE] | jumlah pasal per dokumen |

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
6. Import topik otomatis: `terapkan_topik_otomatis.py`. Cek: COUNT document_topics = COUNT documents.
7. Jalankan server `uvicorn app.main:app --reload`. Cek: `/api/documents` mengembalikan data.
8. Uji endpoint `/api/documents/tata-cara?q=...`. Titik berhenti: respons ditemukan/tidak_ditemukan sesuai ekspektasi.

## 6. Risiko dan Hal Belum Diuji

- [BELUM DIUJI] Skala: beban pengguna bersamaan, waktu respons pada data penuh.
- [BELUM DIUJI] Kualitas jawaban: akurasi Tanya Tata Cara pada domain nyata.
- Bukti dari data [DB]: 47 dokumen tanpa teks (PDF scanned), 386 Perbup tanpa status_hukum, 0 dokumen tanpa topik (semua 469 terkategori otomatis), cakupan topik hanya 10 topik.
- Risiko [KODE]: `extract_pasal` dipanggil on-demand (tidak ada cache pasal) → beban CPU per request.
- Risiko [KODE]: `potong_penjelasan` memotong berdasarkan penanda; dokumen tanpa penanda dibiarkan apa adanya (22 dokumen pasal terakhir > 5000 chars).
- Risiko [DUGAAN]: sinonim di `synonyms.py` statis, perlu update manual.
