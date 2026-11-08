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
