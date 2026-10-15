"""Verifikasi akhir metadata_perda_final.json."""
import collections
import io
import json
import os

d = json.load(io.open("metadata_perda_final.json", encoding="utf-8"))
print("total dokumen :", len(d))

ok = [x for x in d if x["status_ekstraksi"] == "ok"]
gagal = [x for x in d if x["status_ekstraksi"] != "ok"]
print("berhasil      :", len(ok))
print("gagal         :", len(gagal))
print()

print("Rincian 9 dokumen gagal:")
alasan = collections.Counter()
for x in sorted(gagal, key=lambda y: y["id"]):
    print(f"  id={x['id']:<6} {x['tahun']}  {x['jumlah_halaman']:>5}hal  {x['alasan_gagal']}")
    alasan[x["alasan_gagal"].split("(")[0].strip()] += 1
print()
print("rekap alasan:", dict(alasan))
print()

# konsistensi
rusak = [x["id"] for x in ok if not x["path_teks"] or not os.path.exists(x["path_teks"])]
print("path_teks hilang :", rusak or "tidak ada")
kosong = [x["id"] for x in ok if x["panjang_teks"] == 0]
print("panjang_teks = 0 :", kosong or "tidak ada")

# hanya dokumen scan yang boleh punya path_teks None
print("gagal tanpa alasan tidak dikenal:",
      [x["id"] for x in gagal if not x["alasan_gagal"]] or "tidak ada")

# cek isi file benar-benar ada (sample)
print()
print("Sampel 5 teks terbaru (5 dokumen yg baru berhasil):")
baru = [1131, 3772, 4334, 4462, 4593]
for i in baru:
    x = next((y for y in d if y["id"] == i), None)
    if not x:
        continue
    t = io.open(x["path_teks"], encoding="utf-8").read()
    print(f"  {i}: {len(t):>9,} kar di file | metadata {x['panjang_teks']:>9,} | "
          f"cocok={len(t) == x['panjang_teks']}")
    print(f"      {t[:70]!r}")

total_kar = sum(x["panjang_teks"] for x in ok)
print()
print(f"total karakter : {total_kar:,}")
print(f"file .txt      : {len([f for f in os.listdir('text_raw') if f.endswith('.txt')])}")
sz = sum(os.path.getsize(os.path.join("text_raw", f)) for f in os.listdir("text_raw"))
print(f"ukuran text_raw: {sz / 1024**2:.2f} MB")
print("sisa pdf_raw   :", os.listdir("pdf_raw") or "(kosong)")
