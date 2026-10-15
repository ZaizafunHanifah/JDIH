"""
TUGAS 1 - Langkah 1b:_pages__/produk-hukum/jenis/peraturan-perundang-undangan/peraturan-daerah
(yang muncul sebagai link 'Peraturan Daerah' di halaman sebelumnya)

Tujuan:
  1) apakah ada grid tahun + jumlah dokumen per tahun
  2) pola URL untuk masuk ke tahun tertentu

Jalankan: python inspect_1b_listing_real.py
"""
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://jdih.banyumaskab.go.id"
URL_LIST = BASE + "/produk-hukum/jenis/peraturan-perundang-undangan/peraturan-daerah"

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
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    return r


def main():
    print("=" * 78)
    print("STEP 1b - HALAMAN ASLI DAFTAR PERATURAN DAERAH")
    print("=" * 78)
    resp = get(URL_LIST)
    soup = BeautifulSoup(resp.text, "html.parser")
    print("URL   :", URL_LIST)
    print("Status:", resp.status_code, "| bytes:", len(resp.text))

    # Cari konten utama
    print("\n--- Heading halaman ---")
    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        t = " ".join(h.get_text(" ", strip=True).split())
        if t:
            print(f"   <{h.name}> {t[:110]}")

    # --- Grid tahun ---
    print("\n--- Kandidat anchor tahun ---")
    hits = []
    for a in soup.find_all("a", href=True):
        label = " ".join(a.get_text(" ", strip=True).split())
        href = a["href"].strip()
        m = re.fullmatch(r"((?:19|20)\d{2})(\s*\(\s*\d+\s*\))?", label) or re.fullmatch(r"((?:19|20)\d{2})", label)
        if m or re.search(r"/((?:19|20)\d{2})(?:[/?#]|$)", href):
            hits.append((label, urljoin(BASE + "/", href)))
    for lab, full in hits:
        print(f"   label={lab!r:<24} -> {full}")
    print("   total:", len(hits))

    # --- Semua href unik di area konten (filter nav) ---
    print("\n--- Href unik yang relevan (mengandung produk-hukum / tahun / ?) ---")
    seen = set()
    for a in soup.find_all("a", href=True):
        full = urljoin(BASE + "/", a["href"].strip())
        if full in seen:
            continue
        if re.search(r"produk-hukum|/20\d\d|kategori|page=|\?s=", full):
            seen.add(full)
            lab = " ".join(a.get_text(" ", strip=True).split())[:60]
            print(f"   {full}   [{lab}]")
        if len(seen) > 80:
            print("   ... (dipotong)")
            break

    # --- Tabel yang ada ---
    print("\n--- Tabel di halaman ---")
    for i, tb in enumerate(soup.find_all("table")):
        cap = tb.find("caption")
        thead = tb.find("thead")
        cols = [th.get_text(" ", strip=True) for th in tb.find_all("th")] if thead else []
        rows = tb.find_all("tr")
        print(f"   tabel[{i}] class={tb.get('class')} caption={cap.get_text(strip=True) if cap else None!r}")
        print(f"      baris={len(rows)} kolom={cols}")
        for r in rows[1:3]:
            print("      contoh:", [td.get_text(" ", strip=True)[:38] for td in r.find_all(["td", "th"])])

    # --- select filter tahun/jenis ---
    print("\n--- Select filter (kecuali select populate) ---")
    for sel in soup.find_all("select"):
        if sel.get("name") == "pekerjaan":
            continue
        print("   select name=", sel.get("name"), "id=", sel.get("id"))
        for o in sel.find_all("option")[:30]:
            print("      ", o.get("value"), "|", o.get_text(" ", strip=True))

    # --- teks yang memuat "Dokumen"/"dokumen"，也许网格 tahun ---
    txt = soup.get_text("\n", strip=True)
    print("\n--- Pola angka di teks utama (20xx) ---")
    print("   tahun出现:", sorted(set(re.findall(r"\b(?:19|20)\d{2}\b", txt)), reverse=True))
    idx = txt.lower().find("dokumen")
    print("   cuplikan sekitar kata 'dokumen':")
    print("   ", " | ".join(txt[max(0, idx - 300):idx + 300].split()) if idx > -1 else "(tidak ada)")

    # --- URL param pagination / year ---
    print("\n--- Pola URL dengan query string pada link ---")
    qs = sorted({urljoin(BASE + "/", a["href"].strip()) for a in soup.find_all("a", href=True) if "?" in a["href"]})[:40]
    for u in qs:
        print("   ", u)

    time.sleep(1.5)


if __name__ == "__main__":
    main()
