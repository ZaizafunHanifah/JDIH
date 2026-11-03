# Spesifikasi Project JDIH Fitur Tambahan

Dokumen ini menjelaskan konsep, arsitektur, data, API, antarmuka, keterbatasan, dan cara menjalankan project **JDIH Fitur Tambahan**. Dokumen dimaksudkan sebagai bahan belajar serta bahan presentasi kepada pembimbing atau pengelola JDIH.

## 1. Ringkasan Project

### 1.1 Masalah yang Diselesaikan

Pengguna JDIH sering perlu menemukan produk hukum dari kumpulan dokumen yang terus bertambah, tetapi pencarian berdasarkan tahun, jenis dokumen, dan topik dapat menjadi kurang nyaman jika hanya mengandalkan daftar statis. Project ini menyediakan lapisan pencarian dan penelusuran yang lebih terarah tanpa mengubah sistem JDIH resmi.

### 1.2 Yang Dibangun

Project ini membangun demo aplikasi pencarian produk hukum dengan fitur utama berikut:

- **Full-text search** untuk mencari kata atau frasa pada judul dan isi ringkas dokumen.
- **Filter topik** melalui chip topik yang dapat diaktifkan atau dinonaktifkan.
- **Filter jenis dokumen** seperti Peraturan Bupati, Surat Keputusan, Peraturan Daerah, Surat Edaran, dan Peraturan Desa.
- **Filter tahun** melalui grid tahun pada tampilan awal.
- **Urutan dokumen terbaru sebagai default**, sehingga dokumen dengan tanggal terbit paling baru ditampilkan lebih dahulu.
- Pagination, tautan PDF, breadcrumb, dan tampilan responsif untuk membantu penelusuran dokumen.

### 1.3 Posisi Project

Project ini merupakan **layer tambahan atau demo yang terpisah dari web JDIH resmi**. Aplikasi tidak membaca atau menulis data JDIH produksi. Database saat ini berisi **407 dokumen** yang terdiri dari **327 Peraturan Bupati** dan **80 Peraturan Daerah** Kabupaten Banyumas asli, diimpor dari hasil pengumpulan data skripsi penulis (bukan hasil karangan/generate). Di antaranya terdapat **9.229 pasal** dan **5.162 prosedural (55,9%)**, dengan rincian per jenis (Perbup 327 / 6.455 / 3.337, Perda 80 / 2.774 / 1.825). Karena itu, tautan PDF dan isi dokumen dalam demo mencerminkan data nyata namun tidak boleh dianggap sebagai dokumen hukum resmi tanpa verifikasi lebih lanjut.

## 2. Tech Stack

| Komponen | Teknologi | Alasan pemilihan |
|---|---|---|
| Bahasa backend | Python | Mudah dibaca, cocok untuk prototipe, dan memiliki dukungan SQLite bawaan. |
| Framework API | FastAPI | Ringan, cepat dibuat, menyediakan validasi parameter query, dan menghasilkan dokumentasi API otomatis. |
| Server aplikasi | Uvicorn | ASGI server yang sesuai untuk menjalankan aplikasi FastAPI selama development. |
| Database | SQLite | Tidak memerlukan server database terpisah, mudah disalin, dan sudah cukup untuk data demo berukuran kecil hingga menengah. |
| Full-text search | SQLite FTS5 | Menyediakan indeks teks dan operator `MATCH` tanpa menambahkan layanan pencarian eksternal. |
| Template | Jinja2 | Digunakan FastAPI untuk menyajikan halaman `index.html` tanpa framework frontend tambahan. |
| Frontend | HTML, CSS, vanilla JavaScript | Interaksi yang dibutuhkan masih terbatas pada fetch, filter, render tabel, dan pagination, sehingga tidak memerlukan build system atau framework besar. |

### 2.1 Mengapa Tidak Menggunakan Database Server Terpisah

SQLite dipilih karena project ini berfokus pada prototipe dan pembelajaran. Dengan SQLite, database berupa satu file (`jdih.db`), tidak perlu menginstal PostgreSQL/MySQL, membuat akun database, mengatur jaringan, atau menjalankan service tambahan. FTS5 juga sudah tersedia dalam SQLite yang digunakan project ini.

Trade-off-nya adalah SQLite tidak dirancang sebagai database terpusat dengan banyak penulis bersamaan seperti database server. Jika nanti data bertambah sangat besar, trafik meningkat, atau diperlukan banyak proses yang menulis secara bersamaan, migrasi ke PostgreSQL atau mesin pencarian khusus dapat dipertimbangkan.

### 2.2 Mengapa Tidak Menggunakan Framework Frontend Besar

Frontend saat ini hanya membutuhkan pengambilan data dari API, pengelolaan beberapa state filter, render grid/tabel, dan pagination. Vanilla JavaScript menjaga project tetap sederhana, mudah dipelajari, dan dapat dijalankan tanpa proses build seperti Webpack atau Vite.

Jika antarmuka berkembang menjadi aplikasi yang sangat interaktif dengan routing kompleks, form administrasi, state global besar, atau banyak komponen yang digunakan ulang, framework seperti React atau Vue dapat menjadi pilihan. Untuk skala demo ini, tambahan kompleksitas tersebut belum diperlukan.

## 3. Arsitektur & Alur Data

### 3.1 Diagram Alur

```text
+----------------------+
|      Browser         |
|  index.html + app.js |
+----------+-----------+
           |
           | HTTP GET /api/...
           v
+----------------------+
|      FastAPI         |
| app/main.py + router |
+----------+-----------+
           |
           | query SQL / FTS MATCH
           v
+----------------------+
|      SQLite          |
| jdih.db              |
| documents            |
| topics               |
| document_topics      |
| documents_fts        |
+----------------------+
```

Alur umum pengguna adalah sebagai berikut:

1. Browser membuka halaman utama melalui FastAPI.
2. `index.html` memuat `static/app.js` dan menampilkan panel pencarian serta filter.
3. JavaScript memanggil endpoint API menggunakan `fetch`.
4. FastAPI menerima parameter seperti kata kunci, topik, jenis dokumen, tahun, halaman, dan urutan.
5. Backend menyusun query SQLite. Jika kata kunci diisi, query menggunakan `documents_fts MATCH`.
6. SQLite mengembalikan data dokumen, jumlah hasil, dan pagination.
7. JavaScript merender hasil ke grid tahun atau tabel dokumen.

### 3.2 Mengapa Menggunakan FTS5

FTS5 dipilih karena kebutuhan utama adalah pencarian teks yang lebih baik daripada `LIKE`, tetapi project tetap ingin berjalan dengan satu database dan tanpa layanan tambahan seperti Elasticsearch. FTS5 membuat indeks terbalik untuk kolom teks, sehingga pencarian kata pada judul dan isi dapat dilakukan dengan `MATCH` dan dapat diurutkan berdasarkan relevansi menggunakan `bm25`.

