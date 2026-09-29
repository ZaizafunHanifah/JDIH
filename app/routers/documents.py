import math
import re

from fastapi import APIRouter, Query, HTTPException
from app.db import get_db
from app.pasal_extractor import extract_pasal
from app.synonyms import sinonim_dari

router = APIRouter(prefix="/api/documents", tags=["documents"])

_COMMON_WORDS = {"cara", "bagaimana", "yang", "untuk", "dengan", "dari", "pada"}


def _fts5_match_params(query_text: str, limit: int | None = None, pakai_sinonim: bool = True):
    match_str = _fts5_match_string(query_text, pakai_sinonim=pakai_sinonim)
    sql = """
        SELECT d.id, d.judul, d.nomor, substr(d.tanggal_terbit,1,4) as tahun, d.url_pdf, d.konten_text_asli
        FROM documents_fts
        JOIN documents d ON d.id = documents_fts.rowid
        WHERE documents_fts MATCH ?
        ORDER BY bm25(documents_fts)
    """
    if limit:
        sql += " LIMIT ?"
    return sql, [match_str, limit] if limit else [match_str]


def _fts5_match_string(query_text: str, pakai_sinonim: bool = True) -> str:
    """Bangun query FTS5.

    Tanpa sinonim: tiap keyword dibungkus tanda kutip (AND antarkeyword).
    Dengan sinonim: tiap keyword jadi grup (syn1 OR syn2 OR ...), AND antarkeyword.
    """
    keywords = _extract_main_keywords(query_text)
    if not keywords:
        semua_kata = [w for w in query_text.strip().split() if len(w) > 1]
        return " ".join(semua_kata)

    grup = []
    for kw in keywords:
        kata_kunci = sinonim_dari(kw) if pakai_sinonim else [kw]
        if len(kata_kunci) == 1:
            grup.append('"{}"'.format(kata_kunci[0]))
        else:
            grup.append("(" + " OR ".join('"{}"'.format(k) for k in kata_kunci) + ")")

    return " AND ".join(grup)


_QUESTION_WORDS = {"bagaimana", "dimana", "apakah", "kenapa", "mengapa"}


def _extract_main_keywords(query_text: str) -> list[str]:
    stop = _COMMON_WORDS | {"dan", "atau"} | _QUESTION_WORDS
    keywords = []
    for w in query_text.strip().split():
        w_clean = re.sub(r"[^\w]", "", w).lower()
        if len(w_clean) > 3 and w_clean not in stop:
            keywords.append(w_clean)
    return keywords


_AFFIX_PREFIXES = ("meng", "mem", "men", "pem", "pen", "ber", "ter", "di", "pe", "me")


def _strip_prefix(word: str) -> str:
    if len(word) <= 4:
        return word
    for prefix in sorted(_AFFIX_PREFIXES, key=len, reverse=True):
        if word.startswith(prefix) and len(word) - len(prefix) >= 4:
            return word[len(prefix):]
    return word


_AFFIX_SUFFIXES = ("nya", "kan", "an", "i")


def _strip_affixes(word: str) -> str:
    """Lepas awalan lalu akhiran (kan|an|i|nya) selama sisa >= 4 huruf."""
    stem = _strip_prefix(word)
    berubah = True
    while berubah and len(stem) >= 4:
        berubah = False
        for suf in _AFFIX_SUFFIXES:
            if stem.endswith(suf) and len(stem) - len(suf) >= 4:
                stem = stem[: -len(suf)]
                berubah = True
                break
    return stem


def _keyword_pattern(keyword: str) -> re.Pattern:
    stem = _strip_affixes(keyword)
    if len(stem) < 4:
        return re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
    return re.compile(
        r"\b(?:me|mem|men|meng|di|pe|pem|pen|ber|ter)?" + re.escape(stem) + r"(?:kan|an|i|nya)?\b",
        re.IGNORECASE,
    )


def _keyword_patterns(keyword: str, pakai_sinonim: bool = True) -> re.Pattern:
    """Pola gabungan keyword asli + seluruh sinonimnya (OR)."""
    kata_kunci = sinonim_dari(keyword) if pakai_sinonim else [keyword]
    if len(kata_kunci) == 1:
        return _keyword_pattern(kata_kunci[0])
    return re.compile(
        "|".join(f"(?:{_keyword_pattern(k).pattern})" for k in kata_kunci),
        re.IGNORECASE,
    )


