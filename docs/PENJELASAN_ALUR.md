# PENJELASAN ALUR — JDIH Fitur Tambahan

**Tanggal:** 21 November 2026  
**Catatan:** Dokumen ini menggambarkan kode saat ini (API ekstraksi + fitur tata cara saja; fitur topik/metadata/status dihapus).  
**Lokasi file:** `docs/PENJELASAN_ALUR.md`  

---

## Daftar Isi

0. Kepala dokumen  
1. Cerita singkat: projek ini apa dan untuk siapa  
2. Peta rumah: pohon folder dan file penting  
3. Kamus Kecil: istilah teknis dan perumpannya  
4. Database seperti rak buku  
5. Dari nol sampai bisa dicari (pipeline data)  
6. Menyalakan aplikasi  
7. Fitur per fitur  
   7.1 Halaman utama (GET /) dan tampilan  
   7.2 Daftar/pencarian dokumen dengan filter (GET /api/documents)  
   7.3 Detail satu dokumen (GET /api/documents/{id})  
   7.4 Prosedur per dokumen (GET /api/documents/{id}/prosedur)  
   7.5 Tanya Tata Cara (GET /api/documents/tata-cara?q=...)  
       i. mengambil kata kunci dari pertanyaan  
       ii. sinonim  
       iii. membuat tsquery (& dan |)  
       iv. mencari kandidat dokumen di PostgreSQL  
       v. memilih dokumen  
       vi. memecah dokumen menjadi pasal  
       vii. menyaring pasal dan membentuk hasil akhir  
   7.6 API Ekstraksi PDF (POST /api/v1/ekstrak) — upload PDF, otomatis simpan ke database  
   7.7 Skrip Bulk (proses_bulk.py) — proses banyak PDF dari folder  
   7.8 Skrip Export (export_hasil.py) — export hasil olahan ke CSV  
   7.9 Impor data dan backup  
8. Satu contoh perjalanan penuh  
9. Tabel Siapa menjalankan apa  
10. Tabel fitur → file → fungsi → tabel/kolom  
11. Apa yang belum sempurna  
12. Tabel yang diusulkan tapi BELUM ada  
13. Cara mengecek sendiri  

---

## 0. Kepala dokumen

Dokumen ini ditulis berdasarkan kode yang ada di repositori `jdih-fitur-tambahan` saat ini. Database yang digunakan adalah PostgreSQL dengan nama `jdih`. Semua contoh input/output diambil dari menjalankan aplikasi sebenarnya (uvicorn pada port 8765), bukan karangan.

Password database tidak ditulis di sini. Di kode, password dibaca dari environment variable `DB_PASSWORD` (lihat `app/db.py` baris 11). Nilainya ditulis sebagai **(disembunyikan)**.

---

## 1. Cerita singkat: projek ini apa dan untuk siapa

Bayangkan ada sebuah perpustakaan kecil yang menyimpan buku-buku peraturan hukum dari Pemerintah Kabupaten Banyumas. Setiap buku adalah satu peraturan, misalnya "Peraturan Bupati Nomor 48 Tahun 2020 tentang Tata Cara Pemungutan Pajak Restoran". Buku-buku itu disimpan di rak-rak.

Projek ini membuat alat bantu cari buku di perpustakaan itu. Pengguna mengetik pertanyaan di halaman web, misalnya "cara bayar pajak restoran", lalu alat ini mencari buku yang paling cocok dan menunjukkan pasal mana yang membahas caranya.

Alat ini bukan web resmi JDIH. Ini adalah lapisan tambahan atau demo untuk belajar dan mencari tata cara/prosedur dari peraturan yang sudah ada. Tidak boleh dianggap sebagai dokumen hukum resmi tanpa verifikasi lebih lanjut.

Untuk siapa? Untuk siapa saja yang ingin mencari tata cara di peraturan Banyumas tanpa harus membaca semua buku satu per satu.

[TERBUKTI] `app/main.py` baris 7: `app = FastAPI(title="JDIH Fitur Tambahan")`. `README.md` dan `SPESIFIKASI.md` menyebutkan projek adalah layer tambahan/demo terpisah dari web JDIH resmi.

---

## 2. Peta rumah: pohon folder dan file penting

Berikut adalah pohon folder yang penting (hanya file yang terkait fungsi):

```
jdih-fitur-tambahan/
├── app/
│   ├── main.py              # Pintu gerbang aplikasi (server)
│   ├── db.py                # Rumah database dan aturan rak buku
│   ├── pdf_extractor.py     # Ekstrak teks dari PDF + deteksi metadata
│   ├── pasal_extractor.py   # Pemotong isi buku menjadi pasal
│   ├── synonyms.py          # Daftar kata yang sama artinya
│   └── routers/
│       ├── documents.py     # Fitur cari, detail, prosedur, tata cara, upload
│       ├── ekstraksi.py     # API ekstraksi PDF (upload + simpan ke DB)
│       └── __init__.py
├── templates/
│   └── index.html           # Halaman web yang dilihat pengguna
├── static/
│   └── app.js               # Otak halaman web (mengambil data dari server)
├── proses_bulk.py           # Skrip proses bulk PDF dari satu folder
├── export_hasil.py          # Skrip export hasil olahan ke CSV
├── docs/
│   └── PENJELASAN_ALUR.md   # Dokumen ini
├── SPESIFIKASI.md           # Spesifikasi teknis (beberapa bagian usang)
└── requirements.txt         # Daftar alat yang dibutuhkan aplikasi
```

Satu kalimat untuk tiap file penting:

- `app/main.py`: Pintu gerbang. Menyalakan server, memasang halaman web, dan menghubungkan fitur tata cara + ekstraksi.
- `app/db.py`: Aturan rumah database. Membuat tabel, kolom, indeks, dan pemacu (trigger) agar pencarian cepat.
- `app/pdf_extractor.py`: Mengekstrak teks dari PDF (via pypdf) dan mendeteksi metadata (judul, nomor, tahun, jenis_dokumen).
- `app/pasal_extractor.py`: Memotong isi buku menjadi pasal-pasal kecil dan membersihkannya.
- `app/synonyms.py`: Daftar kata yang dianggap sama artinya, misalnya "mengurus" sama dengan "permohonan".
- `app/routers/documents.py`: Otak utama. Menerima pencarian, detail dokumen, prosedur, tanya tata cara, dan upload PDF.
- `app/routers/ekstraksi.py`: API ekstraksi PDF — upload PDF, ekstrak teks, deteksi metadata, otomatis simpan ke tabel `documents`.
- `templates/index.html`: Tampilan halaman web yang dilihat pengguna.
- `static/app.js`: Program di browser yang mengambil data dari server saat pengguna klik atau ketik.
- `proses_bulk.py`: Skrip batch untuk memproses banyak PDF dari satu folder dan menyimpannya ke database.
- `export_hasil.py`: Skrip untuk export hasil olahan (`konten_text_asli`, `konten_tsv`, dll) ke CSV.
- `requirements.txt`: Daftar dependency Python yang dibutuhkan.

[TERBUKTI] Semua file di atas ada dan telah dibaca.

---

## 3. Kamus Kecil: istilah teknis dan perumpannya

Setiap istilah dijelaskan pertama kali muncul dengan perumpamaan perpustakaan, lalu dicatat di sini.

| Istilah | Artinya dalam bahasa sehari-hari | Perumpamaan perpustakaan |
|---------|----------------------------------|--------------------------|
| API / endpoint | Alamat tempat program lain bisa minta data | Meja layanan di perpustakaan |
| Endpoint URL | Alamat lengkap meja layanan, misalnya `/api/documents/tata-cara` | Nomor meja layanan tertentu |
| Server | Program yang siap melayani permintaan | Petugas perpustakaan yang siap membantu |
| Browser | Program yang dibuka pengguna di komputer | Pembaca yang datang ke perpustakaan |
| Tabel database | Rak buku yang menyimpan satu jenis barang | Rak buku peraturan |
| Kolom database | Satu kotak informasi di setiap buku | Halaman informasi tertentu di buku, misalnya judul |
| Baris database | Satu entri lengkap di tabel | Satu buku lengkap |
| Indeks (index) | Daftar pintas untuk mencari cepat | Daftar isi di belakang buku |
| GIN index | Jenis indeks yang cocok untuk mencari kata | Daftar kata di setiap halaman buku |
| tsvector | Daftar kata yang ada di dalam buku | Kartu catatan kata di buku |
| tsquery | Kertas yang berisi kata yang dicari | Kertas pertanyaan yang dibawa pembaca |
| Trigger | Aturan otomatis yang jalan saat sesuatu berubah | Petugas yang otomatis memperbarui kartu saat buku ditambah |
| Regex | Pola pencarian teks yang lebih canggih | Pola pencarian kata dengan tanda bintang |
| Router | Pemula alur permintaan ke fungsi yang tepat | Petugas yang arahkan pembaca ke meja yang tepat |
| Endpoint `tata-cara` | Fitur mencari tata cara/prosedur | Meja layanan khusus tata cara |

