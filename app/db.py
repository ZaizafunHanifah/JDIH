import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jdih.db")


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                judul TEXT NOT NULL,
                nomor TEXT,
                tanggal_terbit TEXT,
                url_pdf TEXT,
                konten_text TEXT,
                jenis_dokumen TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                judul, konten_text,
                content='documents',
                content_rowid='id'
            )
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                INSERT INTO documents_fts(rowid, judul, konten_text)
                VALUES (new.id, new.judul, new.konten_text);
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, judul, konten_text)
                VALUES ('delete', old.id, old.judul, old.konten_text);
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, judul, konten_text)
                VALUES ('delete', old.id, old.judul, old.konten_text);
                INSERT INTO documents_fts(rowid, judul, konten_text)
                VALUES (new.id, new.judul, new.konten_text);
            END
        """)

        conn.commit()