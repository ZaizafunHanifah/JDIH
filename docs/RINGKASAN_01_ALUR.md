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