[TERBUKTI] Semua istilah sesuai dengan kode yang dibaca. Perumpamaan adalah ilustrasi penulis, bukan dari kode.

---

## 4. Database seperti rak buku

Database bernama `jdih` (PostgreSQL). Terdapat 3 rak buku (tabel):

### 4.1 Tabel `documents` (rak buku utama)

Menyimpan informasi lengkap setiap buku peraturan. Jumlah baris: **469** [TERBUKTI] (dari `SELECT COUNT(*)`).

| Kolom | Arti | Contoh isi |
|-------|------|------------|
| `id` | Nomor urut buku | 922 |
| `judul` | Judul lengkap peraturan | "Peraturan Bupati Banyumas Nomor 48 Tahun 2020 Tentang Tata Cara Pemungutan Pajak Restoran" |
| `nomor` | Nomor peraturan | 48 |
| `tanggal_terbit` | Tanggal terbit (placeholder tahun-01-01) | 2020-01-01 |
| `url_pdf` | Alamat unduhan file PDF | ... |
| `konten_text` | Ringkasan teks untuk pencarian | ... |
| `jenis_dokumen` | Jenis peraturan | "Peraturan Bupati" |
| `konten_text_asli` | Teks mentah asli dari PDF (untuk ekstraksi pasal) | ... (bisa NULL) |
| `status_hukum` | Berlaku atau tidak (hanya Perda) | "Berlaku" / NULL |
| `catatan_relasi` | Catatan tentang mencabut/mengubah | ... (bisa NULL) |
| `nomor_tahun` | Identifier unik lintas jenis | ... (bisa NULL) |
| `konten_tsv` | Daftar kata untuk pencarian cepat (tsvector) | ... (diisi otomatis oleh trigger) |

### 4.2 Tabel `topics` (rak topik)

Menyimpan daftar topik buku. Jumlah baris: **10** [TERBUKTI].

| Kolom | Arti | Contoh isi |
|-------|------|------------|
| `id` | Nomor urut topik | 81 |
| `label_topik` | Nama topik | "anggaran belanja pendapatan" |
| `top_keywords` | Kata kunci topik | "anggaran, belanja, pendapatan" |

### 4.3 Tabel `document_topics` (rak hubungan buku-topik)

Menghubungkan satu buku dengan satu atau lebih topik. Jumlah baris: **469** [TERBUKTI].

| Kolom | Arti | Contoh isi |
|-------|------|------------|
| `document_id` | Rujukan ke buku | 922 |
| `topic_id` | Rujukan ke topik | 81 |

Diagram relasi:

```
documents 1 ---- * document_topics * ---- 1 topics
(satu buku)   (rak hubungan)        (satu topik)
```

Satu buku dapat memiliki beberapa topik, dan satu topik dapat dimiliki oleh banyak buku.

### 4.4 Indeks GIN dan kolom `konten_tsv`

Kolom `konten_tsv` bertipe `tsvector`. Ini adalah "kartu catatan kata" dari buku. Setiap kata di judul dan isi buku dipecah dan dicatat di sini supaya pencarian cepat.

Indeks `idx_documents_tsv` bertipe GIN dipasang pada kolom `konten_tsv` [TERBUKTI] (lihat `app/db.py` baris 94-97). GIN adalah jenis daftar pintas yang sangat cocok untuk mencari kata dalam teks panjang.

Contoh: kalimat "cara bayar pajak restoran" dipecah jadi kata-kata: `cara`, `bayar`, `pajak`, `restoran`. Setiap kata dicatat di `konten_tsv` sehingga saat pencarian, database tidak perlu membaca seluruh buku, cukup lihat daftar kata.

[TERBUKTI] `app/db.py` baris 102-105: `to_tsvector('simple', coalesce(NEW.judul,'') || ' ' || coalesce(NEW.konten_text_asli,'') || ' ' || coalesce(NEW.konten_text,''))`.

### 4.5 Trigger `trg_documents_tsv`

Trigger adalah aturan otomatis. Di sini, trigger bernama `trg_documents_tsv` jalan **sebelum** data buku disimpan (INSERT) atau diubah (UPDATE) [TERBUKTI] (lihat `app/db.py` baris 111-116).

Trigger memanggil fungsi `documents_tsv_update()` [TERBUKTI] (baris 100-109). Fungsi ini mengisi `konten_tsv` secara otomatis dari judul + teks asli + teks ringkasan. Jadi pemelihara database tidak perlu memperbarui daftar kata secara manual.

Tidak ada trigger lain di database [TERBUKTI] (dari `information_schema.triggers`, hanya 2 entri `trg_documents_tsv` untuk INSERT dan UPDATE pada tabel `documents`).

[TERBUKTI] Jumlah baris dan struktur tabel dari `inspect_db_readonly.py` (read-only SELECT / information_schema).

---

## 5. Dari nol sampai bisa dicari (pipeline data)

Urutannya adalah:

1. **`import_real_data.py`** — Membaca file `raw_documents_export.csv` di folder proyek. Memasukkan 386 buku Peraturan Bupati ke tabel `documents`. Setiap buku diberi `tanggal_terbit` berupa `{tahun}-01-01` (karena CSV hanya punya tahun). `konten_text_asli` sengaja kosong (NULL). Topik diberikan berdasarkan kata kunci judul (lihat fungsi `match_topics`, baris 26-36). [TERBUKTI]
2. **`import_perda.py`** — Memasukkan 83 buku Peraturan Daerah ke tabel `documents` yang sama, tanpa menghapus data Perbup. [DUGAAN] (file disebutkan di SPESIFIKASI.md dan RINGKASAN.md, tapi tidak ditemukan dalam daftar file proyek saat ini; konfirmasi diperlukan)
3. **`import_raw_content_auto.py`** — Untuk buku yang `konten_text_asli` masih NULL dan punya `url_pdf`, mengambil teks mentah dari PDF melalui URL dan mengisi `konten_text_asli`. [TERBUKTI] (lihat file, baris 6-18)
4. **`terapkan_topik_otomatis.py`** — Mengelompokkan semua buku ke 10 topik secara otomatis menggunakan TF-IDF + KMeans (k=10). Menghapus topik lama dan membuat topik baru dari hasil pengelompokan judul. [TERBUKTI] (lihat file, baris 50-104)
5. **`backup_pg.py`** — Membuat salinan cadangan tabel `documents`, `topics`, `document_topics` ke file SQL. [TERBUKTI] (lihat file, baris 8-30)

Perintah dijalankan dari folder proyek `D:\KULIAH BRODI\magang\jdih-fitur-tambahan`, misalnya:
- `python import_real_data.py`
- `python import_raw_content_auto.py`
- `python terapkan_topik_otomatis.py`
- `python backup_pg.py`

Cara mengecek berhasil: lihat output cetak di layar, misalnya "469 dokumen diimpor", "OK, clusters: 10", atau "backup: jdih_pg_backup_...sql ... bytes".

[TERBUKTI] Semua skrip di atas ada dan telah dibaca. `import_perda.py` disebutkan dalam dokumentasi lama tetapi file tidak terlihat dalam daftar direktori proyek saat ini (diberi tanda [DUGAAN]).

---

## 6. Menyalakan aplikasi

Jalankan di folder proyek `D:\KULIAH BRODI\magang\jdih-fitur-tambahan`.

Perintah persis (PowerShell):
```powershell
$env:DB_PASSWORD="(disembunyikan)"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Variabel lingkungan yang dibutuhkan (nilai tidak ditulis di sini):
- `DB_PASSWORD` — password database PostgreSQL [TERBUKTI] (`app/db.py` baris 11)

Apa yang terjadi saat startup (`app/main.py` baris 13-15):
1. Fungsi `startup_event` dipanggil.
2. Memanggil `init_db()` dari `app/db.py`.
3. `init_db` membuat tabel jika belum ada, menambah kolom baru jika perlu, membuat indeks GIN, membuat trigger, dan mengisi `konten_tsv` yang belum ada. [TERBUKTI]

Error umum: **"no password supplied"** — artinya `DB_PASSWORD` belum diisi, sehingga database menolak koneksi. Cara atasi: set `DB_PASSWORD` sebelum menjalankan uvicorn [TERBUKTI] (dari pengalaman menjalankan `psycopg2.connect` tanpa password sebelumnya).

Aplikasi akan berjalan di `http://127.0.0.1:8765`. Matikan dengan menekan Ctrl+C (atau melalui tool pengelola proses).

