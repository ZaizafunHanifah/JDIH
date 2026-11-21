import io
import re

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - tergantung ketersediaan paket
    PdfReader = None

_MAX_AWAL = 4000

_TERMINATOR = r"(?:\s+dengan\s+rahmat|\s+menimbang)"

_POLA_PERATURAN = re.compile(
    r"(?:perubahan\s+atas\s+)?"
    r"peraturan\s+(bupati|daerah)"
    r"(?:\s+(.*?))?"
    r"\s*nomor\s+(\d+)\s*tahun\s*(\d{4})\s*tentang\s+(.*?)"
    + _TERMINATOR,
    re.IGNORECASE,
)


def ekstrak_teks(sumber) -> dict:
    """
    sumber: str (path file PDF) atau bytes (isi file PDF dalam memori).

    Mengembalikan dict dengan kunci:
        konten_text_asli (str), jumlah_halaman (int), jumlah_karakter (int),
        status ("ok" | "tanpa_teks" | "rusak"), pesan (str)

    Tidak melempar exception ke luar: kesalahan pembacaan PDF ditangkap dan
    ditandai dengan status "rusak". PDF tanpa teks diekstrak ditandai
    "tanpa_teks" (misal scan/gambar).
    """
    if PdfReader is None:
        return {
            "konten_text_asli": "",
            "jumlah_halaman": 0,
            "jumlah_karakter": 0,
            "status": "rusak",
            "pesan": "pypdf tidak terpasang",
        }

    try:
        if isinstance(sumber, (bytes, bytearray)):
            reader = PdfReader(io.BytesIO(bytes(sumber)))
        else:
            reader = PdfReader(sumber)
    except Exception:
        return {
            "konten_text_asli": "",
            "jumlah_halaman": 0,
            "jumlah_karakter": 0,
            "status": "rusak",
            "pesan": "PDF tidak bisa dibaca (rusak/terenkripsi)",
        }

    jumlah_halaman = 0
    parts = []
    try:
        jumlah_halaman = len(reader.pages)
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or "")
            except Exception:
                parts.append("")
    except Exception:
        return {
            "konten_text_asli": "",
            "jumlah_halaman": jumlah_halaman,
            "jumlah_karakter": 0,
            "status": "rusak",
            "pesan": "Gagal mengekstrak teks dari salah satu halaman",
        }

    teks = "\n".join(parts)
    jumlah_karakter = len(teks)

    if not teks or not teks.strip():
        return {
            "konten_text_asli": teks,
            "jumlah_halaman": jumlah_halaman,
            "jumlah_karakter": jumlah_karakter,
            "status": "tanpa_teks",
            "pesan": "Tidak ada teks yang diekstrak (kemungkinan PDF scan/gambar)",
        }

    return {
        "konten_text_asli": teks,
        "jumlah_halaman": jumlah_halaman,
        "jumlah_karakter": jumlah_karakter,
        "status": "ok",
        "pesan": "OK",
    }


def deteksi_metadata(teks: str) -> dict:
    """
    Deteksi judul, jenis_dokumen, nomor, dan tahun dari ~4.000 karakter pertama
    teks hasil ekstraksi PDF.

    Mengembalikan dict {judul, jenis_dokumen, nomor, tahun} dengan masing-masing
    str atau None. Tidak melempar error; jika pola tidak ketemu semua None.

    Aturan:
    - Hanya memindai 4.000 karakter pertama (hindari tangkapan dari Mengingat/isi pasal).
    - Pola: PERATURAN (BUPATI|DAERAH) [daerah] NOMOR <n> TAHUN <yyyy> TENTANG
      <judul> [berhenti sebelum "DENGAN RAHMAT", "Menimbang", atau "BUPATI BANYUMAS,"].
      Case-insensitive, whitespace (termasuk baris baru) dinormalisasi jadi satu spasi.
    - Format judul diambil dari yang benar-benar tertulis di sumber (tidak diarang,
      misal kata "Banyumas" hanya diikutkan jika ada di teks).
    - Dokumen perubahan ("PERUBAHAN ATAS ...") dan Perda ikut terbaca.
    """
    hasil = {"judul": None, "jenis_dokumen": None, "nomor": None, "tahun": None}

    if not teks:
        return hasil

    awalan = teks[:_MAX_AWAL]
    norm = re.sub(r"\s+", " ", awalan)

    m = _POLA_PERATURAN.search(norm)
    if not m:
        return hasil

    jenis = (m.group(1) or "").strip()
    daerah = (m.group(2) or "").strip()
    nomor = (m.group(3) or "").strip()
    tahun = (m.group(4) or "").strip()
    tentang = (m.group(5) or "").strip()
    tentang = re.sub(r"\s+", " ", tentang).strip()
    tentang = tentang.strip(" ,.;:-")

    jenis_dokumen = None
    if jenis.lower() == "bupati":
        jenis_dokumen = "Peraturan Bupati"
    elif jenis.lower() == "daerah":
        jenis_dokumen = "Peraturan Daerah"

    judul_parts = []
    prefix = m.group(0)
    if re.match(r"\s*perubahan\s+atas\s+", prefix, re.IGNORECASE):
        judul_parts.append("Perubahan Atas")
    if jenis_dokumen:
        judul_parts.append(jenis_dokumen)
    if daerah:
        judul_parts.append(daerah)
    judul_parts.append(f"Nomor {nomor} Tahun {tahun} Tentang {tentang}")
    judul = " ".join(judul_parts)

    return {
        "judul": judul,
        "jenis_dokumen": jenis_dokumen,
        "nomor": nomor,
        "tahun": tahun,
    }