Elasticsearch atau layanan sejenis lebih cocok ketika data sangat besar, kueri sangat kompleks, atau diperlukan distribusi dan analitik pencarian tingkat lanjut. Untuk **407 dokumen asli** dan kebutuhan demonstrasi saat ini, FTS5 memberikan manfaat yang cukup dengan biaya operasional yang jauh lebih rendah.

### 3.3 Sinkronisasi FTS dengan Trigger

Tabel `documents_fts` adalah virtual table FTS5 yang terhubung ke tabel utama `documents` melalui `content='documents'` dan `content_rowid='id'`. Agar indeks tidak terpisah secara manual, database memakai tiga trigger:

- `documents_ai` dijalankan setelah dokumen baru ditambahkan, lalu menyalin `id`, `judul`, dan `konten_text` ke FTS.
- `documents_ad` dijalankan setelah dokumen dihapus, lalu menghapus entri FTS berdasarkan `rowid` dan nilai lama.
- `documents_au` dijalankan setelah dokumen diperbarui, lalu menghapus entri lama dan menambahkan entri baru.

Dengan trigger ini, perubahan pada tabel `documents` secara otomatis diikuti oleh perubahan pada indeks pencarian.

## 4. Skema Database

Database disimpan dalam file `jdih.db`. Skema dibuat oleh `app/db.py` saat aplikasi dimulai, sedangkan data diisi melalui dua alternatif:
- `seed.py` — untuk data dummy (150 dokumen, 5 jenis dokumen) — digunakan untuk testing cepat.
- `import_real_data.py` — untuk **data asli (327 dokumen Peraturan Bupati)** — digunakan untuk impor Perbup.
- `import_perda.py` — untuk **data asli (80 dokumen Peraturan Daerah)** — digunakan untuk impor Perda (INSERT, tidak menghapus data Perbup).
- `import_raw_content.py` — untuk mengisi kolom `konten_text_asli` pada Perbup dari `raw_content_export.csv`.

### 4.1 Tabel `documents`

Tabel ini menyimpan metadata dan teks utama setiap produk hukum.

| Kolom | Tipe | Fungsi |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Identifier unik dokumen; juga menjadi `rowid` untuk FTS. |
| `judul` | `TEXT NOT NULL` | Judul lengkap produk hukum. |
| `nomor` | `TEXT` | Nomor dokumen, misalnya `3/2026`. |
| `tanggal_terbit` | `TEXT` | Tanggal terbit dalam format ISO, misalnya `2026-12-20`; tahun diambil dari kolom ini untuk filter. |
| `url_pdf` | `TEXT` | Tautan ke berkas PDF. Pada data asli, tautan berasal dari scraping JDIH resmi dan mengarah ke domain `jdih.banyumaskab.go.id`; namun belum diverifikasi seluruhnya masih aktif. |
| `konten_text` | `TEXT` | Ringkasan atau teks dokumen yang diindeks untuk pencarian. Pada data asli, 47 dokumen memiliki konten kosong karena gagal diekstrak dari PDF sumber (kemungkinan PDF hasil scan/gambar). |
| `jenis_dokumen` | `TEXT` | Jenis dokumen yang dapat difilter, misalnya `Peraturan Bupati`. Kolom ini dibuat generik agar mudah dipetakan ke sumber data lain. |
| `konten_text_asli` | `TEXT` | Salinan teks mentah hasil ekstraksi PDF (belum dibersihkan). Dipakai untuk ekstraksi pasal/prosedur dan sebagai sumber data cadangan ke FTS. |
| `status_hukum` | `TEXT` | Status berlakunya dokumen: `Berlaku` atau `Tidak Berlaku`. Hanya terisi untuk **Peraturan Daerah** (data Perbup tidak memiliki kolom ini saat awal impor). Dapat bernilai NULL. |
| `catatan_relasi` | `TEXT` | Teks mentah dari JDIH tentang mencabut/mengubah dokumen ini (mis. "Dicabut dengan Peraturan Bupati ..."). **46 dari 83 Perda** memiliki catatan relasi. Belum dipetakan ke relasi terstruktur. Dapat bernilai NULL. |
| `nomor_tahun` | `TEXT` | Identifier unik lintas jenis dokumen. Untuk Perbup memakai format `{nomor}_{tahun}` (mis. `3_2020`); untuk Perda memakai prefix `perda_` (mis. `perda_1_2020`) agar tidak bentrok dengan Perbup yang nomor+tahunnya sama. |

### 4.2 Tabel `topics`

Tabel ini menyimpan daftar topik yang dapat digunakan sebagai filter.

| Kolom | Tipe | Fungsi |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Identifier unik topik. |
| `label_topik` | `TEXT NOT NULL UNIQUE` | Nama topik yang ditampilkan pada chip filter. |
| `top_keywords` | `TEXT` | Daftar kata kunci yang membantu pengelola memahami cakupan topik; saat ini tidak digunakan sebagai query FTS terpisah. |

### 4.3 Tabel `document_topics`

Tabel ini merupakan tabel penghubung antara dokumen dan topik.

| Kolom | Tipe | Fungsi |
|---|---|---|
| `document_id` | `INTEGER NOT NULL` | Referensi ke `documents.id`. |
| `topic_id` | `INTEGER NOT NULL` | Referensi ke `topics.id`. |

Kombinasi `(document_id, topic_id)` menjadi primary key sehingga satu dokumen tidak dapat memiliki relasi duplikat ke topik yang sama. Relasi ini memakai foreign key dengan `ON DELETE CASCADE`: ketika dokumen atau topik dihapus, relasinya ikut dihapus.

Hubungan yang terbentuk adalah **many-to-many**:

```text
documents 1 ---- * document_topics * ---- 1 topics
```

Artinya, satu dokumen dapat memiliki beberapa topik, dan satu topik dapat dimiliki oleh banyak dokumen.

### 4.4 Tabel `documents_fts`

Tabel ini adalah virtual table FTS5 untuk pencarian teks.

| Kolom | Tipe | Fungsi |
|---|---|---|
| `rowid` | Integer row identifier | Menghubungkan entri indeks dengan `documents.id`. |
| `judul` | FTS5 text column | Judul dokumen yang dapat dicari. |
| `konten_text` | FTS5 text column | Isi/ringkasan dokumen yang dapat dicari. |

Tabel ini tidak diisi secara langsung oleh kode seed. Pengisiannya dilakukan otomatis oleh trigger ketika data dimasukkan ke `documents`.

## 4.5 Cara Kerja Ekstraksi Pasal

Ekstraksi pasal menggunakan **regex, bukan AI**. Alur `extract_pasal_v2` (yang digunakan saat ini):