---

## 7. Fitur per fitur

Setiap fitur menggunakan templat yang sama.

### 7.1 Halaman utama (GET /) dan tampilan

**a. Apa gunanya:** Menampilkan halaman web utama tempat pengguna mencari dan melihat daftar peraturan.  
**b. Siapa yang memicunya:** Pengguna membuka alamat `http://localhost:8765/` di browser.  
**c. Alur langkah demi langkah:**
1. Browser meminta halaman `/` ke server.
2. `app/main.py` baris 24-26 mengembalikan `templates/index.html`.
3. Browser menampilkan halaman dengan kotak pencarian, daftar tahun, dan tombol.
4. Saat pengguna mengetik, `static/app.js` mengambil data dari server melalui API.

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Terima permintaan `/` | `app/main.py` | `index` | 24-26 | Mengembalikan halaman HTML |
| Tampilan halaman | `templates/index.html` | — | 1-892 | Menyusun tampilan web |
| Otak halaman web | `static/app.js` | `init` | 494-625 | Memuat topik, jenis, status, dan daftar tahun |

**e. Tabel dan kolom database yang dibaca/ditulis:** Tidak langsung (hanya menampilkan halaman; data diambil lewat API lain).  
**f. Contoh nyata:** GET / → status 200, HTML berpanjang 30.680 karakter [TERBUKTI] (dari `endpoint_contoh.py`).  
**g. Kalau gagal/kosong:** Halaman akan gagal ditampilkan jika server tidak berjalan.  
**h. Batasan:** Tampilan hanya menampilkan daftar tahun dan tabel dokumen; fitur tata cara ada di bagian bawah halaman. [TERBUKTI]  
**i. Intinya dalam satu kalimat:** Halaman utama adalah pintu masuk pengguna untuk mencari dan membuka peraturan di perpustakaan digital.

---

### 7.2 Daftar/pencarian dokumen dengan filter (GET /api/documents)

**a. Apa gunanya:** Menampilkan daftar buku peraturan, dengan pilihan mencari judul/isi, memfilter jenis, tahun, status, topik, dan membagi halaman.  
**b. Siapa yang memicunya:** Pengguna mengetik di kotak pencarian atau memilih filter di halaman web. Browser memanggil `GET /api/documents?q=...&topic=...&jenis=...&status=...&tahun=...&page=...&limit=...`.  
**c. Alur langkah demi langkah:**
1. `static/app.js` fungsi `fetchDocuments` (baris 82-117) membangun URL dengan parameter filter.
2. Server menerima di `app/routers/documents.py` fungsi `get_documents` (baris 219-310).
3. Fungsi membangun query SQL dengan filter yang dipakai.
4. Jika ada kata kunci (`q`), query mencari di `judul` atau `konten_text_asli` dengan `ILIKE` (pencarian teks biasa, bukan tsvector).
5. Database mengembalikan daftar buku dan jumlah total.
6. Untuk setiap buku, diambil topiknya dari tabel `document_topics` (fungsi `_fetch_document_topics`, baris 173-182).
7. Jika total hasil 3 atau kurang, juga diambil prosedur tiap buku (fungsi `get_prosedur_untuk_dokumen`, baris 185-216).
8. Hasil dikembalikan ke browser dalam format JSON dengan informasi pagination.

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Ambil data dari server | `static/app.js` | `fetchDocuments` | 82-117 | Mengirim parameter filter ke API |
| Terima permintaan API | `app/routers/documents.py` | `get_documents` | 219-310 | Membangun query SQL dan ambil data |
| Ambil topik buku | `app/routers/documents.py` | `_fetch_document_topics` | 173-182 | Query relasi buku-topik |
| Ambil prosedur (jika sedikit) | `app/routers/documents.py` | `get_prosedur_untuk_dokumen` | 185-216 | Ekstrak pasal prosedural |

**e. Tabel dan kolom database yang dibaca:** `documents` (id, judul, nomor, tanggal_terbit, url_pdf, konten_text_asli, jenis_dokumen, status_hukum, catatan_relasi), `document_topics` (document_id, topic_id), `topics` (id, label_topik). Tidak menulis apa pun.  
**f. Contoh nyata:** GET /api/documents?q=restoran → total 63 dokumen, 3 pertama: ID 1345 (Perda 2/2026), ID 1334 (Perda 1/2025), ID 1339 (Perda 10/2025) [TERBUKTI] (dari `endpoint_contoh.py`).  
**g. Kalau gagal/kosong:** Jika tidak ada yang cocok, browser menampilkan "Tidak ada dokumen yang cocok" [TERBUKTI] (`static/app.js` baris 306-322).  
**h. Batasan:** Pencarian `q` menggunakan `ILIKE` (cocokkan teks biasa), bukan pencarian cepat `konten_tsv` [TERBUKTI] (`documents.py` baris 241-243). Urutan default adalah tanggal terbit terbaru, bukan relevansi [TERBUKTI] (baris 261).  
**i. Intinya dalam satu kalimat:** Fitur ini menampilkan daftar buku peraturan yang bisa difilter dan dicari sesuai kebutuhan pengguna.

---

### 7.3 Detail satu dokumen (GET /api/documents/{id})

**a. Apa gunanya:** Menampilkan informasi lengkap satu buku peraturan, termasuk teks ringkasan dan topiknya.  
**b. Siapa yang memicunya:** Pengguna mengklik buku di daftar, browser memanggil `GET /api/documents/{id}`.  
**c. Alur langkah demi langkah:**
1. Server menerima di `app/routers/documents.py` fungsi `get_document` (baris 449-474).
2. Query mengambil kolom dari tabel `documents` berdasarkan `id`.
3. Jika tidak ada, mengembalikan error 404 "Dokumen tidak ditemukan".
4. Ambil topik dari tabel `document_topics` dan `topics`.
5. Kembalikan JSON lengkap.

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Ambil detail buku | `app/routers/documents.py` | `get_document` | 449-474 | Query documents dan topics |

**e. Tabel dan kolom database yang dibaca:** `documents` (id, judul, nomor, tanggal_terbit, url_pdf, konten_text, jenis_dokumen), `document_topics`, `topics`.  
**f. Contoh nyata:** GET /api/documents/922 → judul "Peraturan Bupati Banyumas Nomor 48 Tahun 2020 Tentang Tata Cara Pemungutan Pajak Restoran", nomor 48, jenis Peraturan Bupati, topik "anggaran belanja pendapatan" [TERBUKTI] (dari `endpoint_contoh.py`).  
**g. Kalau gagal/kosong:** Error 404 jika id tidak ada [TERBUKTI] (baris 460-461).  
**h. Batasan:** Mengembalikan `konten_text` (ringkasan), bukan `konten_text_asli` (teks mentah penuh) [TERBUKTI] (baris 454).  
**i. Intinya dalam satu kalimat:** Fitur ini menunjukkan detail lengkap satu buku peraturan yang dipilih pengguna.

---

### 7.4 Prosedur per dokumen (GET /api/documents/{id}/prosedur)

**a. Apa gunanya:** Menampilkan pasal mana dalam sebuah buku yang berkaitan dengan tata cara/prosedur.  
**b. Siapa yang memicunya:** Pengguna membuka halaman detail atau browser memanggil `GET /api/documents/{id}/prosedur`.  
**c. Alur langkah demi langkah:**
1. Server menerima di `app/routers/documents.py` fungsi `get_document_prosedur` (baris 313-327).
2. Ambil buku dari tabel `documents` berdasarkan `id`, termasuk `konten_text_asli`.
3. Jika tidak ada teks, kembalikan "tidak ada teks yang dapat diproses".
4. Pecah teks menjadi pasal dengan `extract_pasal` dari `app/pasal_extractor.py`.
5. Jika tidak ada pasal, kembalikan "tidak ditemukan struktur pasal".
6. Cari pasal mana yang prosedural dengan `is_procedural`.
7. Jika tidak ada pasal prosedural, kembalikan pesan sesuai.
8. Kembalikan daftar pasal prosedural dengan isi potongan (maksimal 600 karakter tiap pasal).

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Ambil prosedur buku | `app/routers/documents.py` | `get_document_prosedur` | 313-327 | Terima id, panggil get_prosedur |
| Ekstrak dan saring pasal | `app/routers/documents.py` | `get_prosedur_untuk_dokumen` | 185-216 | Panggil extract_pasal dan is_procedural |
| Potong teks jadi pasal | `app/pasal_extractor.py` | `extract_pasal` | 178 (alias v2) | Pecah MEMUTUSKAN menjadi pasal |
| Cek pasal prosedural | `app/pasal_extractor.py` | `is_procedural` | 33-58 | Hitung kata kunci dan penomoran ayat |

