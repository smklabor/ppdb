# Aplikasi Surat Masuk & Surat Keluar

Aplikasi web berbasis **Flask + SQLite** untuk mengelola:

- Surat masuk dan surat keluar
- Hak akses pengguna: **Super Admin, Kepala Sekolah, Wakil Kepala Sekolah, Staff**
- Disposisi surat masuk
- Kategori surat
- Template surat keluar:
  - Surat Keputusan
  - Surat Keterangan
  - Surat Tugas
  - Surat Pernyataan
- Dashboard dengan info grafis
- Rekap laporan cetak **PDF**

## Jalankan

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py initdb
python manage.py run
```

Akses: `http://127.0.0.1:5000`

## Akun awal

| Username | Password | Role |
|---|---|---|
| superadmin | admin123 | super_admin |
| kepsek | admin123 | kepala_sekolah |
| wakasek | admin123 | wakil_kepala_sekolah |
| staff | admin123 | staff |

