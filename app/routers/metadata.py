from fastapi import APIRouter
from app.db import get_db

router = APIRouter(prefix="/api", tags=["metadata"])


@router.get("/jenis-dokumen")
async def get_jenis_dokumen():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT jenis_dokumen as jenis, COUNT(*) as jumlah
            FROM documents
            GROUP BY jenis_dokumen
            ORDER BY jumlah DESC
        """).fetchall()

    return [{"jenis": row["jenis"], "jumlah": row["jumlah"]} for row in rows]


@router.get("/tahun")
async def get_tahun():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DISTINCT strftime('%Y', tanggal_terbit) as tahun
            FROM documents
            ORDER BY tahun DESC
        """).fetchall()

    return [int(row["tahun"]) for row in rows]