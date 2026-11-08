-- usulan_skema.sql
-- Usulan skema tambahan (BELUM DIJALANKAN). Untuk database JDIH PostgreSQL.
-- Hanya CREATE TABLE, tidak ada UPDATE/INSERT.

-- Tabel pasal hasil pra-ekstraksi (opsional, untuk skala besar)
CREATE TABLE IF NOT EXISTS pasal_dokumen (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    nomor_pasal TEXT,
    isi_penuh TEXT,
    is_procedural BOOLEAN DEFAULT FALSE,
    skor_keyword INTEGER DEFAULT 0,
    terpotong BOOLEAN DEFAULT FALSE,
    posisi_awal INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
-- kolom: document_id FK ke documents; nomor_pasal nomor pasal; isi_penuh teks pasal;
-- is_procedural apakah pasal prosedural; skor_keyword skor keyword prosedural;
-- terpotong apakah terpotong; posisi_awal posisi karakter di teks; created_at waktu ekstraksi

CREATE INDEX IF NOT EXISTS idx_pasal_document ON pasal_dokumen(document_id);

-- Tabel log ekstraksi per dokumen
CREATE TABLE IF NOT EXISTS log_ekstraksi (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    jumlah_halaman INTEGER,
    status TEXT,            -- ok / gagal
    alasan_gagal TEXT,
    panjang_teks INTEGER,
    tanggal_proses TIMESTAMP DEFAULT NOW()
);
-- kolom: status hasil ekstraksi; alasan_gagal alasan jika gagal;
-- panjang_teks panjang teks; tanggal_proses waktu proses

-- Tabel relasi dokumen terstruktur
CREATE TABLE IF NOT EXISTS relasi_dokumen (
    id SERIAL PRIMARY KEY,
    doc_sumber INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    doc_target INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    jenis_relasi TEXT NOT NULL,  -- mencabut / mengubah / dicabut_oleh / diubah_oleh
    kutipan TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
-- kolom: doc_sumber dokumen yang menyatakan relasi; doc_target dokumen yang direlasikan;
-- jenis_relasi jenis relasi; kutipan kutipan teks; created_at waktu

-- Tabel sinonim
CREATE TABLE IF NOT EXISTS sinonim (
    id SERIAL PRIMARY KEY,
    keyword TEXT NOT NULL,
    sinonim TEXT NOT NULL,
    UNIQUE (keyword, sinonim)
);
-- kolom: keyword kata kunci; sinonim sinonimnya

-- Tabel log pencarian (tanpa data pribadi)
CREATE TABLE IF NOT EXISTS log_pencarian (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    keywords TEXT,
    hasil_doc_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    pencocokan TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
-- kolom: query_text pertanyaan; keywords keyword yang diekstrak; hasil_doc_id dokumen terpilih;
-- pencocokan strik/longgar; created_at waktu

-- Tabel versi skema
CREATE TABLE IF NOT EXISTS versi_skema (
    id SERIAL PRIMARY KEY,
    versi TEXT NOT NULL,
    deskripsi TEXT,
    tanggal TIMESTAMP DEFAULT NOW()
);
-- kolom: versi nomor versi; deskripsi keterangan; tanggal waktu
