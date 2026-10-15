"""
Verifikasi: apakah server strict soal slug di /produk-hukum/{id}/{slug}?
Menguji 3028 dengan 3 varian slug.
Jalankan: python verify_slug_tolerance.py
"""
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://jdih.banyumaskab.go.id"
DOC_ID = 3028
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9",
}

VARIANTS = [
    ("slug asli", "peraturan-daerah-kabupaten-banyumas-tentang-pemberhentianpemberhentian-sementara-pegawai-daerah"),
    ("slug sembarang", "abc"),
    ("tanpa slug", ""),
]


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    return r


def cek_nomor(soup):
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 3:
            continue
        lab = re.sub(r"\s+", " ", cells[0].get_text(" ")).strip()
        if lab == "Nomor Peraturan":
            return re.sub(r"\s+", " ", cells[2].get_text(" ")).strip()
    return None


for label, slug in VARIANTS:
    url = f"{BASE}/produk-hukum/{DOC_ID}" + (f"/{slug}" if slug else "")
    r = get(url)
    s = BeautifulSoup(r.text, "html.parser")
    h1 = [h.get_text(" ", strip=True) for h in s.find_all("h1")][:3]
    print(f"[{label}]")
    print("  URL   :", url)
    print("  status:", r.status_code, "| bytes:", len(r.text), "| final:", r.url)
    print("  Nomor Peraturan terbaca:", cek_nomor(s))
    print("  h1    :", h1)
    time.sleep(2)