1. **Cari titik awal.** Mencari kata `MEMUTUSKAN` (case-insensitive). Jika tidak ditemukan, tidak ada pasal yang diekstrak.
2. **Cari judul pasal.** Hanya mempertimbangkan baris yang berbentuk `Pasal N.` / `Pasal N` sebagai judul pasal di awal baris (`_PASAL_JUDUL_PATTERN`, multiline).
3. **Validasi urutan nomor.** Nomor pasal harus naik dari `expected = 1`, dan loncatan nomor maksimal **5** (`_MAX_LONJAT_NOMOR = 5`). Hanya baris yang memenuhi syarat yang dipertimbangkan valid.
4. **Potong isi antar judul.** Isi pasal diambil dari akhir judul pasal hingga awal judul pasal berikutnya, atau sampai akhir teks.
5. **Batas akhir ekstraksi.** Isi dipotong di **BAB** dan **LAMPIRAN** (`_BAB_JUDUL_PATTERN`, `_LAMPIRAN_RE`) — konten setelah BAB/LAMPIRAN tidak dimasukkan ke dalam isi pasal.
6. **Tampilan dibatasi 600 karakter.** `_MAX_ISI_LENGTH = 600`. Jika isi pasal lebih dari 600 karakter, tampilan dipotong pada spasi terakhir dan ditambahkan penanda `(dipotong, baca selengkapnya di dokumen lengkap)`; `terpotong` di-set `true`.
7. **Klasifikasi prosedural.** `is_procedural(isi_pasal)` menggunakan **11 kata kunci**: `mengajukan`, `melampirkan`, `menyerahkan`, `diterbitkan`, `permohonan`, `verifikasi`, `hari kerja`, `disetujui`, `ditolak`, `persyaratan`, `tahapan` (skor minimal 2) **atau** terdapat **penomoran ayat berurutan (minimal (1),(2),...)**. Ditandai `is_procedural`, `skor_keyword`, `ada_penomoran_ayat`.

**Catatan:** Untuk 3 dokumen atau kurang pada hasil daftar, field `prosedur` diisi pada `GET /api/documents` (lihat Bab 5.1). Tarik kesimpulan ini hanya berdasarkan kode; ekstraksi berbasis regex, bukan AI.

Semua endpoint menggunakan metode `GET` dan mengembalikan JSON. FastAPI juga menyediakan dokumentasi interaktif pada `/docs` ketika server berjalan.

### 5.1 `GET /api/documents`

Endpoint ini mengambil daftar dokumen dengan pencarian, filter, pengurutan, dan pagination.

**Parameter:**

| Parameter | Wajib | Default | Keterangan |
|---|---:|---:|---|
| `q` | Tidak | - | Kata kunci full-text search. Jika kosong, FTS tidak digunakan. |
| `topic` | Tidak | - | Filter berdasarkan ID topik. |
| `jenis` | Tidak | - | Filter berdasarkan nilai `jenis_dokumen`. |
| `tahun` | Tidak | - | Filter tahun terbit, dibatasi antara 2000 dan 2030. |
> **Catatan:** Pada `GET /api/documents`, field `prosedur` hanya diisi bila hasil **3 dokumen atau kurang** (untuk hasil > 3, `prosedur` bernilai `null`, `app/routers/documents.py:303-307`).
| `sort` | Tidak | `terbaru` | `terbaru` mengurutkan tanggal turun; `relevansi` mengurutkan berdasarkan `bm25` hanya jika `q` diisi. |
| `page` | Tidak | `1` | Halaman hasil, minimal 1. |
| `limit` | Tidak | `10` | Jumlah dokumen per halaman, antara 1 dan 100. |

**Contoh request:**

```http
GET /api/documents?q=RKPD&topic=4&jenis=Peraturan%20Bupati&tahun=2023&sort=relevansi&page=1&limit=10
```

**Contoh response:**

```json
{
  "data": [
    {
      "id": 57,
      "judul": "Peraturan Bupati Banyumas Nomor 3 Tahun 2023 Tentang Rencana Kerja Pemerintah Daerah (RKPD) Kabupaten Banyumas Tahun 2023",
      "nomor": "3/2023",
      "tanggal_terbit": "2023-01-01",
      "jenis_dokumen": "Peraturan Bupati",
      "url_pdf": "https://jdih.banyumaskab.go.id/downloadprodukhukum/xxx",
      "status_hukum": null,
      "catatan_relasi": null,
      "topics": [
        {
          "id": 4,
          "label_topik": "Perencanaan Pembangunan Daerah"
        }
      ]
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 1,
    "total_pages": 1
  }
}
```

**Kegunaan:** menjadi sumber data utama untuk tabel dokumen, jumlah hasil, dan pagination pada frontend.

### 5.2 `GET /api/documents/{id}`

Endpoint ini mengambil detail satu dokumen berdasarkan ID.

**Parameter:**

| Parameter | Wajib | Keterangan |
|---|---:|---|
| `id` | Ya | ID dokumen pada path, misalnya `57`. |

**Contoh request:**

```http
GET /api/documents/57
```

**Contoh response:**

```json
{
  "id": 57,
  "judul": "Peraturan Bupati Banyumas Nomor 3 Tahun 2023 Tentang Rencana Kerja Pemerintah Daerah (RKPD) Kabupaten Banyumas Tahun 2023",
  "nomor": "3/2023",
  "tanggal_terbit": "2023-01-01",
  "jenis_dokumen": "Peraturan Bupati",
  "url_pdf": "https://jdih.banyumaskab.go.id/downloadprodukhukum/xxx",
  "konten_text": "Menetapkan Rencana Kerja Pemerintah Daerah Banyumas Tahun 2023 yang disusun berdasarkan RPJMD dan hasil Musrenbang. Memuat program prioritas, target indikator, dan alokasi anggaran per perangkat daerah untuk mewujudkan visi misi pembangunan daerah.",
  "topics": [
    {
      "id": 4,
      "label_topik": "Perencanaan Pembangunan Daerah"
    }
  ]
}
```

Jika ID tidak ditemukan, endpoint mengembalikan status `404` dengan pesan `Dokumen tidak ditemukan`.

**Kegunaan:** menyediakan detail dokumen dan teks lengkap untuk kebutuhan tampilan atau pengembangan fitur detail.

### 5.3 `GET /api/topics`

Endpoint ini mengambil daftar topik beserta jumlah dokumen pada setiap topik.

**Parameter:** tidak ada.

**Contoh request:**

```http
GET /api/topics
```

**Contoh response:**

```json
[
  {
    "id": 1,
    "label_topik": "Organisasi dan Tata Kerja Perangkat Daerah",
    "top_keywords": "organisasi, tata kerja, kedudukan, susunan, unit pelaksana teknis, uptd",
    "jumlah_dokumen": 73
  },
  {
    "id": 2,
    "label_topik": "Standar Biaya dan Honorarium",
    "top_keywords": "standar biaya, honorarium, satuan biaya",
    "jumlah_dokumen": 20
  }
]
```

Respons selengkapnya berisi 10 topik dengan jumlah dokumen per topik (lihat tabel di bagian 7.2).

**Kegunaan:** mengisi chip filter topik dan menampilkan jumlah dokumen per topik.

