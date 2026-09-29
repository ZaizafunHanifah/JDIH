SINONIM: dict[str, list[str]] = {
    "mengurus": ["permohonan", "pengajuan", "mengurus", "mengaju"],
    "mengajukan": ["permohonan", "pengajuan", "mengurus", "mengaju"],
    "memohon": ["permohonan", "pengajuan", "mengurus", "mengaju"],
    "bayar": ["pembayaran", "penyetoran", "membayar"],
    "membayar": ["pembayaran", "penyetoran", "membayar"],
    "daftar": ["pendaftaran", "mendaftar"],
    "mendaftar": ["pendaftaran", "mendaftar"],
    "gaji": ["penghasilan", "tunjangan"],
    "izin": ["perizinan", "izin"],
}


def sinonim_dari(keyword: str) -> list[str]:
    """Seluruh bentuk kata yang dianggap memenuhi satu keyword.

    Mengembalikan kata aslinya lebih dulu, lalu sinonimnya (tanpa duplikat).
    """
    kata = keyword.lower()
    hasil = [kata]
    for s in SINONIM.get(kata, []):
        if s not in hasil:
            hasil.append(s)
    return hasil
