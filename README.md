# Zivi

Zivi adalah proyek AI agent untuk pembelajaran dan eksperimen pribadi, dengan Ubuntu/Linux sebagai lingkungan pengembangan utama. Fokus proyek ini adalah memahami, mengembangkan, menguji, dan meningkatkan sistem agent secara bertahap.

> **Status:** fork pengembangan pribadi. Belum disertifikasi untuk produksi. Tidak ada rilis atau publikasi paket yang dilakukan melalui workflow ini.

## Tujuan

- Menjadikan Ubuntu/Linux sebagai platform utama pengembangan dan pengujian.
- Mempertahankan fungsi agent yang sudah ada sambil melakukan perubahan kecil dan dapat diverifikasi.
- Membangun workflow engineering yang terencana, berbasis bukti, dan dapat diaudit.
- Mengisolasi data pengujian dari data pengguna sehari-hari.
- Mengganti identitas publik secara bertahap tanpa merusak runtime, installer, atau integrasi.

## Fondasi engineering

Fondasi engineering yang ditambahkan pada PR #1 menyediakan:

- Inspeksi repository dan instruksi proyek sebelum perubahan.
- Kriteria penerimaan dan perencanaan tugas dengan dependensi.
- Implementasi bertahap dan pemeriksaan yang sesuai.
- Pelaporan bukti, blocker, dan hal yang belum diverifikasi.
- Ledger SQLite lokal sebagai fallback untuk status tugas, dengan dependency gates, event audit, dan penyelesaian yang mensyaratkan bukti.
- Pembatasan akses path proyek dan perlindungan agar database milik backend lain tidak dimodifikasi.

Fondasi ini **bukan** organisasi engineering otonom yang telah tersertifikasi. Orkestrasi peran yang terstruktur, action gates deterministik, verifikasi independen, dan sertifikasi build end-to-end masih merupakan pekerjaan lanjutan. CI yang lulus tidak membuktikan semua integrasi eksternal berfungsi.

## Lingkungan yang ditargetkan

- Ubuntu/Linux
- Git (termasuk Git LFS sesuai panduan kontribusi)
- Python **3.14** (`>=3.14,<3.15`) melalui workflow PM yang didukung repository
- Node.js hanya untuk workflow yang memerlukannya
- Docker atau Nix hanya ketika menjalankan pemeriksaan terkait

Ikuti [CONTRIBUTING.md — Development Setup](CONTRIBUTING.md#development-setup) untuk menyiapkan Python dan PM. Jangan mengasumsikan Python sistem yang terpasang sudah memenuhi versi yang diperlukan, dan jangan mengubah environment yang dikelola PM dengan `pip` atau `uv` secara langsung.

## Menyiapkan lingkungan pengujian pribadi

### 1. Clone repository

```bash
git clone https://github.com/xarvea/zivi.git
cd zivi
```

Sebelum berpindah branch, periksa `git status` dan amankan perubahan lokal yang belum di-commit. Gunakan branch pengembangan untuk eksperimen; jangan mengerjakan perubahan langsung di `main`.

### 2. Isolasi data lokal

Gunakan direktori terpisah untuk sesi pengujian, memory, skills, log, dan kredensial:

```bash
export ZIVI_HOME="${ZIVI_HOME:-$HOME/.zivi}"
export HERMES_HOME="$ZIVI_HOME"  # Jembatan kompatibilitas untuk komponen runtime yang belum dimigrasikan
mkdir -p "$ZIVI_HOME"
```

`ZIVI_HOME` adalah variabel yang digunakan untuk setup pribadi. Sebagian komponen runtime masih membaca `HERMES_HOME`; keduanya perlu diarahkan ke direktori yang sama sampai migrasi konfigurasi selesai. Nama internal yang tersisa adalah detail kompatibilitas, bukan branding produk.

Gunakan API key pengujian terpisah jika memungkinkan. Jangan menyimpan kredensial, database sesi, memory, cache, atau log pribadi ke Git.

### 3. Siapkan Python dan PM

Selesaikan prasyarat dan workflow PM di [CONTRIBUTING.md — Development Setup](CONTRIBUTING.md#development-setup) terlebih dahulu. Repository ini memerlukan Python **3.14** (`>=3.14,<3.15`); gunakan interpreter yang disiapkan melalui workflow PM, bukan Python sistem dengan versi yang tidak sesuai.

Setelah PM siap, dari root checkout, aktifkan environment development repository:

```bash
source ./activate
```

Jangan lanjutkan jika aktivasi gagal. Ikuti pesan error dari workflow PM untuk mendiagnosis masalah sebelum menjalankan test.

### 4. Jalankan smoke test CLI

Dengan environment repository aktif dan `ZIVI_HOME`/`HERMES_HOME` diarahkan ke direktori pengujian yang terisolasi, jalankan:

```bash
hermes --version
```

Perintah ini memverifikasi bahwa CLI dari checkout aktif dapat dipanggil dan melaporkan versinya. Ini **bukan** bukti bahwa provider, gateway, installer, updater, atau integrasi eksternal berfungsi. Selama migrasi, nama executable masih `hermes`; command `zivi` belum ditambahkan.

Jika executable yang ditemukan bukan berasal dari checkout ini, periksa aktivasi environment dan `PATH`. Jangan menghapus atau menimpa instalasi lain hanya untuk mengubah prioritas command.

### 5. Siapkan environment pengujian terpisah (opsional)

Dari root checkout setelah workflow PM menyiapkan Python 3.14, buat environment independen untuk test dan editor:

```bash
python -m pm.build_env --source . --out .venv --group dev --group test
```

Direktori tujuan `.venv` harus belum ada, termasuk sebagai direktori kosong atau symlink. Jika ingin memakai lokasi lain, pilih path baru. Jangan menghapus environment yang sudah ada tanpa memastikan bahwa itu hanya environment disposable yang memang ingin dibuat ulang. Gunakan environment terpisah ini untuk test sesuai panduan kontribusi.

Langkah ini tidak menjamin semua backend opsional atau integrasi eksternal terpasang. Siapkan dependensi tambahan hanya untuk fitur yang memang akan diuji.

## Verifikasi perubahan

Gunakan test runner repository:

```bash
scripts/run_tests.sh
```

Untuk pengujian terarah:

```bash
scripts/run_tests.sh tests/test_hermes_constants.py
```

Sebelum mengandalkan perubahan:

1. Jalankan unit test dan behavioral test yang relevan.
2. Jalankan lint, type check, packaging check, serta CI yang sesuai.
3. Tinjau diff lengkap untuk perubahan yang tidak disengaja dan kebocoran secret.
4. Pastikan direktori pengujian Zivi terisolasi dari data normal.
5. Tandai pemeriksaan yang tidak bisa dijalankan sebagai **NOT VERIFIED**; jangan mengklaim test lulus tanpa bukti.

## Aturan pengembangan

- Kerjakan perubahan pada feature branch dan gunakan pull request untuk review.
- Jangan push langsung ke `main`, merge PR, deploy, publish paket/image, atau membuat release tanpa otorisasi eksplisit.
- Pilih commit kecil yang mudah ditinjau dan di-rollback.
- Jangan melakukan penggantian massal string internal tanpa memetakan seluruh consumer, lockfile, test, installer, dan updater.
- Pertahankan pemberitahuan lisensi dan copyright yang diwajibkan serta tinjau lisensi dependency sebelum redistribusi.

## Lisensi

Lihat [LICENSE](LICENSE) untuk teks lisensi yang berlaku. Identitas publik proyek ini adalah **Zivi**; nama internal yang belum dimigrasikan akan diperbarui melalui perubahan terpisah dan teruji.