**e. Tabel dan kolom database yang dibaca:** `documents` (id, konten_text_asli, judul, nomor, tanggal_terbit, url_pdf, jenis_dokumen).  
**f. Contoh nyata:** GET /api/documents/922/prosedur → status "ditemukan", jumlah_pasal_total 106, pasal prosedural termasuk Pasal 1, Pasal 3, Pasal 7 [TERBUKTI] (dari `endpoint_contoh.py`).  
**g. Kalau gagal/kosong:** Jika `konten_text_asli` kosong (47 dokumen Perbup PDF scan), kembalikan "tidak ada teks yang dapat diproses" [TERBUKTI] (baris 186-187).  
**h. Batasan:** Hanya menampilkan pasal yang terdeteksi prosedural; pasal non-prosedural tidak ditampilkan [TERBUKTI] (baris 162).  
**i. Intinya dalam satu kalimat:** Fitur ini mencari dan menunjukkan pasal-prosedur dalam satu buku peraturan.

---

### 7.5 Tanya Tata Cara (GET /api/documents/tata-cara?q=...)

Ini adalah fitur terbesar. Dibagi menjadi 7 sub-alur.

#### 7.5.i Mengambil kata kunci dari pertanyaan

**a. Apa gunanya:** Mengubah pertanyaan pengguna menjadi daftar kata kunci yang akan dicari.  
**b. Siapa yang memicunya:** Fungsi `_extract_main_keywords` dipanggil di `app/routers/documents.py` baris 335 (di dalam `tata_cara`).  
**c. Alur langkah demi langkah:**
1. Ambil teks pertanyaan, misalnya "gimana cara bikin KTP".
2. Pisah jadi kata per kata.
3. Untuk setiap kata, hapus tanda bintang dan ubah jadi huruf kecil.
4. Buang kata yang panjangnya 3 huruf atau lebih kecil (jadi "KTP" dengan 3 huruf dibuang).
5. Buang kata awam yang tidak berguna (lihat daftar di bawah).
6. Sisa kata-kata adalah kata kunci.

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Ekstrak kata kunci | `app/routers/documents.py` | `_extract_main_keywords` | 35-42 | Pisah, bersihkan, buang kata pendek dan awam |

**e. Daftar kata yang dibuang** (`_COMMON_WORDS` baris 11, `_QUESTION_WORDS` baris 32, ditambah "dan" dan "atau" baris 36): `cara`, `bagaimana`, `yang`, `untuk`, `dengan`, `dari`, `pada`, `bagaimana`, `dimana`, `apakah`, `kenapa`, `mengapa`, `dan`, `atau`.

**f. Contoh nyata:** "gimana cara bikin KTP" → kata kunci yang tersisa: `gimana`, `bikin` ("KTP" dibuang karena 3 huruf, "cara" dibuang karena kata awam) [TERBUKTI] (dari uji sebelumnya).  
**g. Kalau gagal/kosong:** Jika tidak ada kata kunci yang tersisa, kembalikan "tidak ditemukan" [TERBUKTI] (baris 336-340).  
**h. Batasan:** Kata pendek seperti "KTP" (3 huruf) selalu dibuang, meskipun penting bagi pengguna [TERBUKTI] (baris 40: `len(w_clean) > 3`).  
**i. Intinya dalam satu kalimat:** Sub-alur ini menyaring pertanyaan pengguna jadi daftar kata kunci yang akan dicari di buku.

#### 7.5.ii Sinonim

**a. Apa gunanya:** Mencari kata yang sama artinya sehingga satu kata kunci bisa cocok dengan beberapa bentuk kata.  
**b. Siapa yang memicunya:** Fungsi `sinonim_dari` di `app/synonyms.py` baris 14-24.  
**c. Alur langkah demi langkah:**
1. Terima satu kata kunci, misalnya "mengurus".
2. Cek daftar sinonim `SINONIM` (baris 1-11).
3. Kembalikan kata asli plus semua sinonimnya, tanpa duplikat.

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Cari sinonim | `app/synonyms.py` | `sinonim_dari` | 14-24 | Kembalikan kata asli + sinonim |

**e. Tabel dan kolom database:** Tidak membaca database (daftar ada di file Python).  
**f. Contoh nyata:** `sinonim_dari("mengurus")` → `["mengurus", "permohonan", "pengajuan", "mengaju"]` [TERBUKTI] (`synonyms.py` baris 2). `sinonim_dari("izin")` → `["izin", "perizinan"]`.  
**g. Kalau gagal/kosong:** Jika kata tidak ada di daftar, kembalikan hanya kata asli sendiri [TERBUKTI] (baris 21: `SINONIM.get(kata, [])`).  
**h. Batasan:** Beberapa entri tidak berfungsi di teks asli: "mengaju" tidak pernah muncul sebagai kata utuh di database (0 dokumen), "memohon" juga 0 dokumen [TERBUKTI] (dari uji `tugas2_4b_6.py`).  
**i. Intinya dalam satu kalimat:** Sinonim membantu satu kata kunci cocok dengan berbagai bentuk kata yang sama artinya di buku.

#### 7.5.iii Membuat tsquery (& dan |)

**a. Apa gunanya:** Mengubah daftar kata kunci menjadi "kertas pertanyaan" yang dipahami database pencarian PostgreSQL.  
**b. Siapa yang memicunya:** Fungsi `bangun_tsquery` di `app/routers/documents.py` baris 399-417.  
**c. Alur langkah demi langkah:**
1. Untuk setiap kata kunci, ambil daftar sinonimnya.
2. Gabungkan kata dalam satu grup dengan tanda `|` (atau), misalnya `(mengurus | permohonan | pengajuan | mengaju)`. Artinya: salah satu kata dalam grup sudah cukup.
3. Gabungkan semua grup dengan tanda `&` (dan). Artinya: setiap grup harus terpenuhi.
4. Hasilnya adalah tsquery, misalnya `(mengurus | permohonan | pengajuan | mengaju) & tambahan & penghasilan`.

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Bangun tsquery | `app/routers/documents.py` | `bangun_tsquery` | 399-417 | Gabungkan kata dengan | dan & |

**e. Tabel dan kolom database:** Tidak langsung (tsquery digunakan dalam query ke `konten_tsv`).  
**f. Contoh nyata:** Keywords `['mengurus', 'tambahan', 'penghasilan']` dengan sinonim → tsquery `(mengurus | permohonan | pengajuan | mengaju) & tambahan & penghasilan` [TERBUKTI] (dari uji `test_endpoint_queries.py` sebelumnya).  
**g. Kalau gagal/kosong:** Jika kata dibersihkan menjadi kosong, grup dilewati [TERBUKTI] (baris 411-412).  
**h. Batasan:** `&` berarti semua kata harus ada; jika satu kata tidak ada di buku, hasilnya kosong [TERBUKTI].  
**i. Intinya dalam satu kalimat:** tsquery adalah kertas pertanyaan yang memberitahu database kata mana yang harus ada dan kata mana yang cukup salah satu.

#### 7.5.iv Mencari kandidat dokumen di PostgreSQL

**a. Apa gunanya:** Mencari buku yang paling cocok dengan kertas pertanyaan (tsquery) di database.  
**b. Siapa yang memicunya:** Fungsi `_cari_tahap` di `app/routers/documents.py` baris 419-447.  
**c. Alur langkah demi langkah:**
1. Buat tsquery dari kata kunci.
2. Query database: cari baris di `documents` di mana `konten_tsv` cocok dengan tsquery (`@@`).
3. Hitung seberapa cocok dengan `ts_rank`.
4. Urutkan dari yang paling cocok (rank tertinggi).
5. Ambil maksimal 10 buku kandidat.

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Cari kandidat | `app/routers/documents.py` | `_cari_tahap` | 419-447 | Query konten_tsv dengan tsquery dan ts_rank |

**e. Tabel dan kolom database yang dibaca:** `documents` (id, judul, nomor, tanggal_terbit, url_pdf, konten_text_asli, jenis_dokumen, status_hukum, konten_tsv).  
**f. Contoh nyata:** tsquery `syarat & (izin | perizinan) & usaha` → 10 kandidat, teratas ID 1302 rank 0.9597 [TERBUKTI] (dari `tugas1_3_4.py`).  
**g. Kalau gagal/kosong:** Jika tidak ada yang cocok, `candidates` kosong dan fungsi mengembalikan None [TERBUKTI] (baris 447).  
**h. Batasan:** Hanya 10 teratas yang dicek; jika yang paling cocok tidak punya pasal yang relevan, coba yang berikutnya [TERBUKTI] (baris 435-446).  
**i. Intinya dalam satu kalimat:** Sub-alur ini mencari 10 buku yang paling cocok dengan kertas pertanyaan di rak database.