def _pasal_memenuhi_keyword(keyword_pats: list[tuple[str, re.Pattern]], isi_pasal: str) -> tuple[bool, list[str], list[str]]:
    if not keyword_pats:
        return False, [], []
    found = [kw for kw, pat in keyword_pats if pat.search(isi_pasal)]
    missing = [kw for kw, pat in keyword_pats if not pat.search(isi_pasal)]

    threshold = 0.75 if len(keyword_pats) > 3 else 1.0
    needed = math.ceil(len(keyword_pats) * threshold)

    return len(found) >= needed, found, missing


_DEFINISI_FRASA = re.compile(r"yang\s+dimaksud\s+dengan", re.IGNORECASE)
_DEFINISI_AWAL = re.compile(r"^\s*Dalam\s+Peraturan\b", re.IGNORECASE)
_MAKSUD_AWAL = re.compile(
    r"^\s*(?:\(\s*1\s*\))?\s*(Maksud|Tujuan|Ruang\s+lingkup|Asas|Sasaran)\b",
    re.IGNORECASE,
)

_MAKS_PASAL_TAMPIL = 8


def _is_pasal_definisi(pasal: dict) -> bool:
    isi_penuh = pasal.get("isi_penuh") or ""
    if _DEFINISI_FRASA.search(isi_penuh[:300]):
        return True
    if pasal.get("nomor_pasal") == 1 and _DEFINISI_AWAL.match(isi_penuh):
        return True
    if _MAKSUD_AWAL.match(isi_penuh[:120]):
        return True
    return False


_PERUBAHAN_JUDUL = re.compile(r"Perubahan", re.IGNORECASE)
_PERUBAHAN_AWAL = re.compile(r"^\s*Beberapa\s+ketentuan\s+dalam\s+Peraturan\b", re.IGNORECASE)
_PERUBAHAN_AWAL2 = re.compile(r"diubah\s+sebagai\s+berikut", re.IGNORECASE)


def _is_dokumen_perubahan(judul: str, valid_pasals: list[dict]) -> bool:
    if judul and _PERUBAHAN_JUDUL.search(judul):
        return True

    pasal_pertama = next((p for p in valid_pasals if p["nomor_pasal"] == 1), None)
    if pasal_pertama is not None:
        isi_penuh = pasal_pertama["isi_penuh"].lstrip()[:200]
        if _PERUBAHAN_AWAL.match(isi_penuh) or _PERUBAHAN_AWAL2.search(isi_penuh):
            return True

    return False


def _cari_pasal_relevan(doc_row, keywords: list[str], pakai_sinonim: bool = True):
    valid_pasals = extract_pasal(doc_row["konten_text_asli"])
    if not valid_pasals:
        return None, []

    keyword_pats = [(kw, _keyword_patterns(kw, pakai_sinonim=pakai_sinonim)) for kw in keywords]

    lolos = []
    for p in valid_pasals:
        if not p["is_procedural"]:
            continue
        if _is_pasal_definisi(p):
            continue
        ok, _found, _missing = _pasal_memenuhi_keyword(keyword_pats, p["isi_penuh"])
        if ok:
            lolos.append(p)

    return lolos, valid_pasals


def _fetch_document_topics(conn, doc_id: int):
    return conn.execute("""
        SELECT t.id, t.label_topik
        FROM topics t
        JOIN document_topics dt ON t.id = dt.topic_id
        WHERE dt.document_id = ?
        ORDER BY t.id
    """, (doc_id,)).fetchall()


def get_prosedur_untuk_dokumen(doc_row):
    if not doc_row["konten_text_asli"] or not doc_row["konten_text_asli"].strip():
        return {"status": "tidak_ada_teks", "pesan": "Dokumen ini belum memiliki teks mentah yang dapat diproses"}

    valid_pasals = extract_pasal(doc_row["konten_text_asli"])

    if not valid_pasals:
        return {"status": "tidak_ditemukan_pasal", "pesan": "Tidak ditemukan struktur pasal yang jelas dalam dokumen ini"}

    total_pasals = len(valid_pasals)
    procedural_pasals = [p for p in valid_pasals if p["is_procedural"]]

    if not procedural_pasals:
        return {
            "status": "tidak_ditemukan_prosedur",
            "pesan": "Ditemukan struktur pasal, tapi tidak ada yang teridentifikasi sebagai tata cara/prosedur",
            "jumlah_pasal_total": total_pasals,
        }

    return {
        "status": "ditemukan",
        "jumlah_pasal_total": total_pasals,
        "pasal_prosedural": [
            {
                "nomor_pasal": p["nomor_pasal"],
                "isi_pasal": p["isi_pasal"],
                "skor_keyword": p["skor_keyword"],
                "terpotong": p["terpotong"],
            }
            for p in procedural_pasals
        ],
    }


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
            params = [_fts5_match_string(q.strip())]
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
            SELECT d.id, d.judul, d.nomor, d.tanggal_terbit, d.url_pdf, d.konten_text, d.konten_text_asli, d.jenis_dokumen
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
            doc_result = {
                "id": row["id"],
                "judul": row["judul"],
                "nomor": row["nomor"],
                "tanggal_terbit": row["tanggal_terbit"],
                "jenis_dokumen": row["jenis_dokumen"],
                "url_pdf": row["url_pdf"],
                "topics": [{"id": tr["id"], "label_topik": tr["label_topik"]} for tr in topic_rows]
            }
            if total <= 3:
                doc_result["prosedur"] = get_prosedur_untuk_dokumen(row)
            else:
                doc_result["prosedur"] = None
            results.append(doc_result)

    return {
        "data": results,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }


