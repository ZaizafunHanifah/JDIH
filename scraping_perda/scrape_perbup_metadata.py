"""
Scraper metadata Peraturan Bupati — JDIH Kabupaten Banyumas
============================================================

Berdasarkan template scrape_metadata.py untuk Perda.
URL patterns yang benar:
  - Listing: /produk-hukom/jenis/peraturan-perundang-undangan/peraturan-bupati/{year}?per_page=50
  - Detail:  /produk-hukom/{doc_id}/{slug}  (slug penuh dari halaman listing)

Fitur:
  - Memeriksa robots.txt
  - Delay acak 10-30 detik antar request
  - Satu permintaan pada satu waktu (sequential)
  - Cache per dokumen — bisa dilanjutkan setelah terhenti
  - Berhenti otomatis jika 5 error beruntun (403/429/5xx)
  - Hanya mengambil: id, nomor, tahun, judul, subjek, bidang_hukum, url

Output:
  - metadata_perbup_2020_2024.json  (hasil akhir)
  - cache_perbup.json               (checkpoint per dokumen)
  - errors_perbup.json              (catatan error)

Cara pakai:
  python scrape_perbup_metadata.py            # scrape 2020-2024
  python scrape_perbup_metadata.py --dry-run    # periksa listing saja
"""
import json
import os
import re
import sys
import time
import random
import argparse
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://jdih.banyumaskab.go.id"
LIST_TMPL = (
    BASE + "/produk-hukom/jenis/peraturan-perundang-undangan/peraturan-bupati/{year}"
    "?per_page=50"
)
# Fallback listing URL (tanpa tahun) — berdasarkan link di homepage
LIST_NOYEAR = BASE + "/produk-hukom/jenis/peraturan-perundang-undangan/peraturan-bupati?per_page=50"
DETAIL_TMPL = BASE + "/produk-hukom/{doc_id}/{slug}"
PDF_TMPL = BASE + "/downloadprodukhukom/{doc_id}"

CACHE_FILE = "cache_perbup.json"
ERROR_FILE = "errors_perbup.json"
OUTPUT_FILE = "metadata_perbup_2020_2024.json"

DELAY_MIN = 10
DELAY_MAX = 30
CONSECUTIVE_ERROR_LIMIT = 5
MAX_RETRY = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9",
}

SCOPE_YEARS = [2020, 2021, 2022, 2023, 2024]

FIELD_DETAIL = [
    "Nomor Peraturan",
    "Tahun Terbit",
    "Tanggal Penetapan",
    "Status Peraturan",
    "Bidang Hukum",
    "Subjek",
]

session = requests.Session()
session.headers.update(HEADERS)


class ServerDownError(Exception):
    """Server mengembalikan error berulang — hentikan scraping."""


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def random_delay():
    delay = random.uniform(DELAY_MIN, DELAY_MAX)
    print(f"  (delay {delay:.1f}s)", end="", flush=True)
    time.sleep(delay)
    print(" done")


def check_robots():
    url = BASE + "/robots.txt"
    try:
        resp = session.get(url, timeout=15)
        if resp.status_code == 200:
            text = resp.text
            print(f"[robots.txt] OK — {len(text)} bytes")
            if "Disallow: /" in text or "Disallow: /produk-hukom" in text:
                print("[robots.txt] WARNING: ada aturan pembatasan!")
            elif text.strip():
                print(f"[robots.txt] Isi:\n{text[:500]}")
            else:
                print("[robots.txt] Kosong — semua diizinkan (default)")
        else:
            print(f"[robots.txt] Status {resp.status_code} — lanjut dengan ekstra hati-hati")
        return resp.status_code == 200
    except Exception as e:
        print(f"[robots.txt] Gagal diakses ({e}) — lanjut dengan ekstra hati-hati")
        return False


def get(url):
    """Single request dengan retry. Raise ServerDownError pada 403/429/5xx."""
    last_exc = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            resp = session.get(url, timeout=45, allow_redirects=True)
            if resp.status_code in (403, 401):
                raise ServerDownError(f"403/401 — access diblokir: {url[:80]}")
            if resp.status_code == 429:
                ra = resp.headers.get("Retry-After", "?")
                raise ServerDownError(f"429 Too Many Requests — Retry-After={ra}")
            if 500 <= resp.status_code < 600:
                raise ServerDownError(f"5xx Server Error {resp.status_code}: {url[:80]}")
            if resp.status_code == 404:
                return None  # 404 = dokumen tidak ada, bukan error server
            if resp.status_code != 200:
                print(f"      ! status {resp.status_code} (percobaan {attempt}/{MAX_RETRY})")
                if attempt < MAX_RETRY:
                    time.sleep(5)
                continue
            if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding or "utf-8"
            return resp
        except (ServerDownError,):
            raise
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_RETRY:
                print(f"      ! percobaan {attempt}/{MAX_RETRY} gagal ({type(exc).__name__})")
                time.sleep(5)
    raise ServerDownError(f"gagal setelah {MAX_RETRY} percobaan: {last_exc}")