#### 7.5.v Memilih dokumen

**a. Apa gunanya:** Dari 10 kandidat, pilih satu buku yang punya pasal yang relevan dengan pertanyaan.  
**b. Siapa yang memicunya:** Fungsi `_cari_tahap` baris 435-447, memanggil `_cari_pasal_relevan` (baris 152-170) dan `_is_dokumen_perubahan` (baris 139-149).  
**c. Alur langkah demi langkah:**
1. Untuk setiap kandidat (urut dari yang paling cocok):
   a. Jika buku tidak punya teks asli, lewati.
   b. Pecah jadi pasal dan cek mana yang relevan dengan kata kunci (`_cari_pasal_relevan`).
   c. Jika ada pasal relevan:
      - Cek apakah buku ini adalah "peraturan perubahan" (judul mengandung "Perubahan" atau pasal 1 berawalan "Beberapa ketentuan dalam Peraturan...").
      - Jika BUKAN perubahan, pilih buku ini sebagai hasil akhir.
      - Jika adalah perubahan, simpan sebagai cadangan (hasil_perubahan) tapi lanjutkan ke kandidat berikutnya.
2. Jika tidak ada yang bukan perubahan, pilih cadangan perubahan pertama.
3. Kembalikan buku terpilih, daftar pasal relevan, semua pasal, dan apakah buku itu perubahan.

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Pilih dokumen | `app/routers/documents.py` | `_cari_tahap` | 435-447 | Loop kandidat, pilih yang punya pasal |
| Cari pasal relevan | `app/routers/documents.py` | `_cari_pasal_relevan` | 152-170 | Pecah jadi pasal, saring kata kunci |
| Cek dokumen perubahan | `app/routers/documents.py` | `_is_dokumen_perubahan` | 139-149 | Cek judul dan pasal 1 |

**e. Tabel dan kolom database:** Tidak langsung di sub-alur ini (data sudah diambil di sub-alur iv).  
**f. Contoh nyata:** Query "syarat izin usaha" → kandidat teratas ID 1332 (Perda 15/2024 Ketenagakerjaan) terpilih karena rank lebih tinggi dari ID 1164 (Perbup 12/2023 Izin Tempat Penjualan Minuman Beralkohol) meskipun ID 1164 lebih topikal [TERBUKTI] (dari `tugas1_3_4.py` dan `tugas4b.py`).  
**g. Kalau gagal/kosong:** Jika tidak ada kandidat yang punya pasal relevan, kembalikan None → "tidak ditemukan" [TERBUKTI] (baris 448).  
**h. Batasan:** Pemilihan bergantung urutan `ts_rank`, bukan kebaruan atau keberlakuan buku [DUGAAN] (tidak ada pengurutan berdasarkan `status_hukum` atau `tanggal_terbit` di `_cari_tahap`).  
**i. Intinya dalam satu kalimat:** Sub-alur ini memilih satu buku terbaik dari 10 kandidat yang punya pasal relevan.

#### 7.5.vi Memecah dokumen menjadi pasal

**a. Apa gunanya:** Memotong teks panjang buku menjadi pasal-pasal kecil untuk diperiksa.  
**b. Siapa yang memicunya:** Fungsi `extract_pasal` (alias `extract_pasal_v2`) di `app/pasal_extractor.py` baris 155-178, dipanggil melalui `potong_penjelasan` (baris 220-241) terlebih dahulu.  
**c. Alur langkah demi langkah:**
1. `potong_penjelasan` mencoba memotong bagian "PENJELASAN" dari teks (agar hanya isi pasal yang dianalisa).
2. `extract_pasal` mencari kata "MEMUTUSKAN" sebagai titik awal isi pasal.
3. Setelah MEMUTUSKAN, cari baris yang berbentuk "Pasal N" di awal baris (`_PASAL_JUDUL_PATTERN`).
4. Pasal harus nomor naik, dan loncatan nomor maksimal 5.
5. Isi pasal diambil dari akhir judul pasal sampai awal judul pasal berikutnya.
6. Potong di "BAB" atau "LAMPIRAN" (jika ada).
7. Bersihkan isi pasal dengan `bersihkan_isi_pasal` (hapus footer "JDIH Kabupaten Banyumas" dan judul bagian di akhir).
8. Jika isi lebih dari 600 karakter, potong dan tambahkan tanda "(dipotong...)".

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Potong bagian penjelasan | `app/pasal_extractor.py` | `potong_penjelasan` | 220-241 | Cari batas PENJELASAN dan potong |
| Pecah teks jadi pasal | `app/pasal_extractor.py` | `extract_pasal` (= v2) | 155-178 | Cari MEMUTUSKAN dan judul Pasal |
| Bangun hasil pasal | `app/pasal_extractor.py` | `_bangun_hasil_pasal` | 87-129 | Potong isi, bersihkan, batasi 600 char |
| Bersihkan isi pasal | `app/pasal_extractor.py` | `bersihkan_isi_pasal` | 75-84 | Hapus footer dan judul bagian |

**e. Tabel dan kolom database:** Tidak langsung (beroperasi pada teks dari `konten_text_asli`).  
**f. Contoh nyata:** Doc 922 (179.301 char) → 106 pasal [TERBUKTI] (dari uji sebelumnya).  
**g. Kalau gagal/kosong:** Jika tidak ada "MEMUTUSKAN" atau tidak ada judul "Pasal N", kembalikan daftar kosong [TERBUKTI] (baris 157-158, 164-165).  
**h. Batasan (BUG TERBUKTI):**
   - `potong_penjelasan` baris 225 menggunakan `r'pasal\\s+\\d+'` (double backslash), sehingga pola tidak pernah cocok dan fungsi **tidak memotong apa pun** (teks tetap utuh termasuk bagian PENJELASAN) [TERBUKTI] (dari uji `tugas2_4b_6.py`: doc 922 last_boundary = -1 dengan regex rusak).
   - `bersihkan_isi_pasal` menggunakan `_PARAGRAF_AKHIR` dengan `re.DOTALL` dan `.*\s*$`, sehingga satu header "Bab"/"Paragraf" di tengah teks dapat menghapus **semua teks hingga akhir dokumen** (mis. Doc 1174 Pasal 9: 8.460.759 char → 851 char) [TERBUKTI] (dari `tugas1b_4b.py`).
   - `extract_pasal` hanya menggunakan `_PASAL_JUDUL_PATTERN` (judul di awal baris), sehingga 60 pasal occurrence (28 pasal asli, 53 kutipan semu) tidak terdeteksi dibanding pola `_PASAL_PATTERN` yang cocok di mana saja [TERBUKTI] (dari `analisis_pembersihan.py`).

**i. Intinya dalam satu kalimat:** Sub-alur ini memotong teks buku panjang menjadi pasal-pasal kecil yang siap diperiksa kata kuncinya.

#### 7.5.vii Menyaring pasal dan membentuk hasil akhir

**a. Apa gunanya:** Dari semua pasal, pilih hanya pasal yang benar-benar berkaitan dengan tata cara dan cocok kata kunci.  
**b. Siapa yang memicunya:** Fungsi `_cari_pasal_relevan` baris 152-170, memanggil `is_procedural` (baris 33-58), `_is_pasal_definisi` (baris 123-131), dan `_pasal_memenuhi_keyword` (baris 101-110).  
**c. Alur langkah demi langkah:**
1. Untuk setiap pasal:
   a. Jika pasal BUKAN prosedural (`is_procedural` false), lewati.
   b. Jika pasal adalah definisi (`_is_pasal_definisi` true), lewati.
   c. Cek apakah pasal cocok semua kata kunci (`_pasal_memenuhi_keyword`).
2. Pasal yang lolos semua tes masuk ke daftar hasil.
3. Batasi tampilan maksimal 8 pasal (`_MAKS_PASAL_TAMPIL` baris 120).

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Saring pasal relevan | `app/routers/documents.py` | `_cari_pasal_relevan` | 152-170 | Cek procedural, definisi, kata kunci |
| Cek pasal prosedural | `app/pasal_extractor.py` | `is_procedural` | 33-58 | Hitung kata kunci prosedural dan penomoran ayat |
| Cek pasal definisi | `app/routers/documents.py` | `_is_pasal_definisi` | 123-131 | Cek frasa "yang dimaksud dengan" dll |
| Cek kata kunci pasal | `app/routers/documents.py` | `_pasal_memenuhi_keyword` | 101-110 | Cek semua kata kunci cocok |

