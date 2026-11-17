# SCRIPT PRESENTASI SISTEM PENCARIAN TATA CARA JDIH
## Untuk Dosen Penguji

---

## 1. PENGENALAN SISTEM

Sistem ini adalah fitur tambahan JDIH (Jaringan Dokumentasi Informasi Hukum) Kabupaten Banyumas yang berfokus pada **pencarian tata cara dan prosedur administrasi** dalam peraturan daerah.

Tujuan utamanya: masyarakat atau pegawai dapat mencari "bagaimana cara mengurus izin usaha", "tata cara pendaftaran sekolah", dst., lalu sistem menampilkan pasal-prosedur yang relevan langsung dari dokumen peraturan asli, bukan ringkasan buatan AI.

---

## 2. ARSITEKTUR SISTEM

```
+---------------------+      +---------------------+      +---------------------+
|   Frontend (HTML/   |      |   Backend (FastAPI) |      |   Database (PostgreSQL)|
|   JavaScript)       |<---->|   (app/routers/)    |<---->|   (app/db.py)        |
+---------------------+      +---------------------+      +---------------------+
        |                           |                           |
        |  GET /                    |                           |
        |  GET /upload              |                           |
        |  GET /api/documents       |                           |
        |  GET /api/documents/tata-cara |                       |
        |  POST /api/documents/upload |                         |
        |  PUT /api/documents/{id}  |                           |
        |  DELETE /api/documents/{id}|                          |
        +---------------------------+---------------------------+
```

---

## 3. STRUKTUR DATABASE (PostgreSQL)

Tabel utama: `documents`

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| id | SERIAL PK | ID unik dokumen |
| judul | TEXT | Judul peraturan |
| nomor | TEXT | Nomor peraturan (contoh: 5/2025) |
| tanggal_terbit | TEXT | Tanggal terbit |
| url_pdf | TEXT | Path/URL file PDF |
| jenis_dokumen | TEXT | Peraturan Bupati / Peraturan Daerah |
| status_hukum | TEXT | Berlaku / Tidak Berlaku |
| catatan_relasi | TEXT | Pencabutan/perubahan |
| konten_text | TEXT | Teks sudah dibersihkan (untuk tampilan) |
| konten_text_asli | TEXT | Teks mentah asli dari PDF (untuk ekstraksi pasal) |
| konten_tsv | tsvector | Indeks full-text search (di-generate otomatis via trigger) |

Tabel pendukung: `topics` dan `document_topics` untuk kategorisasi topik otomatis.

---

## 4. ALUR PENCARIAN FULL-TEXT (FTS)

Sistem menggunakan full-text search bawaan PostgreSQL (tsvector + tsquery), menggantikan FTS5 dari SQLite lama.

**Langkah-langkah:**
1. Pengguna mengetik kata kunci di search box (contoh: "daftar sekolah dasar")
2. Backend mengekstrak kata kunci utama, membuang stop words (cara, bagaimana, yang, dst.)
3. Dibangun tsquery: `daftar & sekolah & dasar`
4. Query SQL: `WHERE konten_tsv @@ to_tsquery('simple', 'daftar & sekolah & dasar')`
5. PostgreSQL mencari via **GIN index** pada kolom `konten_tsv` — sangat cepat, tidak perlu sequential scan seluruh teks
6. Hasil diurutkan berdasarkan `ts_rank` (skor relevansi: frekuensi kata, kedekatan kata, panjang dokumen)
7. Untuk dokumen terbaik, sistem membaca `konten_text_asli` lalu mengekstrak pasal-prosedur yang relevan

**Trigger otomatis:** Setiap kali data di-insert atau di-update, trigger `trg_documents_tsv` otomatis mengisi `konten_tsv` dari gabungan `judul + konten_text_asli + konten_text`.

---

## 5. ALUR PENCARIAN TATA CARA / PROSEDUR

Endpoint: `GET /api/documents/tata-cara?q=...`

1. Ekstrak keyword dari pertanyaan pengguna
2. Coba pencarian tanpa sinonim dulu
3. Kalau tidak ada hasil, coba lagi dengan sinonim (contoh: "mengurus" → ["permohonan", "pengajuan", "mengurus", "mengaju"])
4. Untuk setiap dokumen kandidat:
   - Baca `konten_text_asli`
   - `extract_pasal()` — potong teks menjadi pasal-pasal
   - `potong_penjelasan()` — hapus penjelasan umum, ambil isi inti pasal
   - Filter hanya pasal yang teridentifikasi sebagai **prosedural** (tata cara)
   - Hapus pasal definisi ("yang dimaksud dengan...", "Maksud dan Tujuan", dll.)
   - Cek apakah pasal mengandung semua kata kunci
