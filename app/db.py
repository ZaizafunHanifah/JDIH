import os
import re
import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "jdih")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "5"))


class ConnWrapper:
    """
    Membungkus koneksi psycopg2 agar mendukung conn.execute(...) dan
    placeholder '?' pada skrip lama.
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        cur = self._conn.cursor()
        if params is not None:
            sql = re.sub(r"%(?!s|%)", "%%", sql).replace("?", "%s")
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
        connect_timeout=DB_CONNECT_TIMEOUT,
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                judul TEXT NOT NULL,
                nomor TEXT,
                tanggal_terbit TEXT,
                url_pdf TEXT,
                konten_text TEXT,
                jenis_dokumen TEXT,
                konten_text_asli TEXT,
                status_hukum TEXT,
                catatan_relasi TEXT,
                nomor_tahun TEXT
            )
        """)
        conn.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS konten_text_asli TEXT")
        conn.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS status_hukum TEXT")
        conn.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS catatan_relasi TEXT")
        conn.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS nomor_tahun TEXT")
        conn.execute("""
            ALTER TABLE documents
            ADD COLUMN IF NOT EXISTS konten_tsv tsvector
            GENERATED ALWAYS AS (
                to_tsvector(
                    'simple',
                    coalesce(judul, '') || ' ' || coalesce(konten_text_asli, '')
                )
            ) STORED
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id SERIAL PRIMARY KEY,
                label_topik TEXT NOT NULL UNIQUE,
                top_keywords TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS document_topics (
                document_id INTEGER NOT NULL,
                topic_id INTEGER NOT NULL,
                PRIMARY KEY (document_id, topic_id),
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_konten_tsv
            ON documents USING GIN (konten_tsv)
        """)