def scrape_listing(tahun):
    """
    Ambil daftar dokumen Peraturan Bupati untuk satu tahun.
    Kembalikan list of dict: {id, slug, no_peraturan, tahun, judul, status}.
    """
    url = LIST_TMPL.format(tahun=tahun)
    print(f"  Listing URL: {url}")
    try:
        resp = get(url)
    except ServerDownError:
        raise

    # Try fallback URL (tanpa tahun)
    if resp is None:
        print(f"    -> 404, coba fallback (tanpa tahun)")
        url = LIST_NOYEAR
        resp = get(url)

    if resp is None:
        print(f"    -> 404 pada kedua pola URL")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    tabel = None
    for tb in soup.find_all("table"):
        if tb.find_all("th"):
            tabel = tb
            break

    if tabel is None:
        print(f"  [!] tabel tidak ditemukan untuk tahun {tahun}")
        return []

    hasil = []
    for tr in tabel.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue

        doc_id = None
        slug = None
        for a in tr.find_all("a", href=True):
            m = re.search(r"/produk-hukom/(\d+)/([^/]+)", a["href"])
            if m:
                doc_id = int(m.group(1))
                slug = m.group(2)
                break

        if doc_id is None:
            continue

        sel = [norm(td.get_text(" ")) for td in tds]
        hasil.append({
            "id": doc_id,
            "slug": slug or "detail",
            "no_peraturan": sel[0] if len(sel) > 0 else None,
            "tahun": sel[1] if len(sel) > 1 else str(tahun),
            "judul": sel[2] if len(sel) > 2 else None,
            "status": sel[3] if len(sel) > 3 else None,
        })

    return hasil


