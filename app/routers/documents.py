from fastapi import APIRouter, Query, HTTPException
from app.db import get_db

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _fetch_document_topics(conn, doc_id: int):
    return conn.execute("""
        SELECT t.id, t.label_topik
        FROM topics t
        JOIN document_topics dt ON t.id = dt.topic_id
        WHERE dt.document_id = ?
        ORDER BY t.id
    """, (doc_id,)).fetchall()


@router.get("")
async def get_documents(
    q: str | None = Query(None, description="Kata kunci full-text search"),
    topic: int | None = Query(None, description="Filter by topic ID"),
    jenis: str | None = Query(None, description="Filter jenis dokumen (Peraturan Bupati, Peraturan Daerah, Surat Keputusan, Surat Edaran, Peraturan Desa)"),
    tahun: int | None = Query(None, ge=2000, le=2030, description="Filter tahun terbit"),
    sort: str = Query("terbaru", pattern="^(terbaru|relevansi)$", description="Urutan: terbaru atau relevansi"),
    page: int = Query(1, ge=1, description="Halaman (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Jumlah per halaman"),
):
    offset = (page - 1) * limit
    use_fts = q is not None and q.strip() != ""
    sort_by_relevance = sort == "relevansi" and use_fts

    with get_db() as conn:
        if use_fts:
            base_query = """
                FROM documents_fts
                JOIN documents d ON d.id = documents_fts.rowid
                WHERE documents_fts MATCH ?
            """
            params = [q.strip()]
        else:
            base_query = "FROM documents d WHERE 1=1"
            params = []

        if topic is not None:
            base_query += " AND EXISTS (SELECT 1 FROM document_topics dt WHERE dt.document_id = d.id AND dt.topic_id = ?)"
            params.append(topic)

        if jenis is not None:
            base_query += " AND d.jenis_dokumen = ?"
            params.append(jenis)

        if tahun is not None:
            base_query += " AND strftime('%Y', d.tanggal_terbit) = ?"
            params.append(str(tahun))

        if sort_by_relevance:
            order_clause = "ORDER BY bm25(documents_fts)"
        else:
            order_clause = "ORDER BY d.tanggal_terbit DESC"

        count_query = f"SELECT COUNT(DISTINCT d.id) {base_query}"
        total = conn.execute(count_query, params).fetchone()[0]

        data_query = f"""
            SELECT d.id, d.judul, d.nomor, d.tanggal_terbit, d.url_pdf, d.konten_text, d.jenis_dokumen
            {base_query}
            {order_clause}
            LIMIT ? OFFSET ?
        """
        data_params = params + [limit, offset]
        rows = conn.execute(data_query, data_params).fetchall()

    results = []
    with get_db() as conn:
        for row in rows:
            topic_rows = _fetch_document_topics(conn, row["id"])
            results.append({
                "id": row["id"],
                "judul": row["judul"],
                "nomor": row["nomor"],
                "tanggal_terbit": row["tanggal_terbit"],
                "jenis_dokumen": row["jenis_dokumen"],
                "url_pdf": row["url_pdf"],
                "topics": [{"id": tr["id"], "label_topik": tr["label_topik"]} for tr in topic_rows]
            })

    return {
        "data": results,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }


@router.get("/{doc_id}")
async def get_document(doc_id: int):
    with get_db() as conn:
        row = conn.execute("""
            SELECT id, judul, nomor, tanggal_terbit, url_pdf, konten_text, jenis_dokumen
            FROM documents
            WHERE id = ?
        """, (doc_id,)).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")

        topic_rows = _fetch_document_topics(conn, doc_id)

    return {
        "id": row["id"],
        "judul": row["judul"],
        "nomor": row["nomor"],
        "tanggal_terbit": row["tanggal_terbit"],
        "jenis_dokumen": row["jenis_dokumen"],
        "url_pdf": row["url_pdf"],
        "konten_text": row["konten_text"],
        "topics": [{"id": tr["id"], "label_topik": tr["label_topik"]} for tr in topic_rows]
    }