### 5.4 `GET /api/jenis-dokumen`

Endpoint ini mengambil daftar jenis dokumen beserta jumlahnya.

**Parameter:** tidak ada.

**Contoh request:**

```http
GET /api/jenis-dokumen
```

**Contoh response:**

```json
[
  { "jenis": "Peraturan Bupati", "jumlah": 327 },
  { "jenis": "Peraturan Daerah", "jumlah": 80 }
]
```

**Kegunaan:** mengisi dropdown filter jenis dokumen dan memberi informasi distribusi jenis dokumen. Pada data asli, terdapat dua jenis dokumen — Peraturan Bupati (327) dan Peraturan Daerah (80). Disarankan untuk menampilkan informasi agregat (407 dokumen, 9.229 pasal, 5.162 prosedural, 55,9%) dengan rincian per jenis (Perbup 327 / 6.455 / 3.337, Perda 80 / 2.774 / 1.825).

### 5.5 `GET /api/status-hukum`

Endpoint ini mengembalikan daftar nilai unik `status_hukum` yang ada di database beserta jumlah dokumen masing-masing. Hanya dokumen Peraturan Daerah yang memiliki `status_hukum`; dokumen Peraturan Bupati selalu NULL dan tidak dihitung. **Tambahan:** tersedia endpoint `GET /api/status-hukum` untuk keperluan ini. Parameter `status` juga tersedia pada `GET /api/documents` untuk memfilter berdasarkan `status_hukum`. Response dokumen menyertakan field `status_hukum` dan `catatan_relasi`.

**Parameter:** tidak ada.

**Contoh request:**

```http
GET /api/status-hukum
```

**Contoh response:**

```json
{
  "data": [
    { "status": "Berlaku", "jumlah": 52 },
    { "status": "Tidak Berlaku", "jumlah": 28 }
  ],
  "total_status": 2,
  "total_dokumen_terfilter": 80
}
```

**Kegunaan:** mengisi dropdown filter status hukum pada frontend dan memberi informasi distribusi status. Dapat digunakan bersama parameter `status` pada `GET /api/documents`.

### 5.6 `GET /api/tahun`

Endpoint ini mengambil daftar tahun yang tersedia berdasarkan `tanggal_terbit`.

**Parameter:** tidak ada.

**Contoh request:**

```http
GET /api/tahun
```

**Contoh response:**

```json
[2024, 2023, 2022, 2021, 2020]
```

**Kegunaan:** menyediakan metadata tahun untuk pengembangan atau komponen frontend yang membutuhkan daftar tahun; tampilan grid tahun saat ini menghitung jumlah dokumen per tahun melalui `/api/documents`.

### 5.7 GET /api/documents/{id}/prosedur

Mengembalikan hasil `get_prosedur_untuk_dokumen()` berdasarkan `konten_text_asli`. Status: `tidak_ada_teks`, `tidak_ditemukan_pasal`, `tidak_ditemukan_prosedur`, `ditemukan` (dengan `pasal_prosedural` berisi `nomor_pasal`, `isi_pasal`, `skor_keyword`, `terpotong`).

### 5.8 GET /api/documents/tata-cara

Mencari tata cara berdasarkan `q`. Dua tahap: (1) FTS5 tanpa sinonim, (2) bila tidak ditemukan dicoba dengan sinonim (`diperluas_sinonim`). Pasal definisi/maksud-tujuan dikecualikan; prioritas dokumen non-perubahan (kandidat perubahan hanya dipakai bila tidak ada non-perubahan). Status: `ditemukan`, `hanya_dokumen_perubahan` (hanya dokumen perubahan ditampilkan, tanpa pasal prosedural langsung), `tidak_ditemukan`. Maksimal 8 pasal relevan.

### 6.1 Pola Drill-down: State A ke State B

Frontend memakai dua state tampilan utama untuk meniru pola navigasi JDIH yang umumnya memulai penelusuran dari daftar tahun, lalu masuk ke daftar produk hukum.

```text
State A: Grid Tahun
  2011 | 2012 | ... | 2026
          |
          | pengguna memilih tahun
          v
State B: Tabel Dokumen
  tanggal | judul | jenis/topik | aksi
```

**State A — grid tahun**

- Tampilan awal menampilkan kartu tahun dari **2020 sampai 2024**.
- Setiap kartu menampilkan jumlah dokumen pada tahun tersebut.
- Jumlah dihitung melalui `/api/documents` dengan parameter `tahun`, `jenis`, dan `topic` yang sedang aktif.
- Jenis dokumen default pada frontend adalah `Peraturan Bupati`, sehingga judul awal adalah `DAFTAR PERATURAN BUPATI`.

**State B — tabel dokumen**

- Pengguna masuk ke State B ketika mengklik salah satu kartu tahun.
- Tabel menampilkan tanggal terbit, judul, badge jenis dan topik, serta tombol download.
- Tabel juga memiliki pagination dan informasi jumlah dokumen yang ditampilkan.
- Jika pengguna memasukkan pencarian atau memilih topik saat masih di State A, frontend otomatis pindah ke State B karena hasil pencarian lebih tepat ditampilkan sebagai daftar dokumen.
- Jika hanya jenis dokumen diubah saat berada di State A, grid tahun diperbarui tanpa pindah state.

Breadcrumb digunakan untuk kembali ke daftar tahun. Jika hanya filter tahun yang aktif, breadcrumb akan membersihkan tahun dan kembali ke grid. Jika pencarian atau topik juga aktif, breadcrumb berfungsi sebagai reset dan kembali ke kondisi awal.

Desain ini dipilih agar pengguna dapat memahami distribusi dokumen berdasarkan tahun terlebih dahulu, kemudian memperdalam penelusuran ke dokumen individual. Pola tersebut lebih dekat dengan kebiasaan pengguna JDIH dibandingkan langsung menampilkan seluruh dokumen dalam satu tabel panjang.

### 6.2 Kombinasi Filter

Filter dapat digabungkan dan diperlakukan sebagai irisan hasil:

- `q`: membatasi dokumen yang cocok dengan full-text search.
- `topic`: membatasi dokumen yang memiliki relasi ke topik tertentu.
- `jenis`: membatasi dokumen dengan jenis yang dipilih (pada data asli hanya tersedia "Peraturan Bupati", sehingga filter ini efektif tidak memisahkan dokumen).
- `tahun`: membatasi dokumen berdasarkan tahun terbit.

Jika beberapa filter diisi, backend menerapkan semuanya secara bersamaan. Contohnya, permintaan dengan `q=RKPD`, `topic=4`, `jenis=Peraturan Bupati`, dan `tahun=2023` hanya mengembalikan dokumen yang memenuhi keempat kondisi tersebut.

Pencarian input diberi debounce selama 300 milidetik agar API tidak dipanggil pada setiap karakter yang diketik. Topik menggunakan pilihan tunggal: mengklik topik yang sama akan menonaktifkan filter tersebut. Dropdown jenis dokumen pada data asli hanya menampilkan satu opsi ("Peraturan Bupati" / "Semua Jenis").

