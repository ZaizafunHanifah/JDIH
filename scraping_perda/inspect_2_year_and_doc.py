"""
TUGAS 1 - Langkah 2 & 3: inspeksi tabel tahun kecil (1971, 1 dokumen)
lalu跟进 1 link "Katalog" untuk melihat seluruh metadata + URL Download.

Jalankan: python inspect_2_year_and_doc.py
"""
import json
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://jdih.banyumaskab.go.id"
YEAR = 1971
URL_YEAR = f"{BASE}/produk-hukum/jenis/peraturan-perundang-undangan/peraturan-daerah/{YEAR}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9",
    "Referer": BASE + "/",
}


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=45)
    r.raise_for_status()
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    return r


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def main():
    print("=" * 78)
    print(f"STEP 2 - TABEL DAFTAR DOKUMEN TAHUN {YEAR}")
    print("=" * 78)
    print("URL:", URL_YEAR)
    r = get(URL_YEAR)
    soup = BeautifulSoup(r.text, "html.parser")
    print("Status:", r.status_code, "| bytes:", len(r.text))

    # Temukan tabel yang punya baris data (punya <th> header)
    target = None
    for tb in soup.find_all("table"):
        if tb.find_all("th"):
            target = tb
            break
    if target is None:
        print("!! tidak ditemukan tabel dengan <th>")
        for tb in soup.find_all("table"):
            print("tabel class=", tb.get("class"), "baris=", len(tb.find_all("tr")))
        return

    headers = [norm(th.get_text(" ")) for th in target.find_all("th")]
    print("\nKOLOM TABEL:", headers)

    rows = []
    for tr in target.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        cells = [norm(td.get_text(" ")) for td in tds]
        links = [urljoin(BASE + "/", a["href"].strip()) for a in tr.find_all("a", href=True)]
        link_labels = [norm(a.get_text(" ")) for a in tr.find_all("a", href=True)]
        rows.append({"cells": cells, "links": links, "link_labels": link_labels})

    print(f"Jumlah baris data: {len(rows)}")
    print("\n--- SEMUA BARIS (sel + link) ---")
    for i, row in enumerate(rows, 1):
        print(f"\n[{i}]")
        for j, c in enumerate(row["cells"]):
            colname = headers[j] if j < len(headers) else f"col{j}"
            print(f"   {colname:<14}: {c[:150]}")
        print(f"   {'LINK/LABEL':<14}:")
        for lab, u in zip(row["link_labels"], row["links"]):
            print(f"      - {lab!r:<22} {u}")

    # --- Ambil link Katalog pertama ---
    katalog = None
    for row in rows:
        for lab, u in zip(row["link_labels"], row["links"]):
            if re.search(r"katalog|detail|selengkapnya|detail", lab + " " + u, re.I):
                katalog = (lab, u)
                break
        if katalog:
            break
    if not katalog:
        # fallback: link pertama yang bukan download/pdf
        for row in rows:
            for lab, u in zip(row["link_labels"], row["links"]):
                if ".pdf" not in u.lower() and "download" not in lab.lower():
                    katalog = (lab, u)
                    break
            if katalog:
                break

    if not katalog:
        print("\n!! tidak ada link katalog ditemukan")
        return

    print("\n" + "=" * 78)
    print("STEP 3 - HALAMAN DETAIL DOKUMEN (Katalog)")
    print("=" * 78)
    print("Label :", katalog[0])
    print("URL   :", katalog[1])
    time.sleep(2)

    r2 = get(katalog[1])
    s2 = BeautifulSoup(r2.text, "html.parser")
    print("Status:", r2.status_code, "| bytes:", len(r2.text))
    print("Title :", norm(s2.title.get_text()) if s2.title else None)

    # Kumpulkan semua tabel metadata (label -> nilai)
    print("\n--- FIELD METADATA (dari tabel) ---")
    meta = {}
    for tb in s2.find_all("table"):
        trs = tb.find_all("tr")
        if len(trs) < 2:
            continue
        for tr in trs:
            cells = tr.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            k = norm(cells[0].get_text(" "))
            v = norm(cells[1].get_text(" "))
            if not k:
                continue
            if len(cells) >= 3 and not v:
                v = norm(cells[2].get_text(" "))
            if k and v:
                meta.setdefault(k, v)
    for k, v in meta.items():
        print(f"   {k:<34}: {v[:220]}")

    # Fallback: definisi list
    if not meta:
        print("   (tabel kosong, coba parse <dl>/<li>)")
        for dl in s2.find_all(["dl", "ul"]):
            t = norm(dl.get_text(" | "))
            if "Tahun" in t or "Nomor" in t:
                print("   ", t[:800])

    # --- Link download ---
    print("\n--- SEMUA LINK DI HALAMAN DETAIL ---")
    for a in s2.find_all("a", href=True):
        u = urljoin(BASE + "/", a["href"].strip())
        lab = norm(a.get_text(" "))
        if re.search(r"pdf|download|unduh|file|abstrak|preview|lihat|kkpr", u + " " + lab, re.I):
            print(f"   {lab!r:<28} {u}")

    # --- iframe / embed dokumen ---
    print("\n--- IFRAME / EMBED (viewer PDF) ---")
    for tag in s2.find_all(["iframe", "embed", "object"]):
        print("  ", tag.name, {k: v for k, v in tag.attrs.items() if k in ("src", "data", "type")})

    print("\n--- <a> dengan class btn / tombol aksi ---")
    for a in s2.find_all("a", href=True):
        cls = " ".join(a.get("class") or [])
        lab = norm(a.get_text(" "))
        if cls and re.search(r"btn|button|download|abstrak", cls + " " + lab, re.I):
            print(f"   class={cls!r:<28} label={lab!r:<24} {urljoin(BASE + '/', a['href'].strip())}")

    with open("detail_sample.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "tahun": YEAR,
                "url_tahun": URL_YEAR,
                "kolom_tabel": headers,
                "baris": rows,
                "url_katalog": katalog[1],
                "metadata": meta,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print("\n(tersimpan: detail_sample.json)")


if __name__ == "__main__":
    main()
