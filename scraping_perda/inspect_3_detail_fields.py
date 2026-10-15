"""
TUGAS 1 - Langkah 3b: parse nilai metadata dengan benar.
Diagnosa struktur sel metadata + ekstrak URL PDF asli.

Jalankan: python inspect_3_detail_fields.py
"""
import json
import re
import sys
import time
from urllib.parse import unquote, urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://jdih.banyumaskab.go.id"
URL_DOC = (
    BASE + "/produk-hukum/3028/peraturan-daerah-kabupaten-banyumas-tentang-"
    "pemberhentianpemberhentian-sementara-pegawai-daerah"
)

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


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


LABEL_KEYS = [
    "Tipe Dokumen", "Judul", "T.E.U. Badan / Pengarang", "Nomor Peraturan",
    "Tahun Terbit", "Jenis / Bentuk Peraturan", "Singkatan Jenis / Bentuk Peraturan",
    "Tempat Penetapan", "Tanggal Penetapan", "Sumber", "Subjek", "Status Peraturan",
    "Bahasa", "Lokasi", "Bidang Hukum", "Keterangan", "Penandatangan",
    "Urusan Pemerintahan", "Hasil Uji Materi", "Dokumen Terkait", "Peraturan Terkait",
    "Peraturan Pelaksana", "Abstrak",
]


def main():
    r = get(URL_DOC)
    soup = BeautifulSoup(r.text, "html.parser")
    print("URL   :", URL_DOC)
    print("Status:", r.status_code, "| bytes:", len(r.text))

    # --- Cari baris metadata berdasarkan label yang dikenal ---
    print("\n--- STRUKTUR BARIS METADATA (2 contoh mentah) ---")
    raw_rows = []
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        label = norm(cells[0].get_text(" ")).rstrip(":").strip()
        if any(label == k or label.startswith(k) for k in LABEL_KEYS):
            raw_rows.append((label, cells, tr))
    for label, cells, tr in raw_rows[:2]:
        print(f"\nLABEL: {label!r}  jumlah sel={len(cells)}")
        for k, c in enumerate(cells):
            print(f"   sel[{k}] class={c.get('class')} text={norm(c.get_text(' '))[:120]!r}")
        print("   HTML:", tr.prettify()[:900])

    # --- Ekstrak metadata: ambil sel setelah label, gabung teks + link ---
    print("\n--- METADATA LENGKAP ---")
    meta = {}
    for label, cells, tr in raw_rows:
        parts = []
        links = []
        for c in cells[1:]:
            t = norm(c.get_text(" "))
            if t and t not in (":", "-"):
                parts.append(t)
            for a in c.find_all("a", href=True):
                links.append((norm(a.get_text(" ")), urljoin(BASE + "/", a["href"].strip())))
        val = " | ".join(p for p in parts if p)
        meta[label] = {"nilai": val, "links": links}
        print(f"   {label:<34}: {val[:230]}")
        for lab, u in links:
            print(f"        -> {lab!r:<18} {u}")

    # --- Ekstrak URL PDF dari iframe pdfjs ---
    print("\n--- URL DOKUMEN PDF ---")
    pdf_urls = []
    for ifr in soup.find_all("iframe"):
        src = ifr.get("src", "")
        if "viewer.html?file=" in src:
            f = parse_qs(urlparse(src).query).get("file", [None])[0]
            if f:
                pdf_urls.append(f)
    for a in soup.find_all("a", href=True):
        u = urljoin(BASE + "/", a["href"].strip())
        if ".pdf" in u.lower():
            pdf_urls.append(u)
    for p in dict.fromkeys(pdf_urls):
        print("   PDF:", p)

    # --- Tombol aksi ---
    print("\n--- TOMBOL AKSI ---")
    for a in soup.find_all("a", href=True):
        cls = " ".join(a.get("class") or [])
        lab = norm(a.get_text(" "))
        u = urljoin(BASE + "/", a["href"].strip())
        if re.search(r"btn|download|unduh|abstrak", cls + " " + lab, re.I) and "jdih.banyumaskab.go.id" in u:
            print(f"   class={cls!r:<30} label={lab!r:<12} {u}")

    # --- Verifikasi endpoint download ---
    print("\n--- CEK ENDPOINT DOWNLOAD (HEAD, jeda 2 detik) ---")
    time.sleep(2)
    dl = BASE + "/downloadprodukhukum/3028"
    try:
        rd = requests.get(dl, headers=HEADERS, timeout=45, allow_redirects=True, stream=True)
        ctype = rd.headers.get("Content-Type")
        cd = rd.headers.get("Content-Disposition")
        print("   status :", rd.status_code)
        print("   type   :", ctype)
        print("   disp   :", cd)
        print("   final  :", rd.url)
        first = next(rd.iter_content(16), b"")
        print("   magic  :", first[:8])
        rd.close()
    except Exception as e:
        print("   error:", e)

    with open("detail_sample.json", "w", encoding="utf-8") as f:
        json.dump(
            {"url_dokumen": URL_DOC, "metadata": meta, "pdf_urls": list(dict.fromkeys(pdf_urls))},
            f, ensure_ascii=False, indent=2)
    print("\n(tersimpan: detail_sample.json)")


if __name__ == "__main__":
    main()