Urutan default adalah `terbaru`, yaitu `tanggal_terbit DESC`. Urutan `relevansi` hanya digunakan jika pengguna/API mengirim `q` dan `sort=relevansi`; jika tidak ada kata kunci, aplikasi tetap menggunakan urutan terbaru.

### 6.3 Penanganan Race Condition pada Fetch

Frontend memakai dua mekanisme agar respons lama tidak menimpa tampilan yang lebih baru.

1. **Version token untuk grid tahun**

   Setiap kali grid tahun diminta, `yearFetchVersion` ditambah. Semua permintaan tahun **2020–2024** dijalankan dengan `Promise.all`, tetapi hasil hanya diterima jika nomor versi masih sama dengan versi terbaru. Jika pengguna mengubah filter lebih dahulu, respons lama diabaikan.

2. **`AbortController` untuk fetch dokumen**

   Sebelum permintaan dokumen baru dimulai, frontend membatalkan permintaan dokumen sebelumnya melalui `AbortController`. Jika browser menghasilkan `AbortError`, frontend mengabaikannya dan tidak merender hasil dari permintaan yang sudah tidak relevan.

Kedua mekanisme ini penting karena permintaan API dapat selesai dalam urutan yang berbeda dari urutan pengiriman, terutama saat pengguna cepat mengganti pencarian, topik, jenis, tahun, atau halaman.

## 7. Data Saat Ini

Data saat ini adalah **data asli 407 dokumen** yang terdiri dari **327 Peraturan Bupati** dan **80 Peraturan Daerah** Kabupaten Banyumas, diimpor dari hasil pengumpulan data skripsi penulis melalui `import_real_data.py` (Perbup) dan `import_perda.py` (Perda) — bukan data dummy dari `seed.py`. Totalnya terdapat **9.229 pasal** dan **5.162 prosedural (55,9%)**, dengan rincian per jenis (Perbup 327 / 6.455 / 3.337, Perda 80 / 2.774 / 1.825).\n\n### 7.1 Data Peraturan Daerah\n\n- **Jumlah:** 83 dokumen tahun 2020-2026 hasil scraping situs JDIH Banyumas.\n- **Proses scraping:** daftar per tahun → halaman detail → unduh PDF → ekstraksi teks → PDF dihapus setelah diekstrak.\n- **Hasil ekstraksi:** 92 ditemukan, 9 gagal ekstraksi teks.\n- **Batas yang dipakai:** maksimal 1.000 halaman dan 180 detik per dokumen.\n- **Status hukum:** hanya tersedia untuk Peraturan Daerah; `catatan_relasi` tersedia sebagai teks mentah (46 dari 83 Perda), belum diparsing menjadi relasi terstruktur. `nomor_tahun` menggunakan prefix `"perda_"` untuk mencegah bentrok dengan Perbup.

### 7.1 Jumlah Dokumen

| Jenis dokumen | Dokumen dengan pasal | Dokumen total | Jumlah pasal | Prosedural | Rasio prosedural |
|---|---:|---:|---:|---:|---:|
| Peraturan Bupati | 327 | 386 | 6.455 | 3.337 | 51,7% |
| Peraturan Daerah | 80 | 83 | 2.774 | 1.825 | 66,1% |
| **Total** | **407** | **469** | **9.229** | **5.162** | **55,9%** |

> **Keterangan:** "dokumen dengan pasal" berarti dokumen yang berhasil diekstrak setidaknya 1 pasal oleh `extract_pasal`. Dokumen yang tidak ada pasalnya (62 dokumen) biasanya berupa dokumen pendahuluan atau tidak terstruktur pasal-nya. Perbup memiliki 47 dokumen tanpa `konten_text_asli` (gagal ekstraksi PDF); 327 dari 339 yang tersisa memiliki pasal. Perda memiliki 3 dokumen tanpa pasal.

Pada data asli, terdapat dua jenis dokumen: **Peraturan Bupati** (386 dokumen) dan **Peraturan Daerah** (83 dokumen).

### 7.2 Topik

Terdapat 10 topik yang didefinisikan berdasarkan kata kunci pada judul dokumen:

| ID | Topik | Jumlah relasi dokumen |
|---:|---|---:|
| 1 | Organisasi dan Tata Kerja Perangkat Daerah | 73 |
| 2 | Standar Biaya dan Honorarium | 20 |
| 3 | Pengadaan Barang/Jasa | 27 |
| 4 | Perencanaan Pembangunan Daerah | 10 |
| 5 | Kepegawaian dan Aparatur Sipil Negara | 35 |
| 6 | Pajak dan Retribusi Daerah | 41 |
| 7 | Pelayanan Kesehatan | 33 |
| 8 | Pendidikan | 14 |
| 9 | Pertanian dan Lingkungan Hidup | 7 |
| 10 | Sosial dan Kemasyarakatan | 55 |

Jumlah relasi topik (**353**) lebih besar dari jumlah dokumen (469) karena satu dokumen dapat memiliki lebih dari satu topik. **183 dari 469 dokumen (39,0%) tidak memiliki topik** karena judulnya tidak match kata kunci kategori manapun (139 Perbup + 44 Perda).

Distribusi topik hanya dihitung dari judul dokumen untuk Peraturan Bupati (327 dari 386 dokumen memiliki topik). Peraturan Daerah memiliki 39 dokumen dengan topik dan 44 tanpa topik.

### 7.3 Rentang Tahun

Data asli mencakup tahun **2020 sampai 2024**, dengan total 5 tahun:

| Tahun | Jumlah dokumen |
|---:|---:|
| 2020 | 97 |
| 2021 | 100 |
| 2022 | 79 |
| 2023 | 79 |
| 2024 | 31 |

### 7.4 Kualitas Konten

- **47 dokumen Perbup (12,2% dari 386)** memiliki `konten_text` kosong karena gagal diekstrak dari PDF sumber (kemungkinan PDF berupa scan/gambar tanpa lapisan teks). Dokumen ini tidak bisa ditemukan melalui full-text search pada isi, hanya melalui judul.
- **Peraturan Daerah (83 dokumen)**: 92 ditemukan di JDIH, 9 gagal ekstraksi teks (PDF scan tanpa layer teks), 83 berhasil diimpor dengan `konten_text_asli` terisi penuh.
- `url_pdf` diambil dari hasil scraping asli JDIH, mengarah ke domain resmi, namun belum diverifikasi seluruhnya masih aktif.

## 7.5 Cara Kategorisasi Topik pada Data Asli

Topik ditentukan melalui **pencocokan kata kunci sederhana (string matching case-insensitive) pada kolom JUDUL saja**, bukan hasil topic modeling (LDA/BERTopic) dari skripsi. Hal ini sengaja dipisahkan agar metodologi skripsi tidak tercampur dengan project magang ini.

