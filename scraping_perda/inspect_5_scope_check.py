"""
TUGAS 1b - Verifikasi 2 hal:
  A) Apakah ?per-page=50 benar-benar IncreaseROWS per halaman
     (hanya 1 request, tahun 1995, tanpa membuka detail dokumen)
  B) Refresh angka grid tahun 2020-2026 untuk konfirmasi scope.

Jalankan: python inspect_5_scope_check.py
"""
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://jdih.banyumaskab.go.id"
LIST = BASE + "/produk-hukum/jenis/peraturan-perundang-undangan/peraturan-daerah"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9",
}


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    return r


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def rows_of(soup):
    for tb in soup.find_all("table"):
        if tb.find_all("th"):
            return [tr for tr in tb.find_all("tr") if tr.find_all("td")]
    return []


def main():
    print("=" * 78)
    print("A) UJI ?per-page=50 (apakah benar-benar 50 baris)")
    print("=" * 78)
    url = LIST + "/1995?per-page=50"
    print("URL   :", url)
    r = get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    rows = rows_of(soup)
    print("Status:", r.status_code, "| baris:", len(rows))
    pag = soup.find("ul", class_="pagination")
    print("Pagination:", norm(pag.get_text(" ")) if pag else "(tidak ada)")
    # cek juga bentuk underscore
    time.sleep(2)
    url2 = LIST + "/1995?per_page=50"
    r2 = get(url2)
    s2 = BeautifulSoup(r2.text, "html.parser")
    print("\nURL   :", url2)
    print("Status:", r2.status_code, "| baris:", len(rows_of(s2)))
    pag2 = s2.find("ul", class_="pagination")
    print("Pagination:", norm(pag2.get_text(" ")) if pag2 else "(tidak ada)")

    print("\n" + "=" * 78)
    print("B) REFRESH GRID TAHUN 2020-2026")
    print("=" * 78)
    time.sleep(2)
    r3 = get(LIST)
    s3 = BeautifulSoup(r3.text, "html.parser")
    grid = {}
    for a in s3.find_all("a", href=True):
        lab = norm(a.get_text(" "))
        m = re.fullmatch(r"Tahun\s+((?:19|20)\d{2})\s+(\d+)", lab)
        if m:
            grid[int(m.group(1))] = int(m.group(2))
    scope = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
    print(f"Total tahun di grid: {len(grid)} (rentang {min(grid)}-{max(grid)})")
    print("\nTahun  | Dokumen")
    print("-------+---------")
    total = 0
    for y in scope:
        c = grid.get(y, 0)
        total += c
        print(f"  {y} | {c}")
    print("-------+---------")
    print(f"TOTAL  | {total}")
    print("\nJumlah tahun 2021 di grid:", grid.get(2021, "TIDAK ADA"))
    print("Tahun dalam scope yang tidak ada di grid:",
          [y for y in scope if y not in grid] or "tidak ada")


if __name__ == "__main__":
    main()