@router.get("/{doc_id}/prosedur")
async def get_document_prosedur(doc_id: int):
    with get_db() as conn:
        row = conn.execute("""
            SELECT id, judul, nomor, tanggal_terbit, url_pdf, konten_text_asli, jenis_dokumen
            FROM documents
            WHERE id = ?
        """, (doc_id,)).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")

    return get_prosedur_untuk_dokumen(row)


@router.get("/tata-cara")
async def tata_cara(q: str = Query(..., description="Pertanyaan tentang tata cara/prosedur")):
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Pertanyaan tidak boleh kosong")

    keywords = _extract_main_keywords(q)
    if not keywords:
        return {
            "status": "tidak_ditemukan",
            "pesan": "Tidak ditemukan tata cara yang relevan dengan pertanyaan ini di dokumen yang tersedia."
        }

    hasil = _cari_tahap(q, keywords, pakai_sinonim=False)
    diperluas = False
    if hasil is None:
        hasil = _cari_tahap(q, keywords, pakai_sinonim=True)
        diperluas = hasil is not None

    if hasil is None:
        return {
            "status": "tidak_ditemukan",
            "pesan": "Tidak ditemukan tata cara yang relevan dengan pertanyaan ini di dokumen yang tersedia."
        }

    row, lolos, valid_pasals, dokumen_perubahan = hasil

    if dokumen_perubahan:
        return {
            "status": "hanya_dokumen_perubahan",
            "pesan": "Tidak ditemukan tata cara langsung. Dokumen terkait berikut adalah peraturan perubahan.",
            "diperluas_sinonim": diperluas,
            "dokumen_perubahan": True,
            "dokumen": {
                "id": row["id"],
                "judul": row["judul"],
                "nomor": row["nomor"],
                "tahun": row["tahun"],
                "url_pdf": row["url_pdf"],
            },
        }

    return {
        "status": "ditemukan",
        "diperluas_sinonim": diperluas,
        "dokumen_perubahan": dokumen_perubahan,
        "dokumen": {
            "id": row["id"],
            "judul": row["judul"],
            "nomor": row["nomor"],
            "tahun": row["tahun"],
            "url_pdf": row["url_pdf"],
        },
        "prosedur": {
            "status": "ditemukan",
            "jumlah_pasal_total": len(valid_pasals),
            "jumlah_pasal_relevan": len(lolos),
            "pasal_prosedural": [
                {
                    "nomor_pasal": p["nomor_pasal"],
                    "isi_pasal": p["isi_pasal"],
                    "skor_keyword": p["skor_keyword"],
                    "terpotong": p["terpotong"],
                }
                for p in lolos[:_MAKS_PASAL_TAMPIL]
            ],
        },
    }


def _cari_tahap(q: str, keywords: list[str], pakai_sinonim: bool):
    """Cari dokumen non-perubahan yang punya minimal 1 pasal lolos.

    Kandidat perubahan hanya dipakai bila tidak ada kandidat non-perubahan
    yang lolos di tahap ini. None bila tidak ada hasil sama sekali.
    """
    fts_sql, fts_params = _fts5_match_params(q, limit=10, pakai_sinonim=pakai_sinonim)

    with get_db() as conn:
        candidates = conn.execute(fts_sql, fts_params).fetchall()

    hasil_perubahan = None

    for row in candidates:
        if not row["konten_text_asli"] or not row["konten_text_asli"].strip():
            continue
        lolos, valid_pasals = _cari_pasal_relevan(row, keywords, pakai_sinonim=pakai_sinonim)
        if not lolos:
            continue
        perubahan = _is_dokumen_perubahan(row["judul"], valid_pasals)
        if not perubahan:
            return row, lolos, valid_pasals, False
        if hasil_perubahan is None:
            hasil_perubahan = (row, lolos, valid_pasals, True)

    return hasil_perubahan


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