Proses:
1. Definisikan 10 kategori topik dengan daftar kata kunci masing-masing (lihat tabel di bawah).
2. Untuk setiap dokumen, cek apakah judul mengandung salah satu kata kunci dari topik tersebut.
3. Jika match, assign relasi dokumen-topik (bisa lebih dari satu topik per dokumen).
4. Jika tidak match topik manapun, dokumen tetap diimport tanpa relasi topik.

**Daftar 10 kategori dan kata kuncinya:**

| Topik | Kata Kunci |
|---|---|
| Organisasi dan Tata Kerja Perangkat Daerah | organisasi, tata kerja, kedudukan, susunan, unit pelaksana teknis, uptd |
| Standar Biaya dan Honorarium | standar biaya, honorarium, satuan biaya |
| Pengadaan Barang/Jasa | pengadaan barang, pengadaan jasa, lpse |
| Perencanaan Pembangunan Daerah | rkpd, rpjmd, rencana kerja pemerintah daerah, rencana pembangunan |
| Kepegawaian dan Aparatur Sipil Negara | pegawai, pns, pppk, aparatur sipil negara, jabatan fungsional, tambahan penghasilan |
| Pajak dan Retribusi Daerah | pajak, retribusi, pbb, bphtb |
| Pelayanan Kesehatan | kesehatan, puskesmas, rumah sakit, jkn |
| Pendidikan | pendidikan, sekolah, ppdb, bos |
| Pertanian dan Lingkungan Hidup | pertanian, petani, lingkungan hidup, sampah, air tanah |
| Sosial dan Kemasyarakatan | sosial, bantuan sosial, desa, kemasyarakatan, disabilitas |

## 7.6 Keterbatasan Data Asli

1. **Tanggal terbit placeholder**: `tanggal_terbit` menggunakan format `{tahun}-01-01` karena data sumber hanya memiliki informasi tahun, bukan tanggal lengkap. Akibatnya, pengurutan "terbaru" (`tanggal_terbit DESC`) **dalam tahun yang sama tidak benar-benar berurutan berdasarkan tanggal asli**.
2. **Konten kosong**: 47 dokumen Perbup (12,2%) tidak bisa di-full-text-search karena `konten_text` kosong (gagal ekstraksi dari PDF scan/gambar). Hanya judul yang terindeks.
3. **Dokumen tanpa topik**: 183 dari 469 dokumen (39,0%) tidak muncul saat filter topik apapun dipakai karena judul tidak match kata kunci kategori manapun (139 Perbup + 44 Perda).
4. **URL PDF belum diverifikasi**: `url_pdf` diambil dari hasil scraping asli, tautan mengarah ke domain JDIH resmi, namun belum diverifikasi seluruhnya masih aktif/tersedia.
5. **Topik berbasis judul saja**: Klasifikasi topik dilakukan dengan mencocokkan kata kunci pada **judul** saja, bukan isi dokumen. Dokumen dengan judul tidak informatif dapat gagal diklasifikasikan.

## 7.7 Data Peraturan Daerah

Peraturan Daerah (Perda) ditambahkan ke database sebagai data tambahan di luar skop Peraturan Bupati. Berikut rincian pengelolaannya.

### 7.7.1 Asal Usul dan Jumlah Data

- **83 dokumen Peraturan Daerah** tahun **2020–2026** diimpor ke `jdih.db`.
- **92 dokumen** ditemukan di situs JDIH Banyumas; **9 dokumen** gagal ekstraksi teks (kemungkinan PDF hasil scan/gambar tanpa layer teks); **83 dokumen** berhasil diekstrak dan diimpor dengan `konten_text_asli` terisi penuh.
- **9.229 pasal** terekstrak dari ke-407 dokumen (Perbup 6.455 + Perda 2.774); **5.162 prosedural (55,9%)**, dengan rincian per jenis (Perbup 327 / 6.455 / 3.337, Perda 80 / 2.774 / 1.825).

### 7.7.2 Proses Scraping

Scraping dilakukan oleh script di folder `scraping_perda/` dengan alur berikut:

1. **Daftar per tahun**: `scrape_metadata.py` mengunjungi halaman listing JDIH untuk setiap tahun 2020–2026, mengumpulkan metadata (ID dokumen, nomor, tahun, judul, URL PDF). Target awal: **92 dokumen**.
2. **Halaman detail**: untuk setiap dokumen, metadata tambahan (termasuk `status_hukum` dan `catatan_relasi` bila tersedia) diekstrak dari halaman detail masing-masing.
3. **Unduh PDF**: `download_extract.py` mengunduh PDF dari `/downloadprodukhukum/{doc_id}` dengan `requests` (stream=True).
4. **Ekstraksi teks**: `pdfplumber` digunakan untuk mengekstrak teks dari PDF. Sebelum memproses seluruh file, dilakukan **sampling 3 halaman pertama** untuk mendeteksi PDF hasil scan (tanpa layer teks) — dokumen semacam itu langsung ditandai gagal.
5. **Hapus PDF setelah ekstrak**: `proses_semua.py` **langsung menghapus file PDF** setelah teks diekstrak (baik sukses maupun gagal). Hal ini dilakukan karena ruang disk terbatas (~6 GB pada drive D:). Hanya file teks hasil ekstraksi yang disimpan di `scraping_perda/text_raw/`.
6. **Checkpoint**: setiap dokumen yang selesai dicatat dalam `checkpoint_ekstraksi.json`, sehingga proses dapat dilanjutkan tanpa mengulang dokumen yang sudah selesai.

### 7.7.3 Batas yang Dipakai

| Batas | Nilai | Keterangan |
|---|---|---|
| `BATAS_HALAMAN` | 1000 | PDF dengan lebih dari 1000 halaman dilewati (terverifikasi: ada PDF 1458 halaman). |
| `BATAS_WAKTU_DETIK` | 180 | Timeout 180 detik per dokumen; dokumen melebihi limit ditandai dan dapat dicoba ulang. |
| `HALAMAN_SAMPEL` | 3 | Jumlah halaman sampel untuk mendeteksi PDF scan. |
| `MIN_FREE_GB` | 1.5 | Proses berhenti jika sisa disk di bawah 1,5 GB. |
| `DELAY` | 1.5s | Jeda antar-request untuk menghindari beban berlebih pada server JDIH. |

### 7.7.4 Proses Import ke Database

`import_perda.py` menambahkan 83 dokumen Perda ke `jdih.db` dengan mekanisme berikut:

- **INSERT (bukan REPLACE)**: data Perbup tidak dihapus/ditimpa.
- **Prefix `perda_` pada `nomor_tahun`**: identifier Perda memakai format `perda_{nomor}_{tahun}` (mis. `perda_1_2020`) untuk mencegah bentrok dengan identifier Perbup yang sama.
- **Topik dari kolom CSV**: topik tidak dihitung ulang; diload langsung dari kolom `topik` di `perda_export.csv`.
- **Idempoten**: dokumen yang identifier-nya sudah ada dilewati (dicek via `nomor_tahun` atau `jenis_dokumen + nomor + tahun`).
- **`status_hukum` dan `catatan_relasi`**: diisi dari CSV (kosongkan/NULL bila tidak tersedia). 46 dari 83 Perda memiliki `catatan_relasi`.