5. Kembalikan dokumen terbaik beserta pasal-prosedur yang relevan (maksimal 8 pasal ditampilkan)

Jika dokumen terbaik adalah **peraturan perubahan**, sistem memberi tahu bahwa itu adalah dokumen perubahan, bukan tata cara langsung.

---

## 6. FITUR CRUD UNTUK PEGAWAI (Non-IT)

Karena target pengguna adalah pegawai negeri yang bukan ahli IT, sistem menyediakan antarmuka web sederhana:

### Tambah Data (`POST /api/documents/upload`)
- Pegawai mengisi form: Judul, Nomor, Tanggal Terbit, Jenis Dokumen, Status Hukum, Catatan Relasi
- Upload file PDF
- Sistem otomatis mengekstrak teks dari PDF (menggunakan library `pypdf`)
- Teks mentah disimpan ke `konten_text_asli`, versi bersih ke `konten_text`
- Trigger otomatis isi `konten_tsv`

### Edit Data (`PUT /api/documents/{id}`)
- Pegawai dapat mengubah metadata (judul, nomor, tanggal, jenis, status, catatan)
- Dapat juga mengganti file PDF (teks akan diekstrak ulang)
- File PDF lama dihapus dari storage untuk menghemat ruang

### Hapus Data (`DELETE /api/documents/{id}`)
- Konfirmasi sebelum dihapus
- Data dan file PDF terhapus permanen

---

## 7. DEMO LANGKAH DEMI LANKAH

### Demo 1: Pencarian Dokumen
1. Buka halaman utama
2. Ketik kata kunci di search box (contoh: "izin usaha")
3. Sistem menampilkan daftar dokumen yang cocok, diurutkan relevansi
4. Klik tombol Download untuk membuka PDF asli

### Demo 2: Pencarian Tata Cara
1. Di section "Pencarian Tata Cara & Prosedur", ketik pertanyaan (contoh: "bagaimana cara daftar sekolah dasar")
2. Sistem mencari dokumen yang mengandung prosedur terkait
3. Menampilkan pasal-prosedur yang relevan dengan kutipan langsung dari dokumen asli
4. Terdapat peringatan: "Kutipan langsung dari dokumen asli, bukan ringkasan AI"

### Demo 3: Upload Dokumen Baru
1. Klik menu Upload (atau buka `/upload`)
2. Isi form metadata dan pilih file PDF
3. Klik Simpan Peraturan
4. Dokumen baru langsung muncul di daftar pencarian

### Demo 4: Edit dan Hapus
1. Di tabel dokumen, klik tombol Edit (ikon pensil)
2. Ubah data, klik Simpan Perubahan
3. Klik tombol Hapus (ikon tong sampah), konfirmasi
4. Dokumen hilang dari daftar

---

## 8. KELEBIHAN SISTEM

- **Non-IT friendly:** Pegawai tidak perlu mengetik SQL atau copas teks manual, cukup upload PDF
- **Cepat:** Full-text search dengan GIN index, tidak perlu scan seluruh database
- **Akurasi:** Ekstraksi pasal tingkat dokumen, bukan hanya pencarian kata kunci permukaan
- **Transparan:** Setiap hasil dilengkapi kutipan langsung dari dokumen asli
- **Otomatis:** Indeks pencarian ter-update otomatis saat data ditambahkan/diubah

---

## 9. BATASAN (Untuk Dikembangkan Selanjutnya)

- PDF scan (gambar) tidak dapat diekstrak teksnya, butuh OCR
- Ekstraksi teks PDF bergantung pada kualitas formatting PDF asli
- Hanya mendukung format PDF untuk saat ini

---

## 10. PENUTUP

Sistem ini siap digunakan sebagai prototipe untuk pencarian tata cara administrasi di JDIH Kabupaten Banyumas. Pegawai dapat mengelola data peraturan melalui antarmuka web sederhana tanpa perlu keterampilan IT, sementara masyarakat dapat mencari prosedur administrasi dengan cepat dan akurat berdasarkan isi dokumen asli.

Terima kasih.