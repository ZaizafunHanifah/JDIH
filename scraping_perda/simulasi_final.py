"""
SIMULASI FINAL dengan 3 perbaikan tambahan (persampahan, perseroan, perumdam).
Membandingkan terhadap:
  (a) kategorisasi TERSIMPAN di jdih.db   -> read-only
  (b) hasil simulasi SEBELUM 3 perbaikan  -> dihitung ulang di bawah

JANGAN sentuh jdih.db.
Jalankan: python simulasi_final.py
"""
import collections
import csv
import io
import os
import re
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
DB = os.path.join(ROOT, "jdih.db")
CSV_PERDA = os.path.join(BASE, "perda_export.csv")

sys.path.insert(0, ROOT)
from import_real_data import TOPICS, match_topics  # noqa: E402

csv.field_size_limit(100000000)

# rekonstruksi TOPICS versi SEBELUM 3 perbaikan, untuk perbandingan
def topics_lama():
    t = {k: list(v) for k, v in TOPICS.items()}
    t["Perencanaan Pembangunan Daerah"] = [
        x for x in t["Perencanaan Pembangunan Daerah"] if x != "perseroan"]
    t["Perencanaan Pembangunan Daerah"].insert(
        t["Perencanaan Pembangunan Daerah"].index("tata ruang"), "persero")
    t["Perencanaan Pembangunan Daerah"] = [
        x for x in t["Perencanaan Pembangunan Daerah"] if x != "perumdam"]
    t["Perencanaan Pembangunan Daerah"].insert(
        t["Perencanaan Pembangunan Daerah"].index("persero"), "perumda")
    t["Pertanian dan Lingkungan Hidup"] = [
        x for x in t["Pertanian dan Lingkungan Hidup"] if x != "persampahan"]
    return t


def match_dengan(judul, topics):
    """Versi match_topics tapi dengan dict topics tertentu."""
    if not judul:
        return []
    jl = judul.lower()
    out = []
    for label, kws in topics.items():
        for kw in kws:
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", jl):
                out.append(label)
                break
    return out


def main():
    lama = topics_lama()

    # ---------- baca DB read-only ----------
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT d.id, d.nomor, d.tanggal_terbit, d.judul,
               GROUP_CONCAT(t.label_topik, '||') AS kat
        FROM documents d
        LEFT JOIN document_topics dt ON dt.document_id = d.id
        LEFT JOIN topics t ON t.id = dt.topic_id
        GROUP BY d.id
    """).fetchall()
    conn.close()

    perbup = [{
        "nt": f"{str(r['nomor']).strip()}_{str(r['tanggal_terbit'])[:4].strip()}",
        "judul": r["judul"] or "",
        "db": set((r["kat"] or "").split("||")) - {""},
    } for r in rows]
    for p in perbup:
        p["final"] = set(match_topics(p["judul"]))
        p["sebelum"] = set(match_dengan(p["judul"], lama))

    with io.open(CSV_PERDA, encoding="utf-8") as f:
        perda = list(csv.DictReader(f))
    for r in perda:
        r["_final"] = set(match_topics(r["judul"]))
        r["_sebelum"] = set(match_dengan(r["judul"], lama))

    # ---------- 1. konfirmasi 10_2023 ----------
    print("=" * 78)
    print("1. KONFIRMASI 10_2023")
    print("=" * 78)
    p = next(x for x in perbup if x["nt"] == "10_2023")
    jl = p["judul"].lower()
    print("Judul :", p["judul"].strip())
    print("DB            :", sorted(p["db"]))
    print("Simulasi lalu :", sorted(p["sebelum"]))
    print("FINAL         :", sorted(p["final"]))
    print()
    trig = [kw for kw in TOPICS["Pertanian dan Lingkungan Hidup"]
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", jl)]
    print("keyword '_Pertanian dan Lingkungan Hidup_' yang match di judul:", trig)
    ok = "Pertanian dan Lingkungan Hidup" in p["final"]
    print(f"-> kembali dapat 'Pertanian dan Lingkungan Hidup': {ok}")
    print(f"-> memicu lewat 'persampahan': {'persampahan' in trig}")

    # ---------- 2. dokumen yang berubah vs simulasi sebelumnya ----------
    print()
    print("=" * 78)
    print("2. DOKUMEN YANG BERUBAH vs SIMULASI SEBELUMNYA")
    print("=" * 78)
    berubah_pb = [p for p in perbup if p["final"] != p["sebelum"]]
    berubah_pd = [r for r in perda if r["_final"] != r["_sebelum"]]
    print(f"Perbup berubah : {len(berubah_pb)}")
    print(f"Perda  berubah : {len(berubah_pd)}")

    for label, daftar, kunci in (("PERBUP", berubah_pb, "nt"),
                                ("PERDA", berubah_pd, "nomor_tahun")):
        for x in daftar:
            f, s = x["final"], x["sebelum"]
            if label == "PERDA":
                f, s = x["_final"], x["_sebelum"]
            print(f"\n  [{x[kunci]}]")
            print(f"     SEBELUM: {sorted(s)}")
            print(f"     FINAL  : {sorted(f)}")
            if s - f:
                print(f"     hilang  : {sorted(s - f)}")
            if f - s:
                print(f"     masuk   : {sorted(f - s)}")
            print(f"     judul   : {x['judul'].strip()[:74]}")

    # ---------- 3. total perubahan vs DB ----------
    print()
    print("=" * 78)
    print("3. TOTAL PERUBAHAN vs jdih.db (yang tersimpan sekarang)")
    print("=" * 78)
    tot = [p for p in perbup if p["db"] != p["final"]]
    print(f"Perbup berubah dibanding DB : {len(tot)} dari {len(perbup)}")
    hilang = [p for p in tot if p["db"] and not p["final"]]
    dapat = [p for p in tot if p["final"] and not p["db"]]
    ganti = [p for p in tot if p["db"] and p["final"] and p["db"] != p["final"]]
    print(f"   kehilangan kategori : {len(hilang)}")
    print(f"   dapat kategori baru : {len(dapat)}")
    print(f"   kategori berganti   : {len(ganti)}")

    # ---------- 4. distribusi ----------
    print()
    print("=" * 78)
    print("4. DISTRIBUSI FINAL")
    print("=" * 78)
    for nama, daftar, get in (("PERBUP (386)", perbup, lambda x: x["final"]),
                              ("PERDA (83)", perda, lambda x: x["_final"])):
        ter = [x for x in daftar if get(x)]
        per = collections.Counter()
        for x in ter:
            for t in get(x):
                per[t] += 1
        print(f"\n--- {nama} ---")
        print(f"    match minimal 1 topik : {len(ter)} / {len(daftar)} "
              f"({len(ter) / len(daftar) * 100:.1f}%)")
        print(f"    tanpa topik           : {len(daftar) - len(ter)}")
        print(f"    {'kategori':<44}{'dok':>5}")
        print("    " + "-" * 49)
        for kat in TOPICS:
            n = per.get(kat, 0)
            print(f"    {kat:<44}{n:>5}" + ("   (KOSONG)" if n == 0 else ""))
        print("    " + "-" * 49)
        print(f"    {'TOTAL relasi':<44}{sum(per.values()):>5}")


if __name__ == "__main__":
    main()