### 7.7.5 Status Hukum dan Catatan Relasi

- **`status_hukum`**: hanya tersedia untuk Peraturan Daerah (83 dokumen). Nilai: `Berlaku` (52) atau `Tidak Berlaku` (28), sisanya NULL. Dokumen Peraturan Bupati tidak memiliki kolom ini (selalu NULL).
- **`catatan_relasi`**: berisi teks mentah dari JDIH tentang pencabutan/perubahan. **46 dari 83 Perda** memiliki catatan relasi (mis. "Dicabut dengan Peraturan Daerah ..."). Belum diparse menjadi relasi terstruktur (lihat Bab 8.4).

## 8. Keterbatasan & Pengembangan Lanjutan

### 8.1 Yang Sengaja Belum Dikerjakan

Beberapa fitur belum dimasukkan karena data yang diperlukan belum tersedia atau karena cakupannya berada di luar demo:

- **Status hukum berlaku/dicabut.** Kolom `status_hukum` sudah ditambahkan (lihat Bab 4.1), tetapi hanya terisi untuk **Peraturan Daerah** (83 dokumen). Dokumen Peraturan Bupati tidak memiliki status karena data sumbernya tidak mencakupnya.
- **Relasi antar peraturan terstruktur.** Kolom `catatan_relasi` sudah tersedia sebagai teks mentah (46 dari 83 Perda), tetapi **belum diparse** menjadi relasi terstruktur (tabel `related_documents` dengan tipe relasi). Perlu parsing ekstraksi referensi dokumen dari teks bebas.
- **Pencarian semantik.** Pencarian saat ini berbasis kata/istilah melalui FTS5, bukan pencarian berdasarkan makna. Pencarian semantik memerlukan embedding, model bahasa, dan infrastruktur vector search yang belum menjadi kebutuhan demo.
- **Administrasi dokumen.** CRUD, autentikasi, autorisasi, audit trail, dan validasi unggahan belum disediakan karena project difokuskan pada pengalaman pencarian pengguna.

### 8.2 Pengembangan yang Dapat Ditambahkan

Jika project dikembangkan lebih jauh, beberapa langkah yang dapat dipertimbangkan adalah:

1. Menambahkan kolom status hukum dan tanggal efektif jika data resmi tersedia.
2. Menambahkan tabel relasi antar dokumen, misalnya `related_documents`, dengan jenis relasi.
3. Menambahkan highlight kata pencarian pada judul atau isi.
4. Menambahkan filter gabungan yang lebih lengkap, seperti beberapa topik sekaligus atau rentang tahun.
5. Menambahkan halaman detail dokumen yang menampilkan metadata dan isi secara lebih lengkap.
6. Menambahkan administrasi untuk mengelola dokumen, topik, dan relasi.
7. Menambahkan pengujian API dan frontend untuk mencegah regresi.
8. Jika volume data dan trafik meningkat, mengevaluasi PostgreSQL, layanan pencarian terdedikasi, atau vector search.

### 8.3 Status Integrasi Data JDIH Asli

**Sudah selesai** untuk kedua jenis dokumen:

1. ✅ Data dokumen diekspor dari sumber JDIH resmi (hasil scraping skripsi).
2. ✅ Kolom dipetakan ke `judul`, `nomor`, `tanggal_terbit` (placeholder), `jenis_dokumen`, `url_pdf`, `konten_text`, `konten_text_asli`, `nomor_tahun`.
3. ✅ Nilai `jenis_dokumen` dinormalisasi ke "Peraturan Bupati" dan "Peraturan Daerah".
4. ✅ Daftar 10 topik resmi dibuat dan diisi ke tabel `topics`.
5. ✅ Relasi `document_topics` diisi berdasarkan klasifikasi otomatis kata kunci pada judul.
6. ✅ `init_db()` pada `app/db.py` menambah kolom `konten_text_asli`, `status_hukum`, `catatan_relasi`, dan `nomor_tahun` secara otomatis jika belum ada.
7. ✅ FTS5 tersinkronisasi otomatis melalui trigger setelah impor.
8. ✅ Endpoint `GET /api/status-hukum` dan parameter `status` pada `GET /api/documents` tersedia.
9. ✅ `import_perda.py` menambahkan 80 dokumen Perda (dari 83 yang berhasil) dengan prefix `perda_` pada `nomor_tahun`; tidak menghapus data Perbup.

**Belum dilakukan / Catatan lanjutan:**
- Verifikasi status aktif/tersedia tautan PDF belum dilakukan menyeluruh.
- Kualitas ekstraksi teks PDF bisa ditingkatkan (47 dokumen Perbup kosong).
- Klasifikasi topik berbasis kata kunci judul bisa dikembangkan ke klasifikasi berbasis isi dokumen (konten_text) atau model ML jika diperlukan.
- Relasi antar peraturan (`catatan_relasi`) belum diparse menjadi struktur terrelasi.

### 8.4 Keterbatasan

Berikut keterbatasan teknis dan data yang perlu diperhatikan:

1. **Status hukum hanya tersedia untuk Peraturan Daerah, bukan Peraturan Bupati.** Kolom `status_hukum` diisi hanya untuk Perda (83 dokumen). Dokumen Perbup (386) selalu NULL karena data sumbernya tidak mencakup status berlaku/cabut. Filter `status` pada `GET /api/documents` tidak akan berdampak pada dokumen Perbup.
2. **Catatan relasi belum diparsing menjadi relasi terstruktur.** Kolom `catatan_relasi` berisi teks mentah (46 dari 83 Perda) tentang pencabutan/perubahan, tetapi belum dipetakan ke relasi terstruktur.
3. **Dokumen tanpa teks.** 47 Perbup dan 9 Perda tidak punya teks.
4. **Topik belum lengkap.** 53% Perda dan 36% Perbup belum punya topik.
5. **False positive kata kunci topik.** Kata kunci topik pernah menimbulkan false positive karena pencocokan substring (contoh: "bangunan" cocok dengan "pembangunan") dan sudah diperbaiki dengan pencocokan kata utuh.
6. **Belum ada evaluasi dengan set pertanyaan nyata.** Belum ada evaluasi dengan set pertanyaan nyata untuk mengukur keberhasilan sistem.
2. **Catatan relasi belum diparse menjadi relasi terstruktur.** Kolom `catatan_relasi` berisi teks mentah bebas (mis. "Dicabut dengan Peraturan Daerah Nomor 5 Tahun 2022"). Belum ada ekstraksi entitas, referensi dokumen, atau tabel `related_documents` untuk menghubungkan dokumen secara terstruktur.
3. **47 dokumen Perbup dan 9 Perda tidak punya teks.** 47 dokumen Perbup gagal ekstraksi PDF (scan/gambar tanpa layer teks); 9 Perda juga gagal (dari 92 yang ditemukan, hanya 83 yang berhasil). Dokumen-dokumen ini tidak bisa dilakukan full-text search pada isi, hanya pada judul.
4. **53% Perda dan 36% Perbup belum punya topik.** Dari 83 Perda, 44 dokumen (53%) tidak memiliki topik karena judul tidak match kata kunci. Dari 386 Perbup, 139 dokumen (36%) juga tidak memiliki topik.
5. **Kata kunci topik pernah menimbulkan false positive karena pencocokan substring.** Contoh: kata "bangunan" cocok dengan "pembangunan", atau "desa" cocok dengan "perdesaan". Ini sudah **diperbaiki** dengan pencocokan kata utuh (`\\b` word boundary) pada `import_real_data.py` dan `kategorisasi_ulang.py`.

