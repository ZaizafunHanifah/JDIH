"""
Scraper metadata Peraturan Daerah - JDIH Kabupaten Banyumas
==========================================================

Sumber data:
  daftar : /produk-hukum/jenis/peraturan-perundang-undangan/peraturan-daerah/{tahun}?per_page=50
  detail : /produk-hukum/{doc_id}/{slug}          (slug boleh sembarang, WAJIB ada)
  pdf    : /downloadprodukhukum/{doc_id}            (URL saja, tidak diunduh)

Catatan penting hasil inspeksi:
  - Parameter halaman harus `per_page` (underscore). `per-page` diabaikan server.
  - Kolom tabel listing: No Peraturan | Tahun | Judul Produk Hukum | Status | #
  - Tabel detail punya 3 sel per baris: [label] [ :] [nilai]

Jalankan (test kecil, hanya tahun 2026):
  python scrape_metadata.py
"""
import json
import os
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "https://jdih.banyumaskab.go.id"
LIST_TMPL = (
    BASE + "/produk-hukum/jenis/peraturan-perundang-undangan/peraturan-daerah/{tahun}"
    "?per_page=50"
)
DETAIL_TMPL = BASE + "/produk-hukum/{doc_id}/"
PDF_TMPL = BASE + "/downloadprodukhukum/{doc_id}"

DELAY = 1.5
SLUG_DUMMY = "detail"  # server tidak memvalidasi isi slug

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "id-ID,id;q=0.9",
    "Referer": BASE + "/produk-hukum/jenis/peraturan-perundang-undangan/peraturan-daerah",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# label metadata detail yang diambil
FIELD_DETAIL = [
    "Nomor Peraturan",
    "Tahun Terbit",
    "Tanggal Penetapan",
    "Status Peraturan",
    "Bidang Hukum",
    "Subjek",
]

# --- konfigurasi scraping penuh -------------------------------------------
SCOPE_TAHUN = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
CHECKPOINT = "checkpoint.json"
OUTPUT = "metadata_perda_2020_2026.json"
CHECKPOINT_EVERY = 10
MAX_RETRY = 3


class GagalRequest(Exception):
    """Request gagal setelah semua percobaan ulang."""


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def get(url):
    """Request dengan percobaan ulang; naikkan GagalRequest jika tetap gagal."""
    terakhir = None
    for percobaan in range(1, MAX_RETRY + 1):
        try:
            resp = SESSION.get(url, timeout=60)
            if resp.status_code != 200:
                raise GagalRequest(f"HTTP {resp.status_code}")
            if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding or "utf-8"
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as exc:
            terakhir = exc
            if percobaan < MAX_RETRY:
                print(f"      ! percobaan {percobaan}/{MAX_RETRY} gagal "
                      f"({type(exc).__name__}: {exc}), ulangi ...")
                time.sleep(DELAY * 2)
    raise GagalRequest(f"gagal setelah {MAX_RETRY} percobaan: {terakhir}")


def _tabel_data(soup):
    """Kembalikan <table> pertama yang punya <th> (tabel data, bukan tabel footer)."""
    for tb in soup.find_all("table"):
        if tb.find_all("th"):
            return tb
    return None


def scrape_tahun(tahun):
    """
    Ambil daftar dokumen Peraturan Daerah untuk satu tahun.
    Kembalikan list of dict berisi id, no_peraturan, tahun, judul, status.
    """
    url = LIST_TMPL.format(tahun=tahun)
    soup = get(url)
    tabel = _tabel_data(soup)
    if tabel is None:
        print(f"  [!] tabel tidak ditemukan untuk tahun {tahun}")
        return []

    hasil = []
    for tr in tabel.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue

        doc_id = None
        url_detail = None
        for a in tr.find_all("a", href=True):
            m = re.search(r"/produk-hukum/(\d+)/", a["href"])
            if m:
                doc_id = int(m.group(1))
                url_detail = urljoin(BASE + "/", a["href"].strip())
                break
        if doc_id is None:
            continue

        sel = [norm(td.get_text(" ")) for td in tds]
        hasil.append(
            {
                "id": doc_id,
                "no_peraturan": sel[0] if len(sel) > 0 else None,
                "tahun": sel[1] if len(sel) > 1 else None,
                "judul": sel[2] if len(sel) > 2 else None,
                "status": sel[3] if len(sel) > 3 else None,
                "url_detail": url_detail,
            }
        )
    return hasil


