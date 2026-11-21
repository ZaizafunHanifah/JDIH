import asyncio
import os
import re

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.db import get_db
from app.pdf_extractor import deteksi_metadata, ekstrak_teks

router = APIRouter(prefix="/api/v1", tags=["ekstraksi"])


def _cek_api_key(request: Request) -> None:
    expected = os.getenv("API_KEY_EKSTRAK", "")
    provided = request.headers.get("x-api-key", "")
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="API key tidak valid atau tidak tersedia")


_CTRL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def _bersihkan_nama_file(nama: str) -> str:
    if not nama:
        return ""
    return _CTRL_CHARS.sub("", nama)


def _batas_upload() -> int:
    try:
        return int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
    except ValueError:
        return 20 * 1024 * 1024


@router.post("/ekstrak")
async def ekstrak(
    request: Request,
    file: UploadFile = File(...),
    judul: str = Form(default=""),
):
    """Ekstrak teks PDF, otomatis simpan ke tabel documents.

    Hasil ekstraksi (konten_text_asli, konten_tsv) disimpan ke database
    secara otomatis. Field judul/nomor/tahun/jenis_dokumen diisi dari metadata PDF
    (jika tidak diberikan melalui form judul).
    """
    _cek_api_key(request)

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return JSONResponse(
            status_code=400,
            content={"error": "Hanya file PDF yang diperbolehkan"},
        )

    batas = _batas_upload()
    contents = await file.read(batas + 1)
    if len(contents) > batas:
        return JSONResponse(
            status_code=413,
            content={
                "error": f"File terlalu besar. Maksimum {batas // (1024 * 1024)} MB.",
            },
        )

    nama_file = _bersihkan_nama_file(file.filename or "")

    hasil = await asyncio.to_thread(ekstrak_teks, contents)

    if hasil["status"] == "rusak":
        return JSONResponse(
            status_code=422,
            content={
                "status": "gagal",
                "pesan": hasil["pesan"],
                "nama_file": nama_file,
            },
        )

    if hasil["status"] == "tanpa_teks":
        return JSONResponse(
            status_code=422,
            content={
                "status": "tanpa_teks",
                "pesan": hasil["pesan"],
                "nama_file": nama_file,
                "jumlah_halaman": hasil["jumlah_halaman"],
                "jumlah_karakter": hasil["jumlah_karakter"],
            },
        )

    teks = hasil["konten_text_asli"]
    judul_form = (judul or "").strip()

    if judul_form:
        judul_terpilih = judul_form
        sumber_judul = "form"
        metadata = deteksi_metadata(teks)
        jenis_dokumen = metadata["jenis_dokumen"]
        nomor = metadata["nomor"]
        tahun = metadata["tahun"]
    else:
        metadata = deteksi_metadata(teks)
        if metadata["judul"]:
            judul_terpilih = metadata["judul"]
            sumber_judul = "otomatis"
        else:
            judul_terpilih = None
            sumber_judul = "tidak_terdeteksi"
        jenis_dokumen = metadata["jenis_dokumen"]
        nomor = metadata["nomor"]
        tahun = metadata["tahun"]

    if sumber_judul == "form":
        tsv_input = f"{judul_terpilih} {teks}"
    else:
        tsv_input = teks

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_tsvector('simple', %s)::text", (tsv_input,))
            row = cur.fetchone()
            konten_tsv = row[0] if row else ""

    # Simpan otomatis ke database (INSERT)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents
                ( judul, nomor, tanggal_terbit, jenis_dokumen, konten_text_asli, konten_text,
                  status_hukum, catatan_relasi, nomor_tahun)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, ( judul_terpilih or "", nomor or "",
                  (f"{tahun}-01-01" if tahun else ""),
                  jenis_dokumen or "", teks,
                  re.sub(r"\s+", " ", teks).strip(),
                  None, None,
                  (f"{nomor}/{tahun}" if nomor and tahun else None)))
            new_id = cur.fetchone()[0]

    respons = {
        "status": "berhasil",
        "sumber_judul": sumber_judul,
        "judul": judul_terpilih,
        "metadata": {
            " judul": judul_terpilih,
            "sumber_judul": sumber_judul,
            "jenis_dokumen": jenis_dokumen,
            "nomor": nomor,
            "tahun": tahun,
        },
        "nama_file": nama_file,
        "jumlah_halaman": hasil["jumlah_halaman"],
        "jumlah_karakter": hasil["jumlah_karakter"],
        "konten_text_asli": teks,
        "konten_tsv": konten_tsv,
        "id": new_id,
        "disimpan": True,
    }
    return respons


@router.post("/ekstrak/simpan")
async def ekstrak_simpan(
    request: Request,
    body: dict,
):
    """Simpan hasil ekstraksi ke tabel documents.

    Body JSON contoh:
    {
        "judul": "...",
        "nomor": "48",
        "tanggal_terbit": "2020-01-01",
        "jenis_dokumen": "Peraturan Bupati",
        "konten_text_asli": "...",
        "konten_text": "...",
        "status_hukum": "Berlaku",
        "catatan_relasi": "",
        "nomor_tahun": "48/2020"
    }
    """
    _cek_api_key(request)

    judul = (body.get("judul") or "").strip()
    nomor = (body.get("nomor") or "").strip()
    tanggal_terbit = (body.get("tanggal_terbit") or "").strip()
    jenis_dokumen = (body.get("jenis_dokumen") or "").strip()
    konten_text_asli = body.get("konten_text_asli") or ""
    konten_text = (body.get("konten_text") or "").strip()
    status_hukum = (body.get("status_hukum") or "").strip()
    catatan_relasi = (body.get("catatan_relasi") or "").strip()
    nomor_tahun = (body.get("nomor_tahun") or "").strip()

    if not judul:
        raise HTTPException(status_code=400, detail="Field ' judul' wajib diisi")
    if not konten_text_asli.strip():
        raise HTTPException(status_code=400, detail="Field 'konten_text_asli' wajib diisi")

    if not konten_text:
        konten_text = re.sub(r"\s+", " ", konten_text_asli).strip()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO documents
                ( judul, nomor, tanggal_terbit, jenis_dokumen, konten_text_asli, konten_text,
                  status_hukum, catatan_relasi, nomor_tahun)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, ( judul, nomor, tanggal_terbit, jenis_dokumen, konten_text_asli,
                  konten_text, status_hukum or None, catatan_relasi or None,
                  nomor_tahun or None))
            new_id = cur.fetchone()[0]

    return {
        "status": "berhasil",
        "message": "Hasil ekstraksi tersimpan ke database",
        "id": new_id,
        " judul": judul,
        "nomor": nomor,
        "konten_text_asli_len": len(konten_text_asli),
    }