### 8.5 Kesiapan untuk Skala Penuh

Jika ingin memperluas sistem ke ribuan dokumen, langkah berikut harus dikerjakan terlebih dahulu:

1. **Pra-ekstraksi pasal ke tabel tersendiri.** Saat ini, pasal diekstrak on-the-fly lewat `extract_pasal()` pada setiap request `/tata-cara` dan `/prosedur`. Pada skala ribuan dokumen, ini akan menghabiskan waktu. Pasal harus diekstrak sekali pada fase import dan disimpan di tabel `clauses` (atau serupa) untuk query cepat.
2. **Status hukum untuk semua dokumen.** Perlu pipeline untuk menyinkronkan status berlaku/cabut secara periodik dari sumber JDIH. Saat ini hanya tersedia untuk 83 Perda.
3. **Peringatan untuk aturan yang sudah diubah atau dicabut.** Sistem harus bisa menandai dokumen "Tidak Berlaku" secara visual, dan menampilkan dokumen penggantinya (dari `catatan_relasi` yang sudah diparse).
4. **Kategorisasi topik dari metadata resmi atau model.** Klasifikasi berbasis kata kunci judul saja (\\b matching) sudah baik untuk 469 dokumen, tetapi tidak scalable. Pilih: (a) gunakan metadata topik resmi dari JDIH jika tersedia, atau (b) gunakan topic modeling (LDA/BERTopic) atau zero-shot classification.
5. **Evaluasi dengan 30–50 pertanyaan nyata.** Kumpulkan 30–50 pertanyaan penggunaan riil (bukan sintetis) dan uji `GET /api/documents/tata-cara` serta `GET /api/documents/{id}/prosedur` melawan pertanyaan-pertanyaan ini. Laporkan precisi, recall, dan kasus false positive/negative.

## 9. Cara Menjalankan Project

Project dapat dijalankan dari nol dengan Python 3 dan pip.

### 9.1 Clone atau Salin Folder

Clone repository atau salin folder project ke komputer lokal, lalu buka direktori root project:

```bash
cd jdih-fitur-tambahan
```

### 9.2 Buat Virtual Environment

Pada Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

Pada Linux atau macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 9.3 Instal Dependensi

Jalankan dari root project:

```bash
pip install -r requirements.txt
```

Dependensi yang dipasang adalah FastAPI, Uvicorn, dan Jinja2. SQLite merupakan modul standar Python; FTS5 harus tersedia pada build SQLite yang digunakan.

### 9.4 Seed / Import Database

Project menyediakan tiga cara mengisi database:

#### Opsi A: Data Dummy (untuk testing cepat)
```bash
python seed.py
```
Perintah ini akan:
1. Membuat tabel dan trigger jika belum ada.
2. Menghapus isi tabel demo sebelumnya.
3. Membangkitkan **150 dokumen dummy** (5 jenis: Peraturan Bupati, Surat Keputusan, Surat Edaran, Peraturan Daerah, Peraturan Desa).
4. Membuat 10 topik dan relasi dokumen-topik.
5. Menyimpan hasilnya ke `jdih.db`.

Gunakan opsi ini untuk development dan testing cepat alur pencarian/filter.

#### Opsi B: Data Asli (untuk demo/presentasi)
```bash
python import_real_data.py
```
Perintah ini akan:
1. Memanggil `init_db()` untuk memastikan skema tersedia.
2. Menghapus data lama di tabel `documents`, `topics`, `document_topics` (hanya jika semua berjenis "Peraturan Bupati").
3. Membaca `raw_documents_export.csv` (386 baris, hasil scraping skripsi).
4. Insert **386 dokumen Peraturan Bupati** ke tabel `documents`:
   - `jenis_dokumen` diisi "Peraturan Bupati"
   - `tanggal_terbit` diisi placeholder `{tahun}-01-01` (keterbatasan: data asli hanya punya tahun)
5. Insert 10 topik dengan kata kunci ke tabel `topics`.
6. Assign topik ke dokumen berdasarkan pencocokan kata kunci pada **judul** (case-insensitive, word boundary).
7. Print ringkasan: total dokumen, jumlah per topik, dokumen tanpa topik.
8. Menyimpan hasilnya ke `jdih.db`.

Gunakan opsi ini untuk demo presentasi ke pembimbing/pengelola JDIH karena menggunakan data nyata.

#### Opsi C: Impor Peraturan Daerah (setelah Opsi B)
```bash
python import_perda.py
```
Perintah ini akan:
1. Membaca `perda_export.csv` (80 baris yang berhasil diekstrak dari 92 Perda yang ditemukan).
2. **INSERT** dokumen Perda ke `jdih.db` tanpa menghapus data Perbup yang ada.
3. Menambahkan prefix `perda_` pada kolom `nomor_tahun` untuk mencegah bentrok identifier.
4. Mengisi kolom `status_hukum` (hanya Perda: Berlaku/Tidak Berlaku), `catatan_relasi` (46 dari 83), dan `konten_text_asli`.

> **Catatan:** `import_real_data.py` menghapus isi tabel `documents` (hanya jika berjenis "Peraturan Bupati"). Jika database sudah berisi Peraturan Daerah, jalankan `import_perda.py` **setelah** `import_real_data.py`, atau gunakan `import_perda.py` sendiri untuk menambahkan Perda ke database yang sudah berisi Perbup. Selalu backup `jdih.db` sebelum menimpa data.

### 9.5 Jalankan Server

Jalankan server development:

```bash
uvicorn app.main:app --reload
```

Buka browser pada:

```text
http://localhost:8000
```

Dokumentasi API FastAPI dapat dibuka pada:

```text
http://localhost:8000/docs
```

Saat server pertama kali dimulai, event startup akan memanggil `init_db()` untuk memastikan skema database tersedia. Jika database belum pernah di-seed/import, halaman tetap dapat dibuka tetapi daftar dokumen masih kosong sampai `python seed.py` (data dummy) atau `python import_real_data.py` diikuti `python import_perda.py` (data asli) dijalankan.
