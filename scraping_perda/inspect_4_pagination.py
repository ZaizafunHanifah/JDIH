"""
TUGAS 1b - Cek pagination pada tahun 1995 (46 dokumen).
Tidak melakukan scraping dokumen, hanya inspeksi struktur.

Jalankan: python inspect_4_pagination.py
"""
import re
import sys
import time
from urllib.parse import urljoin, urlparse, parse_qsl

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://jdih.banyumaskab.go.id"
YEAR = 1995
URL = f"{BASE}/produk-hukum/jenis/peraturan-perundang-undangan/peraturan-daerah/{YEAR}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9",
    "Referer": BASE + "/",
}


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    return r


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def data_table(soup):
    for tb in soup.find_all("table"):
        if tb.find_all("th"):
            return tb
    return None


def count_rows(soup):
    tb = data_table(soup)
    if tb is None:
        return 0, None, []
    rows = [tr for tr in tb.find_all("tr") if tr.find_all("td")]
    ids = []
    for tr in rows:
        for a in tr.find_all("a", href=True):
            m = re.search(r"/produk-hukum/(\d+)/", a["href"])
            if m:
                ids.append(int(m.group(1)))
                break
    return len(rows), [norm(th.get_text(" ")) for th in tb.find_all("th")], ids


def main():
    print("=" * 78)
    print(f"PAGINATION CHECK - TAHUN {YEAR} (klaim 46 dokumen)")
    print("=" * 78)
    print("URL:", URL)
    r = get(URL)
    soup = BeautifulSoup(r.text, "html.parser")
    print("Status:", r.status_code, "| bytes:", len(r.text))

    n, headers, ids = count_rows(soup)
    print(f"\nBaris data di halaman ini : {n}")
    print("Kolom                    :", headers)
    print("Jumlah ID unik            :", len(set(ids)))

    # --- Deteksi teks pagination ---
    txt = soup.get_text("\n", strip=True)
    print("\n--- Elemen pagination (kelas nav/ul pagination) ---")
    found_pag = False
    for el in soup.find_all(["ul", "nav", "div", "a", "span", "select", "form"]):
        cls = " ".join(el.get("class") or []) if el.name != "a" else ""
        ident = el.get("id") or ""
        if re.search(r"paginat|page-numbers|page_link|nav-next|dataTable", cls + " " + ident, re.I):
            found_pag = True
            print(f"   <{el.name} class={cls!r} id={ident!r}> {norm(el.get_text(' '))[:160]!r}")
    if not found_pag:
        print("   (tidak ada elemen dengan class/id pagination)")

    print("\n--- Semua <select> (kecuali selectVisitor pekerjaan) ---")
    any_sel = False
    for sel in soup.find_all("select"):
        if sel.get("name") == "pekerjaan":
            continue
        any_sel = True
        print("   select name=", sel.get("name"), "id=", sel.get("id"))
        for o in sel.find_all("option")[:20]:
            print("      ", repr(o.get("value")), "|", norm(o.get_text(" ")))
    if not any_sel:
        print("   (tidak ada select filter/pagination)")

    print("\n--- Link yang mengandung 'page' atau query string ---")
    qs = sorted({urljoin(BASE + "/", a["href"].strip())
                 for a in soup.find_all("a", href=True) if "?" in a["href"]})
    if qs:
        for u in qs:
            print("   ", u)
    else:
        print("   (tidak ada link dengan query string)")

    print("\n--- Kata kunci pagination di teks ---")
    for kw in ["Berikutnya", "Sebelumnya", "Next", "Prev", "Halaman", "dari", "Total", "Menampilkan"]:
        hits = [m.start() for m in re.finditer(kw, txt, re.I)]
        if hits:
            print(f"   {kw!r}: {len(hits)} kemunculan")
    for m in re.finditer(r"(?:Halaman|Page)\s+\d+", txt, re.I):
        print("   cuplikan:", norm(txt[max(0, m.start() - 60):m.start() + 80]))

    print("\n--- Panjang href unik yang relevan di dalam tabel ---")
    tb = data_table(soup)
    if tb:
        hrefs = {urljoin(BASE + "/", a["href"].strip()) for a in tb.find_all("a", href=True)}
        print("   jumlah:", len(hrefs))
        for u in sorted(hrefs)[:5]:
            print("     ", u)

    # --- Uji ?page=2 untuk memastikan tidak ada data tambahan ---
    print("\n--- UJI ?page=2 (jeda 2 detik) ---")
    time.sleep(2)
    url2 = URL + "?page=2"
    try:
        r2 = get(url2)
        s2 = BeautifulSoup(r2.text, "html.parser")
        n2, _, ids2 = count_rows(s2)
        print("   URL   :", url2)
        print("   status:", r2.status_code, "| bytes:", len(r2.text))
        print("   baris :", n2, "| id unik:", len(set(ids2)))
        same = set(ids) == set(ids2)
        print("   ID sama dengan halaman 1? ", same)
        if not same:
            print("   ID baru di page2:", sorted(set(ids2) - set(ids))[:10])
    except Exception as e:
        print("   error:", e)

    print("\n--- Kesimpulan ---")
    print(f"   Klaim grid tahun : 46 dokumen")
    print(f"   Baris di halaman : {n}   -> {'TIDAK ada pagination' if n >= 46 else 'ADA pagination / tidak semua tampil'}")


if __name__ == "__main__":
    main()
