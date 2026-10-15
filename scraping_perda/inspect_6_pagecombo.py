"""
Verifikasi kombinasi parameter: ?page=N&per_page=M (underscore)
Cek apakah page=2 benar-benar menghasilkan ID berbeda.
Hanya inspecting listing, tidak membuka detail dokumen.

Jalankan: python inspect_6_pagecombo.py
"""
import re
import sys
import time

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


def ids_of(soup):
    ids = []
    for tb in soup.find_all("table"):
        if not tb.find_all("th"):
            continue
        for tr in tb.find_all("tr"):
            tds = tr.find_all("td")
            if not tds:
                continue
            for a in tr.find_all("a", href=True):
                m = re.search(r"/produk-hukum/(\d+)/", a["href"])
                if m:
                    ids.append(int(m.group(1)))
                    break
        if ids:
            break
    return ids


def main():
    print("Uji kombinasi ?page=N&per_page=M (underscore)")
    print("=" * 60)
    a = get(LIST + "/1995?page=1&per_page=50")
    ia = ids_of(BeautifulSoup(a.text, "html.parser"))
    print("page=1&per_page=50 ->", len(ia), "baris | id unik:", len(set(ia)))

    time.sleep(2)
    b = get(LIST + "/1995?page=2&per_page=50")
    ib = ids_of(BeautifulSoup(b.text, "html.parser"))
    print("page=2&per_page=50 ->", len(ib), "baris | id unik:", len(set(ib)))
    print("  id sama dgn page1?", set(ia) == set(ib))
    print("  id baru:", sorted(set(ib) - set(ia))[:10])

    time.sleep(2)
    c = get(LIST + "/2020?per_page=50")
    ic = ids_of(BeautifulSoup(c.text, "html.parser"))
    print("\n2020?per_page=50 ->", len(ic), "baris | id unik:", len(set(ic)),
          "| pagination:", bool(BeautifulSoup(c.text, "html.parser").find("ul", class_="pagination")))


if __name__ == "__main__":
    main()
