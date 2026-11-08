import os
import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager

# Sebaiknya isi lewat environment variable / file .env, bukan ditulis di kode
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "jdih")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")


class ConnWrapper:
    """
    Membungkus koneksi psycopg2 supaya kode lama bergaya SQLite
    (conn.execute(...).fetchall()) tetap jalan di PostgreSQL.
    - psycopg2 TIDAK punya conn.execute(); harus lewat cursor.
    - Placeholder '?' (SQLite) otomatis diubah jadi '%s' (PostgreSQL).
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        cur = self._conn.cursor()
        if params is not None:
            # '%' literal (mis. LIKE '%abc%') harus di-escape saat ada parameter
            sql = sql.replace("%", "%%").replace("?", "%s")
        cur.execute(sql, params)
        return cur

    def cursor(self, *args, **kwargs):
        return self._conn.cursor(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._conn, name)


@contextmanager
def get_db():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=DictCursor,
    )
    try:
        yield ConnWrapper(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    judul TEXT NOT NULL,
                    nomor TEXT,
                    tanggal_terbit TEXT,
                    url_pdf TEXT,
                    konten_text TEXT,
                    jenis_dokumen TEXT
                )
            """)

            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'documents'
            """)
            columns = [row[0] for row in cursor.fetchall()]

            if "konten_text_asli" not in columns:
                cursor.execute("ALTER TABLE documents ADD COLUMN konten_text_asli TEXT")
            if "status_hukum" not in columns:
                cursor.execute("ALTER TABLE documents ADD COLUMN status_hukum TEXT")
            if "catatan_relasi" not in columns:
                cursor.execute("ALTER TABLE documents ADD COLUMN catatan_relasi TEXT")
            if "nomor_tahun" not in columns:
                cursor.execute("ALTER TABLE documents ADD COLUMN nomor_tahun TEXT")

            # Full-text search (Postgres native, pengganti FTS5 SQLite)
            if "konten_tsv" not in columns:
                cursor.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS konten_tsv tsvector")

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_tsv
                ON documents USING GIN (konten_tsv)
            """)

            cursor.execute("""
                CREATE OR REPLACE FUNCTION documents_tsv_update() RETURNS trigger AS $$
                BEGIN
                    NEW.konten_tsv := to_tsvector('simple',
                        coalesce(NEW.judul, '') || ' ' ||
                        coalesce(NEW.konten_text_asli, '') || ' ' ||
                        coalesce(NEW.konten_text, ''));
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;
            """)

            cursor.execute("""
                DROP TRIGGER IF EXISTS trg_documents_tsv ON documents;
                CREATE TRIGGER trg_documents_tsv
                BEFORE INSERT OR UPDATE ON documents
                FOR EACH ROW EXECUTE FUNCTION documents_tsv_update();
            """)

            cursor.execute("""
                UPDATE documents SET konten_tsv = to_tsvector('simple',
                    coalesce(judul, '') || ' ' ||
                    coalesce(konten_text_asli, '') || ' ' ||
                    coalesce(konten_text, ''))
                WHERE konten_tsv IS NULL
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS topics (
                    id SERIAL PRIMARY KEY,
                    label_topik TEXT NOT NULL UNIQUE,
                    top_keywords TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_topics (
                    document_id INTEGER NOT NULL,
                    topic_id INTEGER NOT NULL,
                    PRIMARY KEY (document_id, topic_id),
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
                )
            """)