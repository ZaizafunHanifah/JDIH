from fastapi import APIRouter

from app.db import get_db

router = APIRouter(prefix="/api/status-hukum", tags=["status_hukum"])


@router.get("")
async def daftar_status_hukum():
    """Kembalikan daftar status_hukum unik yang ada di database beserta
    jumlah dokumennya. Dokumen dengan status_hukum NULL TIDAK dihitung."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT status_hukum, COUNT(*) AS jumlah
            FROM documents
            WHERE status_hukum IS NOT NULL AND TRIM(status_hukum) <> ''
            GROUP BY status_hukum
            ORDER BY jumlah DESC
        """).fetchall()

    return {
        "data": [
            {"status": r["status_hukum"], "jumlah": r["jumlah"]}
            for r in rows
        ],
        "total_status": len(rows),
        "total_dokumen_terfilter": sum(r["jumlah"] for r in rows),
    }