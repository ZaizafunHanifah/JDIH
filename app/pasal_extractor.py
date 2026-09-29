import re
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import get_db


_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def _to_int(value: str) -> int:
    if value.isdigit():
        return int(value)
    result = 0
    for i in range(len(value)):
        if i + 1 < len(value) and _ROMAN[value[i]] < _ROMAN[value[i + 1]]:
            result -= _ROMAN[value[i]]
        else:
            result += _ROMAN[value[i]]
    return result


_PASAL_PATTERN = re.compile(r"Pasal\s+([IVX]+|\d+)(?=\s|\.|$)", re.IGNORECASE)

_MAX_ISI_LENGTH = 600


_LAMPIRAN_RE = re.compile(r"\bLAMPIRAN\b", re.IGNORECASE)


def is_procedural(isi_pasal: str) -> dict:
    KATA_KUNCI_PROSEDURAL = [
        "mengajukan", "melampirkan", "menyerahkan", "diterbitkan",
        "permohonan", "verifikasi", "hari kerja", "disetujui",
        "ditolak", "persyaratan", "tahapan",
    ]

    isi_lower = isi_pasal.lower()
    skor_keyword = sum(1 for kw in KATA_KUNCI_PROSEDURAL if kw in isi_lower)

    verse_matches = re.findall(r"\((\d+)\)", isi_pasal)
    ada_penomoran_ayat = False
    if len(verse_matches) >= 2:
        nums = sorted(set(int(x) for x in verse_matches))
        for i in range(len(nums) - 1):
            if nums[i + 1] == nums[i] + 1:
                ada_penomoran_ayat = True
                break

    is_procedural_flag = skor_keyword >= 2 or ada_penomoran_ayat

    return {
        "is_procedural": is_procedural_flag,
        "skor_keyword": skor_keyword,
        "ada_penomoran_ayat": ada_penomoran_ayat,
    }


_PASAL_JUDUL_PATTERN = re.compile(r"^[ \t]*Pasal[ \t]+([IVX]+|\d+)[ \t]*\.?[ \t]*$", re.IGNORECASE | re.MULTILINE)

_BAB_JUDUL_PATTERN = re.compile(r"^\s*BAB\s+[IVXLC]+\s*$", re.MULTILINE)

_MAX_LONJAT_NOMOR = 5


def _bangun_hasil_pasal(after: str, valid: list[re.Match]) -> list[dict]:
    result = []
    for i, m in enumerate(valid):
        nomor = _to_int(m.group(1))
        start = m.end()
        if i + 1 < len(valid):
            end = valid[i + 1].start()
        else:
            end = len(after)
        isi_penuh = after[start:end].strip()
        lampiran = _LAMPIRAN_RE.search(isi_penuh)
        if lampiran:
            isi_penuh = isi_penuh[:lampiran.start()].strip()

        bab = _BAB_JUDUL_PATTERN.search(isi_penuh)
        if bab:
            isi_penuh = isi_penuh[:bab.start()].strip()

        prosedural = is_procedural(isi_penuh)

        terpotong = False
        isi_tampilan = isi_penuh
        if len(isi_penuh) > _MAX_ISI_LENGTH:
            truncated = isi_penuh[:_MAX_ISI_LENGTH]
            last_space = truncated.rfind(" ")
            if last_space > 0:
                truncated = truncated[:last_space]
            isi_tampilan = truncated + " ... (dipotong, baca selengkapnya di dokumen lengkap)"
            terpotong = True

        result.append({
            "nomor_pasal": nomor,
            "isi_pasal": isi_tampilan,
            "isi_penuh": isi_penuh,
            "terpotong": terpotong,
            "is_procedural": prosedural["is_procedural"],
            "skor_keyword": prosedural["skor_keyword"],
            "ada_penomoran_ayat": prosedural["ada_penomoran_ayat"],
        })

    return result


def extract_pasal_v1(konten_mentah: str) -> list[dict]:
    match = re.search(r"MEMUTUSKAN", konten_mentah, re.IGNORECASE)
    if not match:
        return []

    after = konten_mentah[match.end():]

    matches = list(_PASAL_PATTERN.finditer(after))

    if not matches:
        return []

    valid = []
    expected = 1
    for m in matches:
        num = _to_int(m.group(1))
        if num == expected:
            valid.append(m)
            expected += 1

    return _bangun_hasil_pasal(after, valid)


def extract_pasal_v2(konten_mentah: str) -> list[dict]:
    match = re.search(r"MEMUTUSKAN", konten_mentah, re.IGNORECASE)
    if not match:
        return []

    after = konten_mentah[match.end():]

    matches = list(_PASAL_JUDUL_PATTERN.finditer(after))

    if not matches:
        return []

    valid = []
    last_num = 0
    for m in matches:
        num = _to_int(m.group(1))
        if num > last_num and (num - last_num) <= _MAX_LONJAT_NOMOR:
            valid.append(m)
            last_num = num

    return _bangun_hasil_pasal(after, valid)


extract_pasal = extract_pasal_v2


if __name__ == "__main__":
    with get_db() as conn:
        rows = conn.execute(
            "SELECT judul, konten_text_asli FROM documents WHERE konten_text_asli IS NOT NULL LIMIT 5"
        ).fetchall()

        first_result = None
        for row in rows:
            judul = row["judul"][:60]
            pasals = extract_pasal(row["konten_text_asli"])
            if pasals:
                first_nomor = pasals[0]["nomor_pasal"]
                last_nomor = pasals[-1]["nomor_pasal"]
                print(f"Judul: {judul}...")
                print(f"  Jumlah pasal ditemukan: {len(pasals)}")
                print(f"  Pasal pertama: {first_nomor}, Pasal terakhir: {last_nomor}")
            else:
                print(f"Judul: {judul}...")
                print(f"  Jumlah pasal ditemukan: 0")
                print(f"  Pasal pertama: -, Pasal terakhir: -")

            if first_result is None:
                first_result = pasals

        if first_result:
            print("\n--- is_procedural untuk dokumen pertama ---")
            for p in first_result:
                print(
                    f"  Pasal {p['nomor_pasal']}: "
                    f"is_procedural={p['is_procedural']}, "
                    f"skor_keyword={p['skor_keyword']}, "
                    f"ada_penomoran_ayat={p['ada_penomoran_ayat']}, "
                    f"terpotong={p['terpotong']}"
                )