def pisah_status(nilai):
    """
    Pecah nilai 'Status Peraturan' menjadi dua bagian: status hukum + catatan relasi.

    Pendekatan: ambil HANYA token status di awal teks. Sisa teks apa pun
    diperlakukan sebagai catatan relasi, sehingga aman terhadap berbagai
    variasi kalimat relasi di JDIH ("Mencabut :", "Dicabut oleh :",
    "Mengubah", "Diubah Oleh :", "Mencabut ... Mencabut ...").

    Contoh masukan:
      "Berlaku"
        -> ("Berlaku", "")
      "Tidak Berlaku ~ tidak berlaku"
        -> ("Tidak Berlaku", "~ tidak berlaku")
      "Berlaku Mencabut : PERATURAN DAERAH Nomor 10 Tahun 2018 tentang X"
        -> ("Berlaku", "Mencabut : PERATURAN DAERAH Nomor 10 Tahun 2018 tentang X")
      "Berlaku Mengubah : PERATURAN DAERAH Nomor 1 Tahun 2024 tentang Pajak"
        -> ("Berlaku", "Mengubah : PERATURAN DAERAH Nomor 1 Tahun 2024 tentang Pajak")
      "Dicabut oleh : PERATURAN DAERAH Nomor 3 Tahun 2020"
        -> ("", "Dicabut oleh : PERATURAN DAERAH Nomor 3 Tahun 2020")
    """
    teks = norm(nilai)
    if not teks:
        return "", ""

    # status baku JDIH hanya di awal teks: "Berlaku" / "Tidak Berlaku"
    m = re.match(r"(?i)^(tidak\s+berlaku|berlaku)\b", teks)
    if m:
        status = "Tidak Berlaku" if m.group(1).lower().startswith("tidak") else "Berlaku"
        return status, norm(teks[m.end():])

    # format tak dikenal (tidak diawali status baku) -> seluruhnya catatan
    return "", teks


def scrape_detail(doc_id):
    """
    Ambil metadata dari halaman detail satu dokumen.
    Kembalikan dict berisi doc_id, url_detail, FIELD_DETAIL, serta
    'Status Peraturan' yang sudah dipecah jadi status_hukum + catatan_relasi.
    """
    url = DETAIL_TMPL.format(doc_id=doc_id) + SLUG_DUMMY
    soup = get(url)

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

    hasil = {"id": doc_id, "url_detail": url}
    for f in FIELD_DETAIL:
        hasil[f] = ketemu.get(f) or None

    # 'Status Peraturan' dipecah jadi status hukum + catatan relasi
    status_hukum, catatan_relasi = pisah_status(hasil.get("Status Peraturan"))
    hasil["status_hukum"] = status_hukum or None
    hasil["catatan_relasi"] = catatan_relasi or None
    return hasil


def ambil_url_pdf(doc_id):
    """Pola URL PDF sudah pasti, tidak perlu request."""
    return PDF_TMPL.format(doc_id=doc_id)


# --- checkpoint & retry ----------------------------------------------------


def muat_checkpoint(path=CHECKPOINT):
    """Baca checkpoint lama supaya dokumen yang sudah jadi tidak di-scrape ulang."""
    if not os.path.exists(path):
        return {"data": {}, "errors": []}
    try:
        with open(path, encoding="utf-8") as f:
            isi = json.load(f)
        isi.setdefault("data", {})
        isi.setdefault("errors", [])
        print(f"[checkpoint] dimuat: {len(isi['data'])} dokumen, "
              f"{len(isi['errors'])} error dari run sebelumnya")
        return isi
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[checkpoint] GAGAL dibaca ({exc}), mulai dari nol")
        return {"data": {}, "errors": []}


def simpan_checkpoint(cp, path=CHECKPOINT):
    """Tulis checkpoint secara atomik supaya file tidak korup saat proses mati."""
    sementara = path + ".tmp"
    with open(sementara, "w", encoding="utf-8") as f:
        json.dump(cp, f, ensure_ascii=False, indent=2)
    os.replace(sementara, path)