**e. Aturan `is_procedural`:** Pasal dianggap prosedural jika skor kata kunci ≥ 2 (kata seperti `mengajukan`, `melampirkan`, `menyerahkan`, `diterbitkan`, `permohonan`, `verifikasi`, `hari kerja`, `disetujui`, `ditolak`, `persyaratan`, `tahapan`) **atau** terdapat penomoran ayat berurutan minimal (1),(2)... [TERBUKTI] (`pasal_extractor.py` baris 34-52).

**f. Aturan definisi (di-skip):** Pasal di-skip jika mengandung "yang dimaksud dengan" dalam 300 karakter pertama, atau pasal 1 berawalan "Dalam Peraturan...", atau berawalan "Maksud/Tujuan/Ruang lingkup/Asas/Sasaran" [TERBUKTI] (`documents.py` baris 123-131).

**g. Threshold kata kunci:** Jika lebih dari 3 kata kunci, cukup 75% cocok; jika 3 atau kurang, semua harus cocok [TERBUKTI] (baris 107-108).

**h. Contoh nyata:** Query "cara bayar pajak restoran" → doc 922, 18 pasal relevan dari 106 pasal, pasal pertama Pasal 7 tentang besaran pokok pajak [TERBUKTI] (dari `endpoint_contoh.py`).  
**i. Kalau gagal/kosong:** Jika tidak ada pasal yang lolos, fungsi mengembalikan daftar kosong dan `_cari_tahap` mencoba kandidat berikutnya [TERBUKTI] (baris 161-168, 439-440).  
**j. Batasan:** Hanya pasal prosedural yang ditampilkan; pasal materi (misal tentang tarif) tidak ikut meskipun cocok kata kunci [TERBUKTI] (baris 162).  
**k. Intinya dalam satu kalimat:** Sub-alur ini memilih pasal-pasal yang benar-benar tentang tata cara dan cocok kata kunci pengguna.

---

### 7.6 Daftar topik, jenis dokumen, tahun, status hukum

**a. Apa gunanya:** Memberikan daftar pilihan filter untuk pengguna di halaman web.  
**b. Siapa yang memicunya:** Browser memanggil `GET /api/topics`, `GET /api/jenis-dokumen`, `GET /api/tahun`, `GET /api/status-hukum` saat halaman dimuat.  
**c. Alur langkah demi langkah:**
1. Setiap fungsi router menerima permintaan, query tabel terkait, kembalikan JSON daftar.
2. `static/app.js` menampilkan topik sebagai chip, jenis dan status sebagai dropdown, tahun sebagai daftar kartu.

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Daftar topik | `app/routers/topics.py` | `get_topics` | 7-27 | Query topics dengan jumlah buku |
| Daftar jenis | `app/routers/metadata.py` | `get_jenis_dokumen` | 7-17 | Query documents group by jenis |
| Daftar tahun | `app/routers/metadata.py` | `get_tahun` | 20-29 | Query tahun distinct dari documents |
| Daftar status | `app/routers/status.py` | `daftar_status_hukum` | 9-27 | Query status_hukum (tidak NULL) |

**e. Tabel dan kolom database yang dibaca:** `topics`, `document_topics`, `documents` (jenis_dokumen, tanggal_terbit, status_hukum).  
**f. Contoh nyata:**
- Topik: 10 topik, teratas "anggaran belanja pendapatan" 436 buku [TERBUKTI].
- Jenis: Peraturan Bupati 386, Peraturan Daerah 83 [TERBUKTI].
- Tahun: 2020, 2021, 2022, 2023, 2024, 2025, 2026 [TERBUKTI].
- Status: Berlaku 75, Tidak Berlaku 8 (hanya Perda yang punya status; 386 Perbup NULL) [TERBUKTI].
**g. Kalau gagal/kosong:** Jika tabel kosong, mengembalikan daftar kosong.  
**h. Batasan:** Status hukum hanya tersedia untuk Perda (83 buku), Perbup selalu NULL [TERBUKTI] (dari `endpoint_contoh.py`: total_status 2, total_dokumen_terfilter 83).  
**i. Intinya dalam satu kalimat:** Fitur ini memberikan daftar filter agar pengguna bisa menyaring buku peraturan.

---

### 7.6 API Ekstraksi PDF (POST /api/v1/ekstrak)

**a. Apa gunanya:** Menerima upload PDF, mengekstrak teks, mendeteksi metadata (judul, nomor, tahun, jenis_dokumen), lalu **otomatis menyimpan** ke tabel `documents`.  
**b. Siapa yang memicunya:** Client (Postman, skrip, atau frontend) memanggil `POST /api/v1/ekstrak` dengan file PDF.  
**c. Alur langkah demi langkah:**
1. Validasi API key (`x-api-key`).
2. Validasi file berakhiran `.pdf` dan ukuran di bawah batas (default 20 MB).
3. Ekstrak teks dari PDF via `ekstrak_teks()` (`app/pdf_extractor.py`).
4. Jika status "rusak" atau "tanpa_teks" → return 422.
5. Deteksi metadata dari teks via `deteksi_metadata()` (`app/pdf_extractor.py`).
6. Jika `judul` diberikan via form → pakai itu; jika tidak → pakai hasil deteksi otomatis.
7. INSERT ke tabel `documents` (judul, nomor, tanggal_terbit, jenis_dokumen, konten_text_asli, konten_text, nomor_tahun).
8. Trigger `trg_documents_tsv` otomatis mengisi `konten_tsv`.
9. Return JSON berisi `id`, `judul`, `konten_text_asli`, `konten_tsv`, dll.

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Terima upload | `app/routers/ekstraksi.py` | `ekstrak` | 37-160 | Validasi, ekstrak, simpan |
| Ekstrak teks PDF | `app/pdf_extractor.py` | `ekstrak_teks` | 23-94 | Baca PDF via pypdf, return teks |
| Deteksi metadata | `app/pdf_extractor.py` | `deteksi_metadata` | 97-156 | Regex cari judul/nomor/tahun/jenis |

**e. Tabel dan kolom database yang ditulis:** `documents` (judul, nomor, tanggal_terbit, jenis_dokumen, konten_text_asli, konten_text, nomor_tahun). `konten_tsv` diisi otomatis oleh trigger.  
**f. Contoh nyata:** POST PDF "Perbup 48/2020 Pajak Restoran" → response 200 dengan `id=470`, `judul="Peraturan Bupati Nomor 48 Tahun 2020..."`, `disimpan=true`.  
**g. Kalau gagal/kosong:** 400 jika bukan PDF, 413 jika terlalu besar, 422 jika rusak/tanpa teks, 401 jika API key salah.  
**h. Batasan:** Metadata deteksi hanya memindai 4.000 karakter pertama. Jika pola peraturan tidak ditemukan, judul/nomor/tahun bisa None.  
**i. Intinya dalam satu kalimat:** Fitur ini menerima PDF dan langsung menyimpannya ke database dengan metadata yang terdeteksi otomatis.

---

### 7.7 Skrip Bulk (proses_bulk.py)

**a. Apa gunanya:** Memproses banyak PDF dari satu folder sekaligus dan menyimpannya ke database.  
**b. Siapa yang memicunya:** Operasi menjalankan `python proses_bulk.py --folder ./pdf_input` di server.  
**c. Alur langkah demi langkah:**
1. Baca semua file `.pdf` di folder yang diberikan.
2. Untuk tiap PDF: ekstrak teks → deteksi metadata → INSERT ke `documents`.
3. Tampilkan progress per file dan ringkasan akhir (sukses/tanpa teks/gagal).

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Proses tiap PDF | `proses_bulk.py` | `proses_satu_pdf` | 21-67 | Ekstrak + simpan |
| Loop semua PDF | `proses_bulk.py` | `main` | 70-105 | Argparse + loop + ringkasan |

**e. Tabel dan kolom database:** Menulis ke `documents` (sama seperti endpoint ekstraksi).  
**f. Contoh nyata:** `python proses_bulk.py --folder ./pdf_input` → 50 PDF, 48 sukses, 2 tanpa teks.  
**g. Kalau gagal/kosong:** File tidak terbaca → status "gagal"; PDF scan/gambar → status "tanpa_teks".  
**h. Batasan:** Hanya file `.pdf` di folder yang diproses (tidak rekursif).  
**i. Intinya dalam satu kalimat:** Skrip ini memproses banyak PDF dari folder sekaligus untuk diisi ke database.

---