def scrape_detail(doc_id, slug):
    """
    Ambil metadata dari halaman detail satu dokumen.
    Kembalikan dict berisi: id, no_peraturan, tahun, judul, subjek, bidang_hukum, url.
    """
    # Try with full slug first, then /detail as fallback
    for slug_try in [slug, "detail"]:
        url = DETAIL_TMPL.format(doc_id=doc_id, slug=slug_try)
        try:
            resp = get(url)
        except ServerDownError:
            raise

        if resp is None:
            continue  # 404

        soup = BeautifulSoup(resp.text, "html.parser")

        ketemu = {}
        for tr in soup.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            label = norm(cells[0].get_text(" ")).rstrip(":").strip()
            if label in FIELD_DETAIL and label not in ketemu:
                nilai = norm(cells[2].get_text(" "))
                if nilai:
                    ketemu[label] = nilai

        if not ketemu and slug_try == "detail":
            continue  # Try next slug option

        result = {
            "id": doc_id,
            "url": url,
            "no_peraturan": ketemu.get("Nomor Peraturan"),
            "tahun": ketemu.get("Tahun Terbit"),
            "judul": ketemu.get("Judul") or ketemu.get("Tipe Dokumen"),
            "subjek": ketemu.get("Subjek"),
            "bidang_hukum": ketemu.get("Bidang Hukum"),
            "status_peraturan": ketemu.get("Status Peraturan"),
        }

        # Juga ekstrak judul dari header <h2>
        if not result["judul"]:
            h2 = soup.find("h2")
            if h2:
                result["judul"] = norm(h2.get_text(" "))

        if result["subjek"] or result["bidang_hukum"]:
            return result

        # If we got the full slug page but no fields, return what we have
        if slug_try != "detail":
            return result

    return None


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def save_errors(errors):
    with open(ERROR_FILE, "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)


def scrape_semua(dry_run=False):
    """Jalankan scraping untuk Perbup 2020-2024."""
    print("=" * 78)
    print("SCRAPING PERATURAN BUPATI 2020-2024 — METADATA JDIH")
    print(f"Delay: {DELAY_MIN}-{DELAY_MAX}s | Maks retry: {MAX_RETRY} | Max error beruntun: {CONSECUTIVE_ERROR_LIMIT}")
    print("=" * 78)

    # Check robots.txt
    print("\n[0] Memeriksa robots.txt ...")
    if not check_robots():
        print("  WARNING: tidak bisa memverifikasi robots.txt")
    random_delay()

    # Load checkpoint
    cache = load_cache()
    errors = []
    if os.path.exists(ERROR_FILE):
        with open(ERROR_FILE, encoding="utf-8") as f:
            errors = json.load(f)

    print(f"\n[checkpoint] Dokumen sudah berhasil: {len(cache)}")
    print(f"[checkpoint] Dokumen error: {len(errors)}")

    if dry_run:
        print("\n[DRY RUN] Hanya menguji listing page, tidak scrape detail")
        for tahun in SCOPE_YEARS:
            print(f"\n[{tahun}] Mengambil daftar ...")
            try:
                rows = scrape_listing(tahun)
                print(f"    {len(rows)} dokumen")
                for r in rows[:3]:
                    print(f"    id={r['id']} slug={r['slug'][:40]}... {r['judul'][:60] if r['judul'] else 'N/A'}")
            except ServerDownError as e:
                print(f"    SERVER DOWN: {e}")
                break
            random_delay()
        return

    # 1. Kumpulkan semua listing
    print("\n[1] Mengumpulkan daftar dokumen per tahun ...")
    semua = []
    for tahun in SCOPE_YEARS:
        print(f"\n  [{tahun}] ", end="", flush=True)
        try:
            rows = scrape_listing(tahun)
            print(f"{len(rows)} dokumen")
            semua.extend(rows)
        except ServerDownError as e:
            print(f"SERVER DOWN: {e}")
            print("  Scraping dihentikan. Silakan jalankan lagi nanti.")
            break
        random_delay()

    # Dedup by id
    unik = {}
    for r in semua:
        if r["id"] not in unik:
            unik[r["id"]] = r
    semua = sorted(unik.values(), key=lambda r: (r.get("tahun") or "0", r["id"]))
    total = len(semua)
    print(f"\n  TOTAL unik: {total} dokumen")

    if total == 0:
        print("  Tidak ada dokumen ditemukan. Cek koneksi server atau pola URL.")
        return

    # 2. Loop detail dengan checkpoint
    print(f"\n[2] Scrape detail (delay {DELAY_MIN}-{DELAY_MAX}s, checkpoint tiap 5 dokumen) ...")
    sudah = baru = 0
    errors_beruntun = 0

    for i, row in enumerate(semua, 1):
        doc_id = str(row["id"])

        if doc_id in cache:
            sudah += 1
            continue

        # Print progress
        judul_preview = (row.get("judul") or "")[:50]
        print(f"  ({i}/{total}) id={row['id']} {judul_preview}")

        try:
            result = scrape_detail(row["id"], row.get("slug", "detail"))

            if result:
                cache[doc_id] = result
                baru += 1
                subjek = result.get("subjek", "None")
                bh = result.get("bidang_hukum", "None")
                print(f"    -> subjek={subjek}, bidang_hukum={bh}")
            else:
                errors.append({"id": row["id"], "error": "detail page not found or no metadata"})
                print(f"    -> GAGAL: detail page 404")

            errors_beruntun = 0

        except ServerDownError as e:
            errors.append({"id": row["id"], "error": str(e)})
            errors_beruntun += 1
            print(f"    -> SERVER DOWN: {e} (error beruntun: {errors_beruntun})")
            if errors_beruntun >= CONSECUTIVE_ERROR_LIMIT:
                print(f"\n  !!! {CONSECUTIVE_ERROR_LIMIT} error beruntun — scraping dihentikan")
                save_cache(cache)
                save_errors(errors)
                print(f"  Cache tersimpan: {len(cache)} dokumen, {len(errors)} error")
                return

        # Checkpoint setiap 5 dokumen
        if (baru + sudah) % 5 == 0:
            save_cache(cache)
            save_errors(errors)
            print(f"  >> checkpoint: {len(cache)} berhasil, {len(errors)} error")

        # Delay antar request
        random_delay()

    # Save final
    save_cache(cache)
    save_errors(errors)

    # 3. Output akhir
    print("\n" + "=" * 78)
    print("RINGKASAN")
    print("=" * 78)
    dokumen = list(cache.values())
    print(f"Berhasil: {len(dokumen)}")
    print(f"Error: {len(errors)}")

    subjek_count = sum(1 for d in dokumen if d.get("subjek"))
    bh_count = sum(1 for d in dokumen if d.get("bidang_hukum"))
    print(f"Dokumen dengan Subjek: {subjek_count}")
    print(f"Dokumen dengan Bidang Hukum: {bh_count}")

    dokumen.sort(key=lambda d: (d.get("tahun") or "", d.get("id") or 0))

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(dokumen, f, ensure_ascii=False, indent=2)

    print(f"\nTersimpan: {OUTPUT_FILE}")
    print(f"Cache: {CACHE_FILE}")
    print(f"Errors: {ERROR_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Perbup metadata from JDIH Banyumas")
    parser.add_argument("--dry-run", action="store_true", help="Test listing pages only")
    args = parser.parse_args()
    scrape_semua(dry_run=args.dry_run)
