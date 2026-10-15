"""Cek isi checkpoint sebelum run ulang."""
import collections
import io
import json

cp = json.load(io.open("checkpoint_ekstraksi.json", encoding="utf-8"))
ok = sum(1 for v in cp.values() if v.get("status_ekstraksi") == "ok")
print("checkpoint total :", len(cp))
print("berhasil (ok)    :", ok)
print("gagal            :", len(cp) - ok)
print()
alasan = collections.Counter()
for k, v in sorted(cp.items(), key=lambda x: int(x[0])):
    if v.get("status_ekstraksi") != "ok":
        a = v.get("alasan")
        alasan[a] += 1
        print(f"  id={k:<6} {v.get('jumlah_halaman')}hal  {a}")
print()
print("rekap alasan gagal:")
for a, n in alasan.items():
    print(f"  {n}x  {a}")