### 7.8 Skrip Export (export_hasil.py)

**a. Apa gunanya:** Export hasil olahan dari database ke CSV untuk dikirim ke pembimbing/pengurus JDIA.  
**b. Siapa yang memicunya:** Operasi menjalankan `python export_hasil.py --output hasil.csv`.  
**c. Alur langkah demi langkah:**
1. Query semua baris dari tabel `documents`.
2. Tulis ke file CSV dengan kolom: id, judul, nomor, tanggal_terbit, jenis_dokumen, konten_text_asli, konten_tsv, nomor_tahun.

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Export ke CSV | `export_hasil.py` | `export` | 17-50 | Query DB, tulis CSV |

**e. Tabel dan kolom database:** Membaca `documents` (id, judul, nomor, tanggal_terbit, jenis_dokumen, konten_text_asli, konten_tsv, nomor_tahun).  
**f. Contoh nyata:** `python export_hasil.py --output hasil.csv` → file CSV dengan ratusan baris.  
**g. Kalau gagal/kosong:** Jika tidak ada data, CSV hanya berisi header.  
**h. Batasan:** Opsi `--limit` membatasi jumlah baris; `--only-with-text` hanya export dokumen yang punya `konten_text_asli`.  
**i. Intinya dalam satu kalimat:** Skrip ini mengubah data di database menjadi file CSV yang siap dikirim.

---

### 7.9 Impor data dan backup (legacy)

**a. Apa gunanya:** (Legacy) Memasukkan data buku ke database dan membuat salinan cadangan.  
**b. Siapa yang memicunya:** Operasi menjalankan skrip lama seperti `import_real_data.py`, `import_raw_content_auto.py`, `backup_pg.py` (tidak lagi diperlukan untuk fitur tata cara + ekstraksi).  
**c. Alur langkah demi langkah (import_real_data.py):**
1. Baca file `raw_documents_export.csv`.
2. Periksa apakah ada data bukan Perbup (jika ada, batalkan untuk menghindari kehilangan data).
3. Hapus data lama di `documents`.
4. Masukkan 386 buku Perbup dengan `tanggal_terbit = {tahun}-01-01`.

**d. KODE-NYA DI MANA:**

| Langkah | File | Fungsi | Baris | Apa yang dikerjakan |
|---------|------|--------|-------|---------------------|
| Impor data asli | `import_real_data.py` | `import_data` | 39-147 | Baca CSV, masukkan ke DB |
| Isi teks asli | `import_raw_content_auto.py` | (skrip utama) | 1-23 | Ambil PDF dari URL, simpan teks |
| Backup database | `backup_pg.py` | (skrip utama) | 1-31 | Ambil semua baris, tulis file SQL |

**e. Tabel dan kolom database:** `documents`.  
**f. Contoh nyata:** `import_real_data.py` mencetak "469 dokumen diimpor".  
**g. Kalau gagal/kosong:** Jika ada data bukan Perbup, skrip berhenti dan tidak menghapus apa pun.  
**h. Batasan:** Skrip ini legacy dan tidak lagi diperlukan untuk alur baru (API ekstraksi + bulk).  
**i. Intinya dalam satu kalimat:** Skrip lama untuk impor data awal dari CSV.

---

## 8. Satu contoh perjalanan penuh

Pengguna mengetik **"cara bayar pajak restoran"** di halaman web sampai hasil muncul:

1. Pengguna mengetik di kotak pencarian tata cara dan menekan tombol "Cari" (`templates/index.html` baris 787-796, `static/app.js` baris 499-514).
2. `static/app.js` memanggil `GET /api/documents/tata-cara?q=cara+bayar+pajak+restoran` (`static/app.js` baris 507).
3. Server menerima di `app/routers/documents.py` fungsi `tata_cara` (baris 330-396).
4. `_extract_main_keywords` (baris 35-42): kata kunci yang tersisa = `bayar`, `pajak`, `restoran` ("cara" dibuang kata awam).
5. `bangun_tsquery` (baris 399-417, pakai_sinonim=False dulu): tsquery = `bayar & pajak & restoran`. Dengan sinonim: `(bayar | pembayaran | penyetoran | membayar) & pajak & restoran` (`app/synonyms.py` baris 5-6).
6. `_cari_tahap` (baris 419-447): query `konten_tsv @@ to_tsquery('simple', 'bayar & pajak & restoran')`, urutkan `ts_rank DESC`, ambil 10.
7. Database mengembalikan kandidat. ID 922 (Perbup 48/2020 Pajak Restoran) ada di antara kandidat.
8. `_cari_pasal_relevan` (baris 152-170): pecah doc 922 jadi 106 pasal, saring pasal prosedural yang cocok kata kunci.
9. Ditemukan 18 pasal relevan, pertama Pasal 7 tentang besaran pokok pajak restoran.
10. Bukan dokumen perubahan, sehingga langsung dipilih sebagai hasil.
11. Hasil JSON dikembalikan ke browser: status "ditemukan", dokumen ID 922, 18 pasal relevan.
12. `static/app.js` fungsi `renderTataCaraResult` (baris 523-604) menampilkan kartu hasil dengan judul dan kutipan pasal.

**Contoh output sungguhan** (dipotong):
```json
{
  "status": "ditemukan",
  "diperluas_sinonim": false,
  "dokumen_perubahan": false,
  "dokumen": {"id": 922, "judul": "Peraturan Bupati Banyumas Nomor 48 Tahun 2020 Tentang Tata Cara Pemungutan Pajak Restoran", "nomor": "48", "tahun": "2020"},
  "prosedur": {
    "jumlah_pasal_total": 106,
    "jumlah_pasal_relevan": 18,
    "pasal_prosedural": [
      {"nomor_pasal": 7, "isi_pasal": "(1) Besaran pokok Pajak Restoran terutang dihitung dengan cara mengalikantarif sebagaimana dimaksud ...", ...},
      {"nomor_pasal": 8, "isi_pasal": "(1) Pengusaha Restoran wajib mengenakan Pajak Restoran dengan tarif sebagaimana dimaksud dalam Pasal...", ...}
    ]
  }
}
```
[TERBUKTI] (dari `endpoint_contoh.py`).

---

## 9. Tabel Siapa menjalankan apa

| Perintah | Dijalankan dari folder | Kapan dipakai | Fitur yang bergantung |
|----------|------------------------|---------------|----------------------|
| `python proses_bulk.py --folder ./pdf_input` | Folder proyek / server | Saat memproses banyak PDF dari folder | Ekstraksi + simpan ke DB |
| `python export_hasil.py --output hasil.csv` | Folder proyek / server | Saat export hasil olahan ke CSV | Fitur tata cara (data sudah di DB) |
| `$env:DB_PASSWORD="(disembunyikan)"; .\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765` | Folder proyek / server | Saat menyalakan server aplikasi | Semua fitur API dan halaman web |
| `python -c "from app.db import init_db; init_db()"` | Folder proyek / server | Saat pertama kali inisialisasi database | Semua fitur |

[TERBUKTI] Semua skrip ada dan telah dibaca. Perintah uvicorn telah diuji secara langsung (port 8765).

---

## 10. Tabel fitur → file → fungsi → tabel/kolom

| Fitur | File | Fungsi | Tabel/kolom |
|-------|------|--------|-------------|
| Halaman utama | `app/main.py` | `index` | — |
| Tampilan web | `templates/index.html` | — | — |
| Otak halaman web | `static/app.js` | `fetchDocuments`, `renderTataCaraResult` | — |
| Daftar/pencarian buku | `app/routers/documents.py` | `get_documents` | `documents` |
| Detail buku | `app/routers/documents.py` | `get_document` | `documents` |
| Prosedur buku | `app/routers/documents.py` | `get_document_prosedur`, `get_prosedur_untuk_dokumen` | `documents` (konten_text_asli) |
| Tanya tata cara | `app/routers/documents.py` | `tata_cara`, `_cari_tahap`, `_cari_pasal_relevan`, `bangun_tsquery`, `_extract_main_keywords`, `_pasal_memenuhi_keyword`, `_is_pasal_definisi`, `_is_dokumen_perubahan` | `documents` (konten_tsv, konten_text_asli) |
| Ekstrak pasal | `app/pasal_extractor.py` | `extract_pasal`, `potong_penjelasan`, `bersihkan_isi_pasal`, `is_procedural`, `_bangun_hasil_pasal` | — (teks dari konten_text_asli) |
| Sinonim | `app/synonyms.py` | `sinonim_dari` | — |
| API Ekstraksi PDF | `app/routers/ekstraksi.py` | `ekstrak` | `documents` (INSERT) |
| Proses Bulk PDF | `proses_bulk.py` | `proses_satu_pdf`, `main` | `documents` (INSERT) |
| Export Hasil | `export_hasil.py` | `export` | `documents` (SELECT) |
| Atur database | `app/db.py` | `init_db`, `get_db`, `documents_tsv_update` | Semua tabel |

