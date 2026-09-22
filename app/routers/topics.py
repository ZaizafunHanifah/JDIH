from fastapi import APIRouter
from app.db import get_db

router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.get("")
async def get_topics():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT t.id, t.label_topik, t.top_keywords,
                   COUNT(dt.document_id) as jumlah_dokumen
            FROM topics t
            LEFT JOIN document_topics dt ON t.id = dt.topic_id
            GROUP BY t.id, t.label_topik, t.top_keywords
            ORDER BY t.id
        """).fetchall()

    return [
        {
            "id": row["id"],
            "label_topik": row["label_topik"],
            "top_keywords": row["top_keywords"],
            "jumlah_dokumen": row["jumlah_dokumen"]
        }
        for row in rows
    ]