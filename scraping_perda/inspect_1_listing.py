"""
TUGAS 1 - Langkah 1: Inspeksi halaman daftar Peraturan Daerah.
Tujuan: memastikan apakah halaman berisi grid tahun + jumlah dokumen,
dan menemukan pola URL untuk masuk ke tahun tertentu.

Jalankan: python inspect_1_listing.py
"""
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://jdih.banyumaskab.go.id"
URL_LIST = BASE + "/produk-hukum/jenis/produk-hukum-daerah/peraturan-daerah"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9",
}


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=45)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r


def main():
    print("=" * 78)
    print("STEP 1 - HALAMAN DAFTAR PERATURAN DAERAH")
    print("=" * 78)
    resp = get(URL_LIST)
    soup = BeautifulSoup(resp.text, "html.parser")
    print("URL   :", URL_LIST)
    print("Status:", resp.status_code, "| bytes:", len(resp.text))

    # --- 1a. Cari link yang mengandung "/peraturan-daerah/" ---
    print("\n--- 1a. Semua link unik yang mengandung '/peraturan-daerah/' ---")
    seen = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "/peraturan-daerah" not in href:
            continue
        label = " ".join(a.get_text(" ", strip=True).split())
        full = urljoin(BASE + "/", href)
        seen.setdefault(full, set()).add(label)
    for full, labels in sorted(seen.items()):
        lab = " | ".join(sorted(x for x in labels if x))[:90]
        print(f"{full}\n    label: {lab!r}")

    # --- 1b. Deteksi grid tahun (tautan tahun 4 digit) ---
    print("\n--- 1b. Deteksi grid tahun (anchor teks = 4 digit, atau href berisi /20xx) ---")
    year_hits = []
    for a in soup.find_all("a", href=True):
        label = " ".join(a.get_text(" ", strip=True).split())
        href = a["href"].strip()
        m_label = re.fullmatch(r"(19|20)\d{2}", label)
        m_href = re.search(r"/((?:19|20)\d{2})(?:[/?#]|$)", href)
        if m_label or m_href:
            year_hits.append((m_label.group(0) if m_label else m_href.group(1), label, urljoin(BASE + "/", href)))
    for y, lab, full in year_hits:
        print(f"tahun={y!r:>8}  label={lab!r:<30} -> {full}")
    print(f"total kandidat tahun: {len(year_hits)}")

    # --- 1c. Cari elemen yang memuat angka dalam kurung -> "2020 (12)" ---
    print("\n--- 1c. Teks berpola 'tahun (jumlah)' di seluruh halaman ---")
    txt = soup.get_text("\n", strip=True)
    found = re.findall(r"((?:19|20)\d{2})\s*[(\-–]\s*(\d+)\s*[)\]]", txt)
    print("pola '(tahun (jumlah))':", found[:60])
    found2 = re.findall(r"((?:19|20)\d{2})\s*(\d+)\s*(?:Dokumen|dokumen|Produk)", txt)
    print("pola 'tahun jumlah Dokumen':", found2[:60])

    # --- 1d. Elemen parent dari kandidat tahun pertama (konteks visual) ---
    if year_hits:
        y, lab, full = year_hits[0]
        print(f"\n--- 1d. Konteks HTML untuk kandidat tahun pertama ({y}) ---")
        node = None
        for a in soup.find_all("a", href=True):
            if " ".join(a.get_text(" ", strip=True).split()) == lab and y in a["href"]:
                node = a
                break
        if node is not None:
            block = node.find_parent(["li", "div", "td", "a"])
            for _ in range(2):
                if block and block.find_parent(["li", "div", "td"]):
                    block = block.find_parent(["li", "div", "td"])
            print(block.prettify()[:1500] if block else node.prettify()[:1500])

    # --- 1e. Blok konten utama / tabel yang mungkin sudah ada ---
    print("\n--- 1e. Ringkasan elemen utama halaman ---")
    print("judul <h1..h3>:")
    for h in soup.find_all(["h1", "h2", "h3"]):
        t = " ".join(h.get_text(" ", strip=True).split())
        if t:
            print(f"   <{h.name}> {t[:100]}")
    print("tabel:", len(soup.find_all("table")))
    print("form/select (filter):")
    for sel in soup.find_all("select"):
        print("   select name=", sel.get("name"), "id=", sel.get("id"))
        for o in sel.find_all("option")[:15]:
            print("      option:", o.get("value"), "|", o.get_text(strip=True))
    for f in soup.find_all("form"):
        print("   form action=", f.get("action"), "method=", f.get("method"), "id=", f.get("id"))

    # --- 1f. Skrip yang/wp-json/ajax shrinkage untuk data dinamis ---
    print("\n--- 1f. Indikasi endpoint data dinamis ---")
    for pat in [r"/wp-json/[^'\"\s]+", r"/api/[^'\"\s]{0,60}", r"admin-ajax\.php[^'\"\s]*", r"\?s=", r"page=\d+", r"posts_per_page"]:
        hits = sorted(set(re.findall(pat, resp.text)))[:12]
        if hits:
            print(f"   {pat} -> {hits}")

    time.sleep(1.5)


if __name__ == "__main__":
    main()