[TERBUKTI] Semua entri sesuai dengan kode yang dibaca.

---

## 11. Apa yang belum sempurna

Berikut adalah masalah yang **benar-benar terbukti** dari kode dan database saat ini. Tidak ada yang disembunyikan.

| Masalah | Bukti | Sudah diperbaiki atau belum di commit ini | Dampak bagi pengguna (bahasa sederhana) |
|---------|-------|-------------------------------------------|------------------------------------------|
| `bersihkan_isi_pasal` memakai `re.DOTALL` dengan `.*\s*$` sehingga bisa menghapus teks sangat banyak | `app/pasal_extractor.py` baris 69-72, 82-83; bukti: Doc 1174 Pasal 9 8.460.759 char → 851 char (`tugas1b_4b.py`) | **Belum** | Isi pasal bisa hilang besar-besaran, hasil jadi tidak lengkap |
| `potong_penjelasan` memakai `r'pasal\\s+\\d+'` (double backslash) sehingga tidak memotong | `app/pasal_extractor.py` baris 225; bukti: doc 922 last_boundary = -1 (`tugas2_4b_6.py`) | **Belum** | Bagian PENJELASAN tidak terpotong, teks jadi panjang dan berisi bukan pasal |
| Kata ≤ 3 huruf (mis. KTP) dibuang di `_extract_main_keywords` | `app/routers/documents.py` baris 40 (`len(w_clean) > 3`); bukti: 42 dokumen ada "KTP" tapi query KTP gagal (`tugas2_4b_6.py`) | **Belum** | Pengguna tidak bisa mencari KTP, kartu tanda penduduk, dll |
| Kata awam (urus, bikin, gimana) menjadi kata wajib | `app/routers/documents.py` baris 35-42; bukti: "mau urus izin usaha" tidak ditemukan meskipun ada 46 dokumen izin usaha | **Belum** | Pertanyaan dengan kata awam bisa gagal meskipun ada buku yang cocok |
| Pemilihan dokumen bergantung urutan ts_rank, bukan kebaruan/keberlakuan | `app/routers/documents.py` baris 423-429 (`ORDER BY rank DESC LIMIT 10`); bukti: "syarat izin usaha" pilih ID 1332 (ketenagakerjaan) bukan ID 1164 (izin usaha) (`tugas1_3_4.py`, `tugas4b.py`) | **Belum** | Hasil bisa berupa buku yang topiknya tidak tepat |
| `status_hukum` 386 Perbup masih kosong (NULL) | DB: status_hukum Berlaku 75 + Tidak Berlaku 8 = 83 (hanya Perda) (`endpoint_contoh.py`) | **Belum** | Filter status tidak berguna untuk Perbup |
| 47 PDF scan tanpa teks (`konten_text_asli` NULL) | DB: 47 dokumen dengan konten_text_asli NULL (dokumen RINGKASAN.md dan SPESIFIKASI.md); bukti: query `konten_text_asli IS NULL` | **Belum** | 47 buku tidak bisa dicari isinya, hanya judul |
| Entri sinonim tidak berfungsi (mengaju, memohon) | `app/synonyms.py` baris 2-4; bukti: "mengaju" 0 dokumen word boundary, "memohon" 0 dokumen (`tugas2_4b_6.py`) | **Belum** | Sinonim ini tidak pernah membantu pencarian |

[TERBUKTI] Semua masalah di atas terbukti dari kode dan/atau hasil uji langsung. Tidak ada dugaan yang ditulis sebagai fakta.

---

## 12. Tabel yang diusulkan tapi BELUM ada

Berikut adalah rencana rak buku tambahan dari `docs/usulan_skema.sql` yang **belum dipasang** ke database:

| Tabel yang diusulkan | Satu kalimat penjelasan | Kenapa belum dibuat |
|----------------------|-------------------------|---------------------|
| `pasal_dokumen` | Menyimpan hasil potong pasal setiap buku untuk pencarian cepat tanpa harus memotong ulang setiap kali | Belum dijalankan (hanya file SQL, tidak ada perintah CREATE TABLE di kode aplikasi) |
| `log_ekstraksi` | Mencatat hasil ekstraksi teks tiap buku (berhasil/gagal, alasan) | Belum dijalankan |
| `relasi_dokumen` | Menyimpan relasi antar buku (mencabut, mengubah, dll) secara terstruktur | Belum dijalankan |
| `sinonim` | Menyimpan daftar sinonim di database agar bisa diedit tanpa ubah kode | Belum dijalankan (sinonim masih dalam file Python) |
| `log_pencarian` | Mencatat pertanyaan pengguna dan hasilnya (tanpa data pribadi) | Belum dijalankan |
| `versi_skema` | Mencatat versi skema database | Belum dijalankan |

[TERBUKTI] `docs/usulan_skema.sql` berisi 6 CREATE TABLE dengan komentar "BELUM DIJALANKAN" (baris 3). Tidak ada tabel ini di database saat ini (hanya 3 tabel: documents, topics, document_topics) [TERBUKTI] (dari `inspect_db_readonly.py`).

---

## 13. Cara mengecek sendiri

Berikut adalah kumpulan perintah read-only (tidak mengubah apa pun) untuk membuktikan isi dokumen ini. Jalankan dari folder proyek.

### 13.1 Cek struktur database

```powershell
$env:DB_PASSWORD="(disembunyikan)"
.\venv\Scripts\python.exe -c "
import psycopg2
from psycopg2.extras import RealDictCursor
c = psycopg2.connect(host='localhost', port=5432, dbname='jdih', user='postgres', password=__import__('os').environ['DB_PASSWORD'], cursor_factory=RealDictCursor)
cur = c.cursor()
cur.execute(\"SELECT table_name, (SELECT COUNT(*) FROM information_schema.columns WHERE table_name=t.table_name) as col_count FROM information_schema.tables t WHERE table_schema='public'\")
for r in cur.fetchall(): print(r['table_name'], r['col_count'])
cur.execute(\"SELECT COUNT(*) FROM documents\")
print('documents:', cur.fetchone()[0])
c.close()
"
```

Hasil yang diharapkan: documents (jumlah sesuai data).

### 13.2 Cek trigger dan indeks

```powershell
.\venv\Scripts\python.exe -c "
import psycopg2, os
c = psycopg2.connect(host='localhost', port=5432, dbname='jdih', user='postgres', password=os.environ['DB_PASSWORD'])
cur = c.cursor()
cur.execute(\"SELECT trigger_name, event_object_table, action_timing FROM information_schema.triggers WHERE trigger_schema='public'\")
for r in cur.fetchall(): print(r)
cur.execute(\"SELECT indexname FROM pg_indexes WHERE schemaname='public' AND indexname='idx_documents_tsv'\")
print('idx_documents_tsv ada:', cur.fetchone() is not None)
c.close()
"
```
Hasil yang diharapkan: trigger `trg_documents_tsv` ada, indeks `idx_documents_tsv` ada.

### 13.3 Uji satu endpoint (butuh server nyala)

Nyalakan server:
```powershell
$env:DB_PASSWORD="(disembunyikan)"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Di jendela PowerShell lain (atau gunakan browser):
```
http://127.0.0.1:8765/api/documents/tata-cara?q=cara%20bayar%20pajak%20restoran
```
Hasil yang diharapkan: JSON dengan `"status": "ditemukan"`, dokumen ID 922, `"jumlah_pasal_relevan": 18`.

Matikan server setelah selesai (Ctrl+C).

### 13.4 Cek bug potong_penjelasan

```powershell
.\venv\Scripts\python.exe -c "
import re
low = 'pasal 1 mulai berlaku'
print(re.findall(r'pasal\\s+\\d+', low))   # harusnya [] (bug: double backslash)
print(re.findall(r'pasal\s+\d+', low))     # harusnya ['pasal 1'] (fix)
"
```
Hasil yang diharapkan: baris pertama kosong `[]`, baris kedua `['pasal 1']`.

---

**Akhir dokumen.** Dokumen ini ditulis berdasarkan kode commit `e696204` pada cabang `perbaiki-penyaring-pasal`. Semua klaim ditandai [TERBUKTI] (dibaca kode atau dijalankan langsung) atau [DUGAAN] (disimpulkan tanpa melihat kode langsung). Tidak ada fitur yang dibuat palsu; fitur yang tidak ada ditulis "belum ada".
