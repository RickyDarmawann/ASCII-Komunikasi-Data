# ASCII Chat — Komunikasi Data

Aplikasi chat satu lawan satu berbasis Python + Streamlit dan PostgreSQL Supabase. Pesan hanya menerima karakter ASCII tercetak (desimal 32–126). Setiap pesan memiliki tabel encoding ASCII dan visual sinyal NRZ-I.

## Fitur

- Daftar dan masuk menggunakan ID pengguna, email, dan password.
- Password disimpan sebagai hash bcrypt; tidak ada verifikasi email.
- Kontak dicari menggunakan ID pengguna.
- Polling percakapan setiap 2 detik dengan st.fragment.
- Validasi ASCII sebelum pesan disimpan, juga dibatasi oleh constraint database.
- Tabel karakter, hexadecimal, biner 7 bit MSB dulu, parity even, dan end bit.
- SVG NRZ-I: start 0 + data 7 bit + parity even + end 1; bit 1 membalik level.
- Panel uji karakter untuk memeriksa ASCII dan karakter yang tidak didukung.

> Encoding: ASCII 7 bit. ANSI, UTF-8, dan UTF-16 tidak didukung sebagai encoding aplikasi.

## 1. Skema Supabase

Project Supabase yang digunakan adalah **ASCII-Komunikasi-Data**: https://supabase.com/dashboard/project/sifdhjevbulotudscvqj

Skema aplikasi berada di namespace terpisah ascii_chat, dengan tabel users, contacts, dan messages. Skema ini tidak mengubah tabel pada public. SQL sudah diterapkan pada project di atas. File supabase/schema.sql tetap disertakan sebagai referensi dan setup ulang pada project lain jika diperlukan.

Jangan masukkan ascii_chat ke daftar exposed schemas Data API. Aplikasi mengaksesnya melalui koneksi PostgreSQL sisi server, bukan dari browser.

## 2. Jalankan lokal (Linux / Windows)

Disarankan Python 3.11 atau 3.12.

1. Clone https://github.com/ZeonPlay/ASCII-Komunikasi-Data.git lalu masuk ke folder project.
2. Buat virtual environment: python -m venv .venv
3. Aktifkan environment: Linux/macOS menggunakan source .venv/bin/activate; Windows PowerShell menggunakan .venv\\Scripts\\Activate.ps1.
4. Pasang dependensi dengan pip install -r requirements.txt.
5. Buat file .streamlit/secrets.toml berisi:

    [database]
    url = "postgresql://postgres.PROJECT_REF:DB_PASSWORD@aws-0-REGION.pooler.supabase.com:6543/postgres?sslmode=require"

Ganti placeholder dengan connection string dari Supabase Dashboard → project ASCII-Komunikasi-Data → Connect. Pastikan koneksi mengarah ke project sifdhjevbulotudscvqj. Untuk Streamlit Cloud, gunakan connection string pooler yang direkomendasikan Supabase bila tersedia. Jangan commit secrets.toml atau password database ke Git.

Jalankan dengan streamlit run app.py.

## 3. Deploy ke Streamlit Community Cloud

1. Buka https://share.streamlit.io/ dan masuk dengan GitHub.
2. Pilih repository ZeonPlay/ASCII-Komunikasi-Data, branch main, file utama app.py.
3. Di Advanced settings → Secrets, masukkan konfigurasi [database] url seperti di atas, memakai connection string project ASCII-Komunikasi-Data (sifdhjevbulotudscvqj).
4. Deploy, lalu tes membuat dua akun berbeda, menambahkan kontak, dan mengirim pesan dari dua sesi/browser.

Jangan masukkan connection string ke source code, commit, issue, atau screenshot publik.

## 4. Keamanan dan catatan

- SQL di Python menggunakan parameter placeholder %s, bukan menggabungkan input pengguna ke dalam SQL.
- Password menggunakan bcrypt; database menyimpan password_hash, bukan password asli.
- Database hanya diakses dari server Streamlit menggunakan kredensial PostgreSQL yang disimpan di Secrets. Jangan berikan connection string kepada pengguna atau commit ke Git.
- Karena autentikasi aplikasi ini dibuat sendiri untuk tugas, gunakan hanya untuk demonstrasi akademik; jangan gunakan ulang password penting.
- Polling 2 detik membaca ulang percakapan. Ini realtime berbasis polling, bukan WebSocket.
- Satu karakter menjadi 10 bit: start 0, tujuh bit data MSB dulu, parity even, end 1. Parity dihitung dari bit data saja agar total bit 1 pada data + parity genap.
- NRZ-I dimulai dari level pilihan pengguna; bit 1 membalik level di awal bit dan bit 0 mempertahankan level. Level tidak di-reset di antara karakter.