def scrape_semua(scope=SCOPE_TAHUN):
    """Jalankan scraping metadata untuk seluruh scope, dengan checkpoint."""
    cp = muat_checkpoint()
    data = cp["data"]
    errors = cp["errors"]
    id_error_tercatat = {str(e["id"]) for e in errors}

    print("=" * 78)
    print(f"SCRAPING PERDA 2020-2026  (target 92 dokumen, delay {DELAY}s)")
    print("=" * 78)

    # --- 1. kumpulkan semua listing per tahun ---
    print("\n[1] Mengambil daftar dokumen per tahun ...")
    semua_daftar = []
    for tahun in scope:
        try:
            rows = scrape_tahun(tahun)
            print(f"    {tahun}: {len(rows)} dokumen")
            semua_daftar.extend(rows)
        except Exception as exc:
            print(f"    {tahun}: GAGAL ({exc})")
            errors.append({"id": None, "tahun": tahun, "tahap": "listing",
                           "error": f"{type(exc).__name__}: {exc}"})
        time.sleep(DELAY)

    # dedup by id (jaga-jaga ada dokumen yang muncul di 2 tahun)
    unik = {}
    for r in semua_daftar:
        unik[r["id"]] = r
    semua_daftar = sorted(unik.values(), key=lambda r: (r["tahun"], r["id"]))
    total = len(semua_daftar)
    print(f"    TOTAL unik: {total} dokumen")

    # --- 2. loop detail dengan checkpoint ---
    print(f"\n[2] Scrape detail (checkpoint tiap {CHECKPOINT_EVERY} dokumen) ...")
    baru = sudah = 0
    sejak_checkpoint = 0

    for i, row in enumerate(semua_daftar, 1):
        doc_id = str(row["id"])

        if doc_id in data:
            sudah += 1
            continue
        if doc_id in id_error_tercatat:
            sudah += 1
            continue

        try:
            detail = scrape_detail(row["id"])
            gabung = dict(row)
            gabung.pop("url_detail", None)
            gabung.update(detail)
            gabung["url_pdf"] = ambil_url_pdf(row["id"])
            data[doc_id] = gabung
            baru += 1
            sejak_checkpoint += 1

            kosong = [f for f in FIELD_DETAIL if not gabung.get(f)]
            print(f"    ({i}/{total}) id={row['id']} {row['tahun']} "
                  f"{'lengkap' if not kosong else 'kosong: ' + ', '.join(kosong)}")
        except Exception as exc:
            errors.append({"id": row["id"], "tahun": row["tahun"], "tahap": "detail",
                           "error": f"{type(exc).__name__}: {exc}"})
            id_error_tercatat.add(doc_id)
            print(f"    ({i}/{total}) id={row['id']} {row['tahun']} GAGAL: {exc}")

        if sejak_checkpoint >= CHECKPOINT_EVERY:
            simpan_checkpoint({"data": data, "errors": errors})
            print(f"      >> checkpoint: {len(data)} dokumen, {len(errors)} error")
            sejak_checkpoint = 0

        time.sleep(DELAY)

    simpan_checkpoint({"data": data, "errors": errors})
    return data, errors


def main():
    data, errors = scrape_semua()

    # --- 3. output akhir ---
    dokumen = list(data.values())

    # hitung ulang pecahan status dari field mentah (tanpa request baru),
    # aman dijalankan ulang setelah pisah_status diperbaiki
    for d in dokumen:
        status_hukum, catatan_relasi = pisah_status(d.get("Status Peraturan"))
        d["status_hukum"] = status_hukum or None
        d["catatan_relasi"] = catatan_relasi or None

    dokumen.sort(key=lambda d: (d.get("tahun") or "", d.get("id") or 0))

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(dokumen, f, ensure_ascii=False, indent=2)
    simpan_checkpoint({"data": data, "errors": errors})

    # --- 4. ringkasan (tanpa print 92 dokumen) ---
    print()
    print("=" * 78)
    print("RINGKASAN SCRAPING 2020-2026")
    print("=" * 78)
    print(f"Target dokumen     : 92")
    print(f"Berhasil di-scrape : {len(dokumen)}")
    print(f"Error              : {len(errors)}")
    if errors:
        gagal = [e for e in errors if e.get("id") is not None]
        if gagal:
            print(f"  id gagal ({len(gagal)}): "
                  f"{', '.join(str(e['id']) for e in gagal)}")
        gagal_tahun = [e for e in errors if e.get("id") is None]
        if gagal_tahun:
            print(f"  gagal listing ({len(gagal_tahun)}): "
                  f"{', '.join(str(e['tahun']) for e in gagal_tahun)}")
        for e in errors[:15]:
            print(f"    - id={e.get('id')} tahun={e.get('tahun')} "
                  f"tahap={e.get('tahap')}: {e.get('error','')[:90]}")

    # sebaran status_hukum
    berlaku = sum(1 for d in dokumen if d.get("status_hukum") == "Berlaku")
    tidak_berlaku = sum(1 for d in dokumen if d.get("status_hukum") == "Tidak Berlaku")
    tidak_dikenali = sum(1 for d in dokumen if d.get("status_hukum") is None)
    print()
    print("Sebaran status_hukum:")
    print(f"  Berlaku        : {berlaku}")
    print(f"  Tidak Berlaku  : {tidak_berlaku}")
    print(f"  Tidak dikenal  : {tidak_dikenali}")
    if tidak_dikenali:
        ganjil = [d["id"] for d in dokumen if d.get("status_hukum") is None]
        print(f"    id dengan status tidak dikenali: {ganjil}")

    ada_relasi = [d for d in dokumen if d.get("catatan_relasi")]
    print(f"\ncatatan_relasi tidak kosong: {len(ada_relasi)}")
    if ada_relasi:
        print(f"  id: {', '.join(str(d['id']) for d in ada_relasi)}")

    # kelengkapan field
    print("\nKelengkapan field:")
    for f in FIELD_DETAIL:
        terisi = sum(1 for d in dokumen if d.get(f))
        print(f"  {f:<20}: {terisi}/{len(dokumen)}")

    # per tahun
    print("\nDokumen per tahun:")
    for t in SCOPE_TAHUN:
        n = sum(1 for d in dokumen if d.get("tahun") == str(t))
        print(f"  {t}: {n}")

    print(f"\nTersimpan : {OUTPUT}")
    print(f"Checkpoint: {CHECKPOINT}")


if __name__ == "__main__":
    main()


