# Konfigurasi Database

Aplikasi memakai PostgreSQL. Nilai default host, port, nama database, dan
username berada di `app/db.py`: `localhost`, `5432`, `jdih`, dan `postgres`.
Password dibaca dari environment variable `DB_PASSWORD`, bukan ditulis di kode.

Di PowerShell, isi password sebelum menjalankan server:

```powershell
$env:DB_PASSWORD = "password-postgres-anda"
uvicorn app.main:app --reload
```

Jika diperlukan, konfigurasi lain juga bisa diatur lewat environment:

```powershell
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$env:DB_NAME = "jdih"
$env:DB_USER = "postgres"
```

Koneksi database menunggu maksimal 5 detik secara default. Atur
`DB_CONNECT_TIMEOUT` jika membutuhkan batas waktu lain.
