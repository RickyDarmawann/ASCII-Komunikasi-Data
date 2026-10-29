# Menambahkan teks atau potongan gambar ke hasil.
"""Chat realtime untuk praktikum Komunikasi Data — ASCII 7 bit dan NRZ-I."""
# Mengaktifkan aturan anotasi tipe agar lebih fleksibel.
from __future__ import annotations

# Mengambil fitur atau alat yang dipakai pada aplikasi.
import html
# Mengambil fitur atau alat yang dipakai pada aplikasi.
import re
# Mengambil fitur atau alat yang dipakai pada aplikasi.
from contextlib import closing
# Mengambil fitur atau alat yang dipakai pada aplikasi.
from typing import Any

# Mengambil fitur atau alat yang dipakai pada aplikasi.
import bcrypt
# Mengambil fitur atau alat yang dipakai pada aplikasi.
import psycopg2
# Mengambil fitur atau alat yang dipakai pada aplikasi.
from psycopg2.extras import RealDictCursor
# Mengambil fitur atau alat yang dipakai pada aplikasi.
import streamlit as st
# Mengambil fitur atau alat yang dipakai pada aplikasi.
import streamlit.components.v1 as components


# Mengatur judul, ikon, dan lebar halaman aplikasi.
st.set_page_config(page_title="ASCII Chat | Komunikasi Data", page_icon="💬", layout="wide")


# ---------- Koneksi database dan sesi pengguna ----------
# Bagian ini mengatur koneksi PostgreSQL dan data sesi Streamlit.
# Membuat koneksi ke database Supabase PostgreSQL dari Streamlit Secrets.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def db_connect():
    # Menambahkan teks atau potongan gambar ke hasil.
    """Buka koneksi PostgreSQL menggunakan URL rahasia dari Streamlit Secrets."""
    # Mencoba menjalankan bagian ini sambil menangani jika terjadi kesalahan.
    try:
        # Menyimpan hasil proses ke dalam variabel.
        database_url = st.secrets["database"]["url"]
    # Menangani kesalahan jika proses sebelumnya gagal.
    except Exception as exc:
        # Menghentikan proses dan memberi tahu bahwa ada masalah.
        raise RuntimeError(
            # Menambahkan teks atau potongan gambar ke hasil.
            "Rahasia database belum diatur. Tambahkan [database] url pada Secrets."
        # Menutup daftar nilai atau pemanggilan fungsi.
        ) from exc
    # Mengembalikan hasil dari fungsi ini.
    return psycopg2.connect(database_url, connect_timeout=10, cursor_factory=RealDictCursor)


# Menjalankan SQL yang menghasilkan satu baris data, misalnya pencarian pengguna.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def query_one(sql: str, params: tuple = ()) -> Any:
    # Membuka proses atau sumber daya yang akan ditutup otomatis.
    with closing(db_connect()) as conn:
        # Membuka proses atau sumber daya yang akan ditutup otomatis.
        with conn:
            # Membuka proses atau sumber daya yang akan ditutup otomatis.
            with conn.cursor() as cur:
                # Menjalankan perintah database.
                cur.execute(sql, params)
                # Mengembalikan hasil dari fungsi ini.
                return cur.fetchone()


# Menjalankan SQL yang menghasilkan banyak baris data, misalnya daftar pesan.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def query_all(sql: str, params: tuple = ()) -> list[dict]:
    # Membuka proses atau sumber daya yang akan ditutup otomatis.
    with closing(db_connect()) as conn:
        # Membuka proses atau sumber daya yang akan ditutup otomatis.
        with conn:
            # Membuka proses atau sumber daya yang akan ditutup otomatis.
            with conn.cursor() as cur:
                # Menjalankan perintah database.
                cur.execute(sql, params)
                # Mengembalikan hasil dari fungsi ini.
                return list(cur.fetchall())


# Menjalankan SQL perubahan data yang tidak perlu mengembalikan baris.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def execute(sql: str, params: tuple = ()) -> None:
    # Membuka proses atau sumber daya yang akan ditutup otomatis.
    with closing(db_connect()) as conn:
        # Membuka proses atau sumber daya yang akan ditutup otomatis.
        with conn:
            # Membuka proses atau sumber daya yang akan ditutup otomatis.
            with conn.cursor() as cur:
                # Menjalankan perintah database.
                cur.execute(sql, params)


# Menyiapkan nilai awal session_state agar status login dan chat tetap terjaga saat UI diperbarui.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def init_state():
    # Menyimpan beberapa nilai dalam bentuk kamus.
    defaults = {
        # Menambahkan teks atau potongan gambar ke hasil.
        "user": None, "active_contact": None, "auth_tab": "Masuk",
        # Menambahkan teks atau potongan gambar ke hasil.
        "flash": None,
    # Menutup daftar nilai atau pemanggilan fungsi.
    }
    # Mengulang langkah ini untuk setiap item.
    for key, value in defaults.items():
        # Memeriksa apakah syarat ini benar.
        if key not in st.session_state:
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.session_state[key] = value


# ---------- Pemeriksaan karakter, konversi ASCII, dan pembentukan frame ----------
# Bagian ini mengubah karakter menjadi kode ASCII dan bit untuk dikirim sebagai frame.
# Memeriksa setiap karakter dan menandai apakah termasuk ASCII tercetak (kode 32–126).
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def inspect_ascii(text: str) -> list[dict]:
    # Membuat daftar untuk menyimpan beberapa nilai.
    rows = []
    # Mengulang langkah ini untuk setiap item.
    for char in text:
        # Mengambil kode angka dari karakter.
        code = ord(char)
        # Menyimpan hasil proses ke dalam variabel.
        supported = 32 <= code <= 126
        # Bagian ini membantu menjalankan proses aplikasi.
        rows.append({
            # Menambahkan teks atau potongan gambar ke hasil.
            "char": char, "code": code, "supported": supported,
            # Menambahkan teks atau potongan gambar ke hasil.
            "reason": "" if supported else (
                # Menambahkan teks atau potongan gambar ke hasil.
                "karakter kontrol" if code < 32 or code == 127
                # Bagian ini membantu menjalankan proses aplikasi.
                else "tidak didukung (kode > 127)"
            # Menutup daftar nilai atau pemanggilan fungsi.
            ),
        # Menutup daftar nilai atau pemanggilan fungsi.
        })
    # Mengembalikan hasil dari fungsi ini.
    return rows


# Memastikan pesan tidak kosong dan semua karakternya didukung sebelum dikirim.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def validate_message(text: str) -> tuple[bool, str]:
    # Memeriksa apakah syarat ini benar.
    if not text:
        # Mengembalikan hasil dari fungsi ini.
        return False, "Pesan tidak boleh kosong."
    # Mengulang langkah ini untuk setiap item.
    for char in text:
        # Mengambil kode angka dari karakter.
        code = ord(char)
        # Memeriksa apakah syarat ini benar.
        if not 32 <= code <= 126:
            # Mengembalikan hasil dari fungsi ini.
            return False, (
                # Menambahkan teks atau potongan gambar ke hasil.
                f"Karakter {char!r} (U+{code:04X}) tidak didukung. "
                # Menambahkan teks atau potongan gambar ke hasil.
                "Hanya ASCII 7 bit (kode 32-126)."
            # Menutup daftar nilai atau pemanggilan fungsi.
            )
    # Mengembalikan hasil dari fungsi ini.
    return True, ""


# KONVERSI ASCII: ord() mengambil kode desimal; format biner menghasilkan 7 bit (MSB lebih dulu).
# Lalu dibuat parity genap dan frame: Start bit 0 + 7 bit data + parity + End bit 1.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def encode_character(char: str) -> dict:
    # Mengambil nilai yang akan diproses.
    value = ord(char)  # Karakter -> kode ASCII desimal.
    # Menyimpan urutan bit yang akan diproses.
    bits = f"{value:07b}"  # Kode desimal -> representasi biner 7 bit.
    # Menghitung bit parity agar jumlah bit 1 menjadi genap.
    parity = bits.count("1") % 2  # Parity genap: total bit 1 termasuk parity menjadi genap.
    # Menyusun bit menjadi satu frame data.
    frame = "0" + bits + str(parity) + "1"  # Susunan frame: Start + Data + Parity + End.
    # Mengembalikan hasil dari fungsi ini.
    return {
        # Menambahkan teks atau potongan gambar ke hasil.
        "char": char, "ascii": value, "hex": f"{value:02X}", "bits": bits,
        # Menambahkan teks atau potongan gambar ke hasil.
        "parity": parity, "end": 1, "frame": frame,
    # Menutup daftar nilai atau pemanggilan fungsi.
    }


# Membuat tabel encoding dengan memanggil encode_character() untuk setiap karakter.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def signal_table(text: str) -> list[dict]:
    # Mengembalikan hasil dari fungsi ini.
    return [encode_character(ch) for ch in text]


# ---------- Logika NRZ-I dan penggambaran sinyal ----------
# Bagian ini mengubah urutan bit menjadi level tegangan, lalu menggambarnya sebagai SVG.
# Membentuk grafik NRZ-I dalam SVG berdasarkan bit frame setiap karakter.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def nrzi_svg(text: str, initial_high: bool = False) -> str:
    # Menambahkan teks atau potongan gambar ke hasil.
    """SVG NRZ-I: 1 membalik level di awal bit; 0 mempertahankan level."""
    # Memeriksa apakah syarat ini benar.
    if not text:
        # Mengembalikan hasil dari fungsi ini.
        return '<p style="font:14px sans-serif;color:#777">Belum ada karakter untuk divisualisasikan.</p>'

    # Menyimpan hasil proses ke dalam variabel.
    frames = signal_table(text)  # Encode tiap karakter menjadi frame bit.
    # Menyimpan urutan bit yang akan diproses.
    bits = "".join(item["frame"] for item in frames)  # Gabungkan semua frame menjadi satu aliran bit.
    # Menyimpan hasil proses ke dalam variabel.
    start_level = 1 if initial_high else 0  # Level awal: rendah (0) karena initial_high=False.
    # Menentukan level sinyal pada bit ini.
    level = start_level
    # Membuat daftar untuk menyimpan beberapa nilai.
    levels = []
    # LOGIKA NRZ-I: bit 1 membalik level tegangan; bit 0 mempertahankan level sebelumnya.
    # Mengulang langkah ini untuk setiap item.
    for bit in bits:
        # Memeriksa apakah syarat ini benar.
        if bit == "1":
            # Menentukan level sinyal pada bit ini.
            level = 1 - level  # 0 -> 1 atau 1 -> 0.
        # Bagian ini membantu menjalankan proses aplikasi.
        levels.append(level)  # Simpan level untuk digambar pada kolom bit ini.

    # Bagian ini membantu menjalankan proses aplikasi.
    bit_w, left, top = 42, 24, 72
    # Bagian ini membantu menjalankan proses aplikasi.
    high_y, low_y = 96, 168  # Posisi level +V dinaikkan sedikit agar grafik lebih lega.
    # Menyimpan hasil proses ke dalam variabel.
    plot_w = bit_w * len(bits)
    # Menentukan posisi atau ukuran gambar.
    width = left * 2 + plot_w
    # Menentukan posisi atau ukuran gambar.
    height = 300
    # Membuat daftar untuk menyimpan beberapa nilai.
    parts = [
        # Menambahkan teks atau potongan gambar ke hasil.
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        # Menambahkan teks atau potongan gambar ke hasil.
        f'viewBox="0 0 {width} {height}" role="img" aria-label="Sinyal NRZ-I">',
        # Menambahkan teks atau potongan gambar ke hasil.
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        # Menambahkan teks atau potongan gambar ke hasil.
        '<style>text{font-family:Arial,sans-serif;fill:#252525}.bit{font-size:14px}.label{font-size:12px}.frame-title{font-size:13px;font-weight:600}</style>',
        # Menambahkan teks atau potongan gambar ke hasil.
        f'<text x="4" y="{high_y+4}" font-size="12">+V</text>',
        # Menambahkan teks atau potongan gambar ke hasil.
        f'<text x="4" y="{low_y+4}" font-size="12">-V</text>',
    # Menutup daftar nilai atau pemanggilan fungsi.
    ]

    # VISUALISASI: tandai batas frame dan beri judul untuk setiap karakter.
    # Mengulang langkah ini untuk setiap item.
    for i, frame in enumerate(frames):
        # Menentukan posisi atau ukuran gambar.
        x = left + i * 10 * bit_w
        # Menyimpan hasil proses ke dalam variabel.
        char_label = "spasi" if frame["char"] == " " else f""
        # Bagian ini membantu menjalankan proses aplikasi.
        parts.append(
            # Menambahkan teks atau potongan gambar ke hasil.
            f'<text class="frame-title" x="{x + 5*bit_w}" y="24" text-anchor="middle">'
            # Menambahkan teks atau potongan gambar ke hasil.
            f'{html.escape(char_label)}</text>'
        # Menutup daftar nilai atau pemanggilan fungsi.
        )
        # Memeriksa apakah syarat ini benar.
        if i > 0:
            # Bagian ini membantu menjalankan proses aplikasi.
            parts.append(f'<line x1="{x}" y1="34" x2="{x}" y2="224" stroke="#555" stroke-width="2.5"/>')

    # VISUALISASI: gambar garis pembatas kolom dan label 0/1 di bawah grafik.
    # Mengulang langkah ini untuk setiap item.
    for i, bit in enumerate(bits):
        # Menentukan posisi atau ukuran gambar.
        x = left + i * bit_w
        # Bagian ini membantu menjalankan proses aplikasi.
        parts.append(f'<line x1="{x}" y1="36" x2="{x}" y2="224" stroke="#d9d9d9" stroke-width="1"/>')
        # Bagian ini membantu menjalankan proses aplikasi.
        parts.append(
            # Menambahkan teks atau potongan gambar ke hasil.
            f'<text class="bit" x="{x+bit_w/2}" y="205" text-anchor="middle">{bit}</text>'
        # Menutup daftar nilai atau pemanggilan fungsi.
        )
    # Bagian ini membantu menjalankan proses aplikasi.
    parts.append(f'<line x1="{left+plot_w}" y1="36" x2="{left+plot_w}" y2="224" stroke="#d9d9d9" stroke-width="1"/>')

    # VISUALISASI GELOMBANG: bentuk garis siku dari level NRZ-I yang sudah dihitung.
    # Level sebelumnya dipertahankan hingga tepi bit,
    # lalu bit 1 membalik level tepat di awal kolom bit tersebut.
    # Menentukan posisi atau ukuran gambar.
    y_prev = high_y if start_level else low_y
    # Membuat daftar untuk menyimpan beberapa nilai.
    points = [f"{left},{y_prev}"]
    # Mengulang langkah ini untuk setiap item.
    for i, level_now in enumerate(levels):
        # Menentukan posisi atau ukuran gambar.
        x = left + i * bit_w
        # Menentukan posisi atau ukuran gambar.
        y_now = high_y if level_now else low_y
        # Memeriksa apakah syarat ini benar.
        if y_now != y_prev:
            # Bagian ini membantu menjalankan proses aplikasi.
            points.append(f"{x},{y_now}")
        # Bagian ini membantu menjalankan proses aplikasi.
        points.append(f"{x+bit_w},{y_now}")
        # Menentukan posisi atau ukuran gambar.
        y_prev = y_now
    # Bagian ini membantu menjalankan proses aplikasi.
    parts.append(
        # Menambahkan teks atau potongan gambar ke hasil.
        '<polyline points="' + " ".join(points) +
        # Menambahkan teks atau potongan gambar ke hasil.
        '" fill="none" stroke="#1D9E75" stroke-width="4" stroke-linejoin="miter" stroke-linecap="square"/>'
    # Menutup daftar nilai atau pemanggilan fungsi.
    )

    # VISUALISASI FRAME: beri label Start (S), Data, Parity (P), dan End (E) di bawah bit.
    # Mengulang langkah ini untuk setiap item.
    for i, frame in enumerate(frames):
        # Menentukan posisi atau ukuran gambar.
        x = left + i * 10 * bit_w
        # Membuat daftar untuk menyimpan beberapa nilai.
        # groups = [(0, 1, "S"), (1, 8, f'Data "{html.escape(frame["char"])}"'), (8, 9, "P"), (9, 10, "E")]
        # Mengulang langkah ini untuk setiap item.
        for a, b, label in groups:
            # Bagian ini membantu menjalankan proses aplikasi.
            gx1, gx2 = x + a * bit_w + 2, x + b * bit_w - 2
            # Menyimpan hasil proses ke dalam variabel.
            gy = 238
            # Bagian ini membantu menjalankan proses aplikasi.
            parts.append(
                # Menambahkan teks atau potongan gambar ke hasil.
                f'<path d="M {gx1} {gy} v 6 H {gx2} v -6" fill="none" stroke="#777" stroke-width="1"/>'
            # Menutup daftar nilai atau pemanggilan fungsi.
            )
            # Bagian ini membantu menjalankan proses aplikasi.
            parts.append(
                # Menambahkan teks atau potongan gambar ke hasil.
                f'<text class="label" x="{(gx1+gx2)/2}" y="263" text-anchor="middle">{label}</text>'
            # Menutup daftar nilai atau pemanggilan fungsi.
            )
    # Bagian ini membantu menjalankan proses aplikasi.
    parts.append("</svg>")
    # Mengembalikan hasil dari fungsi ini.
    return "".join(parts)


# Menampilkan SVG NRZ-I di halaman Streamlit; level awal dipatok rendah.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def show_signal(text: str):
    # Level awal selalu rendah; tidak perlu menampilkan pilihan level ke pengguna.
    # Menyimpan hasil proses ke dalam variabel.
    svg = nrzi_svg(text, initial_high=False)
    # Menampilkan komponen HTML di halaman aplikasi.
    components.html(
        # Menambahkan teks atau potongan gambar ke hasil.
        f'<div style="overflow-x:auto;max-width:100%;padding:8px 0">{svg}</div>',
        # Menentukan posisi atau ukuran gambar.
        height=330, scrolling=True,
    # Menutup daftar nilai atau pemanggilan fungsi.
    )


# ---------- Pendaftaran, login, dan pesan kesalahan ----------
# Password disimpan sebagai hash bcrypt, bukan teks asli.
# Memvalidasi data pendaftaran, mengecek duplikasi, lalu menyimpan akun dengan hash password.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def register_user(user_id: str, email: str, password: str, confirm: str) -> tuple[bool, str]:
    # Bagian ini membantu menjalankan proses aplikasi.
    user_id, email = user_id.strip(), email.strip().lower()
    # Memeriksa apakah syarat ini benar.
    if not re.fullmatch(r"[A-Za-z0-9_]{3,24}", user_id):
        # Mengembalikan hasil dari fungsi ini.
        return False, "ID pengguna harus 3–24 karakter: huruf, angka, atau garis bawah."
    # Memeriksa apakah syarat ini benar.
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        # Mengembalikan hasil dari fungsi ini.
        return False, "Format email tidak valid."
    # Memeriksa apakah syarat ini benar.
    if len(password) < 6:
        # Mengembalikan hasil dari fungsi ini.
        return False, "Password minimal 6 karakter."
    # Memeriksa apakah syarat ini benar.
    if password != confirm:
        # Mengembalikan hasil dari fungsi ini.
        return False, "Konfirmasi password tidak sama."
    # Menyimpan hasil proses ke dalam variabel.
    exists = query_one(
        # Menambahkan teks atau potongan gambar ke hasil.
        "SELECT user_id FROM ascii_chat.users WHERE lower(user_id)=lower(%s) OR lower(email)=lower(%s)",
        # Menentukan nilai yang menjadi bagian dari data ini.
        (user_id, email),
    # Menutup daftar nilai atau pemanggilan fungsi.
    )
    # Memeriksa apakah syarat ini benar.
    if exists:
        # Mengembalikan hasil dari fungsi ini.
        return False, "ID pengguna atau email sudah digunakan."
    # Menyimpan hasil proses ke dalam variabel.
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    # Memanggil fungsi untuk menjalankan tugas tertentu.
    query_one(
        # Menambahkan teks atau potongan gambar ke hasil.
        "INSERT INTO ascii_chat.users (user_id, email, password_hash) "
        # Menambahkan teks atau potongan gambar ke hasil.
        "VALUES (%s, %s, %s) RETURNING id",
        # Menentukan nilai yang menjadi bagian dari data ini.
        (user_id, email, hashed),
    # Menutup daftar nilai atau pemanggilan fungsi.
    )
    # Mengembalikan hasil dari fungsi ini.
    return True, "Pendaftaran berhasil. Silakan masuk menggunakan ID, email, dan password."


# Mencari akun berdasarkan ID dan email, lalu mencocokkan password dengan hash bcrypt.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def login_user(user_id: str, email: str, password: str) -> tuple[bool, str, dict | None]:
    # Menyimpan hasil proses ke dalam variabel.
    row = query_one(
        # Menambahkan teks atau potongan gambar ke hasil.
        "SELECT id, user_id, email, password_hash FROM ascii_chat.users "
        # Menambahkan teks atau potongan gambar ke hasil.
        "WHERE lower(user_id)=lower(%s) AND lower(email)=lower(%s)",
        # Menentukan nilai yang menjadi bagian dari data ini.
        (user_id.strip(), email.strip().lower()),
    # Menutup daftar nilai atau pemanggilan fungsi.
    )
    # Memeriksa apakah syarat ini benar.
    if not row or not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        # Mengembalikan hasil dari fungsi ini.
        return False, "ID, email, atau password tidak cocok.", None
    # Mengembalikan hasil dari fungsi ini.
    return True, "Berhasil masuk.", {"id": str(row["id"]), "user_id": row["user_id"], "email": row["email"]}


# Menggambar UI daftar/masuk dan memproses hasil pengiriman form autentikasi.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def auth_page():
    # Menampilkan atau memproses bagian antarmuka Streamlit.
    st.title("ASCII Chat")
    # Menampilkan atau memproses bagian antarmuka Streamlit.
    st.caption("Praktikum Komunikasi Data · Chat satu lawan satu")
    # Menyimpan hasil proses ke dalam variabel.
    auth_tab = st.radio(
        # Menambahkan teks atau potongan gambar ke hasil.
        "Autentikasi", ["Daftar", "Masuk"], horizontal=True,
        # Menyimpan hasil proses ke dalam variabel.
        label_visibility="collapsed", key="auth_tab",
    # Menutup daftar nilai atau pemanggilan fungsi.
    )
    # Memeriksa apakah syarat ini benar.
    if auth_tab == "Daftar":
        # Membuka proses atau sumber daya yang akan ditutup otomatis.
        with st.form("form_daftar", clear_on_submit=True):
            # Menyimpan hasil proses ke dalam variabel.
            new_id = st.text_input("ID pengguna", max_chars=24)
            # Menyimpan hasil proses ke dalam variabel.
            new_email = st.text_input("Email")
            # Menyimpan hasil proses ke dalam variabel.
            password = st.text_input("Password", type="password")
            # Menyimpan hasil proses ke dalam variabel.
            confirm = st.text_input("Konfirmasi password", type="password")
            # Menyimpan hasil proses ke dalam variabel.
            submitted = st.form_submit_button("Daftar", use_container_width=True)
        # Memeriksa apakah syarat ini benar.
        if submitted:
            # Mencoba menjalankan bagian ini sambil menangani jika terjadi kesalahan.
            try:
                # Bagian ini membantu menjalankan proses aplikasi.
                ok, message = register_user(new_id, new_email, password, confirm)
                # Memeriksa apakah syarat ini benar.
                if ok:
                    # Menampilkan atau memproses bagian antarmuka Streamlit.
                    st.session_state["flash"] = message
                    # Menampilkan atau memproses bagian antarmuka Streamlit.
                    st.session_state["auth_tab"] = "Masuk"
                    # Menampilkan atau memproses bagian antarmuka Streamlit.
                    st.rerun()
                # Menjalankan bagian ini jika syarat sebelumnya tidak terpenuhi.
                else:
                    # Menampilkan atau memproses bagian antarmuka Streamlit.
                    st.error(message)
            # Menangani kesalahan jika proses sebelumnya gagal.
            except Exception as exc:
                # Menampilkan atau memproses bagian antarmuka Streamlit.
                st.error(db_error_message(exc))
    # Menjalankan bagian ini jika syarat sebelumnya tidak terpenuhi.
    else:
        # Memeriksa apakah syarat ini benar.
        if st.session_state.get("flash"):
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.success(st.session_state["flash"])
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.session_state["flash"] = None
        # Membuka proses atau sumber daya yang akan ditutup otomatis.
        with st.form("form_masuk"):
            # Menyimpan hasil proses ke dalam variabel.
            user_id = st.text_input("ID pengguna", key="login_id")
            # Menyimpan hasil proses ke dalam variabel.
            email = st.text_input("Email", key="login_email")
            # Menyimpan hasil proses ke dalam variabel.
            password = st.text_input("Password", type="password", key="login_password")
            # Menyimpan hasil proses ke dalam variabel.
            submitted = st.form_submit_button("Masuk", use_container_width=True)
        # Memeriksa apakah syarat ini benar.
        if submitted:
            # Mencoba menjalankan bagian ini sambil menangani jika terjadi kesalahan.
            try:
                # Bagian ini membantu menjalankan proses aplikasi.
                ok, message, user = login_user(user_id, email, password)
                # Memeriksa apakah syarat ini benar.
                if ok:
                    # Menampilkan atau memproses bagian antarmuka Streamlit.
                    st.session_state["user"] = user
                    # Menampilkan atau memproses bagian antarmuka Streamlit.
                    st.session_state["active_contact"] = None
                    # Menampilkan atau memproses bagian antarmuka Streamlit.
                    st.rerun()
                # Menjalankan bagian ini jika syarat sebelumnya tidak terpenuhi.
                else:
                    # Menampilkan atau memproses bagian antarmuka Streamlit.
                    st.error(message)
            # Menangani kesalahan jika proses sebelumnya gagal.
            except Exception as exc:
                # Menampilkan atau memproses bagian antarmuka Streamlit.
                st.error(db_error_message(exc))
    # Menampilkan atau memproses bagian antarmuka Streamlit.
    st.divider()


# Mengubah exception menjadi pesan yang aman ditampilkan kepada pengguna.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def db_error_message(exc: Exception) -> str:
    # Pesan umum menghindari kebocoran detail koneksi/kredensial.
    # Memeriksa apakah syarat ini benar.
    if isinstance(exc, (psycopg2.Error, RuntimeError)):
        # Mengembalikan hasil dari fungsi ini.
        return "Database tidak dapat diakses. Periksa Secrets dan pastikan skema SQL sudah dijalankan."
    # Mengembalikan hasil dari fungsi ini.
    return f"Terjadi kesalahan: {type(exc).__name__}. Silakan coba lagi."


# ---------- Kontak, pengiriman pesan, dan tampilan percakapan ----------
# Mencari pengguna berdasarkan ID dan menyimpan relasi kontak untuk kedua arah.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def add_contact(owner_id: str, target_id: str) -> tuple[bool, str]:
    # Menyimpan hasil proses ke dalam variabel.
    target_id = target_id.strip()
    # Memeriksa apakah syarat ini benar.
    if not target_id:
        # Mengembalikan hasil dari fungsi ini.
        return False, "Masukkan ID pengguna."
    # Menyimpan hasil proses ke dalam variabel.
    target = query_one(
        # Menambahkan teks atau potongan gambar ke hasil.
        "SELECT id, user_id FROM ascii_chat.users WHERE lower(user_id)=lower(%s)",
        # Menentukan nilai yang menjadi bagian dari data ini.
        (target_id,),
    # Menutup daftar nilai atau pemanggilan fungsi.
    )
    # Memeriksa apakah syarat ini benar.
    if not target:
        # Mengembalikan hasil dari fungsi ini.
        return False, "ID pengguna tidak ditemukan."
    # Memeriksa apakah syarat ini benar.
    if str(target["id"]) == owner_id:
        # Mengembalikan hasil dari fungsi ini.
        return False, "Kamu tidak bisa menambahkan ID sendiri."
    # Memanggil fungsi untuk menjalankan tugas tertentu.
    execute(
        # Menambahkan teks atau potongan gambar ke hasil.
        "INSERT INTO ascii_chat.contacts (owner_id, contact_id) VALUES (%s, %s), (%s, %s) "
        # Menambahkan teks atau potongan gambar ke hasil.
        "ON CONFLICT (owner_id, contact_id) DO NOTHING",
        # Menentukan nilai yang menjadi bagian dari data ini.
        (owner_id, str(target["id"]), str(target["id"]), owner_id),
    # Menutup daftar nilai atau pemanggilan fungsi.
    )
    # Mengembalikan hasil dari fungsi ini.
    return True, f"Kontak {target['user_id']} ditambahkan."


# Mengambil daftar kontak yang dimiliki pengguna.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def list_contacts(owner_id: str) -> list[dict]:
    # Mengembalikan hasil dari fungsi ini.
    return query_all(
        # Menambahkan teks atau potongan gambar ke hasil.
        "SELECT u.id::text AS id, u.user_id FROM ascii_chat.contacts c "
        # Menambahkan teks atau potongan gambar ke hasil.
        "JOIN ascii_chat.users u ON u.id=c.contact_id "
        # Menambahkan teks atau potongan gambar ke hasil.
        "WHERE c.owner_id=%s ORDER BY u.user_id",
        # Menentukan nilai yang menjadi bagian dari data ini.
        (owner_id,),
    # Menutup daftar nilai atau pemanggilan fungsi.
    )


# Mengambil maksimal 100 pesan di antara dua pengguna, dari yang lama ke yang baru.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def list_messages(owner_id: str, contact_id: str) -> list[dict]:
    # Mengembalikan hasil dari fungsi ini.
    return query_all(
        # Menambahkan teks atau potongan gambar ke hasil.
        "SELECT sender_id::text AS sender_id, recipient_id::text AS recipient_id, "
        # Menambahkan teks atau potongan gambar ke hasil.
        "body FROM ascii_chat.messages "
        # Menambahkan teks atau potongan gambar ke hasil.
        "WHERE (sender_id=%s AND recipient_id=%s) OR (sender_id=%s AND recipient_id=%s) "
        # Menambahkan teks atau potongan gambar ke hasil.
        "ORDER BY created_at DESC LIMIT 100",
        # Menentukan nilai yang menjadi bagian dari data ini.
        (owner_id, contact_id, contact_id, owner_id),
    # Menutup daftar nilai atau pemanggilan fungsi.
    )[::-1]


# Memvalidasi isi pesan, memastikan kedua pihak terhubung sebagai kontak, lalu menyimpan pesan.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def send_message(sender_id: str, recipient_id: str, body: str) -> tuple[bool, str]:
    # Bagian ini membantu menjalankan proses aplikasi.
    ok, reason = validate_message(body)
    # Memeriksa apakah syarat ini benar.
    if not ok:
        # Mengembalikan hasil dari fungsi ini.
        return False, reason
    # Menyimpan hasil proses ke dalam variabel.
    permitted = query_one(
        # Menambahkan teks atau potongan gambar ke hasil.
        "SELECT 1 FROM ascii_chat.contacts WHERE owner_id=%s AND contact_id=%s "
        # Menambahkan teks atau potongan gambar ke hasil.
        "UNION SELECT 1 FROM ascii_chat.contacts WHERE owner_id=%s AND contact_id=%s LIMIT 1",
        # Menentukan nilai yang menjadi bagian dari data ini.
        (sender_id, recipient_id, recipient_id, sender_id),
    # Menutup daftar nilai atau pemanggilan fungsi.
    )
    # Memeriksa apakah syarat ini benar.
    if not permitted:
        # Mengembalikan hasil dari fungsi ini.
        return False, "Tambahkan pengguna sebagai kontak sebelum mengirim pesan."
    # Memanggil fungsi untuk menjalankan tugas tertentu.
    execute(
        # Menambahkan teks atau potongan gambar ke hasil.
        "INSERT INTO ascii_chat.messages (sender_id, recipient_id, body) VALUES (%s, %s, %s)",
        # Menentukan nilai yang menjadi bagian dari data ini.
        (sender_id, recipient_id, body),
    # Menutup daftar nilai atau pemanggilan fungsi.
    )
    # Mengembalikan hasil dari fungsi ini.
    return True, "Pesan terkirim."


# Membuat tampilan utama chat: status akun, daftar kontak, dan percakapan terpilih.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def chat_page():
    # Menyimpan hasil proses ke dalam variabel.
    user = st.session_state["user"]

    # Tampilkan pemberitahuan setelah percakapan berhasil dihapus.
    if st.session_state.get("chat_notice"):
        st.success(st.session_state["chat_notice"])
        st.session_state["chat_notice"] = None

    # Menampilkan atau memproses bagian antarmuka Streamlit.
    st.title("ASCII Chat")
    # Bagian ini membantu menjalankan proses aplikasi.
    head1, head2 = st.columns([5, 1])
    # Bagian ini membantu menjalankan proses aplikasi.
    head1.caption(f"Masuk sebagai **{user['user_id']}**")
    # Memeriksa apakah syarat ini benar.
    if head2.button("Keluar", use_container_width=True):
        # Menampilkan atau memproses bagian antarmuka Streamlit.
        st.session_state["user"] = None
        # Menampilkan atau memproses bagian antarmuka Streamlit.
        st.session_state["active_contact"] = None
        # Menampilkan atau memproses bagian antarmuka Streamlit.
        st.rerun()
    # Bagian ini membantu menjalankan proses aplikasi.
    left, right = st.columns([1, 2.4], gap="large")

    # Membuka proses atau sumber daya yang akan ditutup otomatis.
    with left:
        # Menampilkan atau memproses bagian antarmuka Streamlit.
        st.subheader("Kontak")
        # Membuka proses atau sumber daya yang akan ditutup otomatis.
        with st.form("add_contact", clear_on_submit=True):
            # Menyimpan hasil proses ke dalam variabel.
            target = st.text_input("Tambah kontak · cari berdasarkan ID")
            # Menyimpan hasil proses ke dalam variabel.
            add = st.form_submit_button("Tambah kontak", use_container_width=True)
        # Memeriksa apakah syarat ini benar.
        if add:
            # Mencoba menjalankan bagian ini sambil menangani jika terjadi kesalahan.
            try:
                # Bagian ini membantu menjalankan proses aplikasi.
                ok, message = add_contact(user["id"], target)
                # Menentukan nilai yang menjadi bagian dari data ini.
                (st.success if ok else st.error)(message)
            # Menangani kesalahan jika proses sebelumnya gagal.
            except Exception as exc:
                # Menampilkan atau memproses bagian antarmuka Streamlit.
                st.error(db_error_message(exc))
        # Mencoba menjalankan bagian ini sambil menangani jika terjadi kesalahan.
        try:
            # Menyimpan hasil proses ke dalam variabel.
            contacts = list_contacts(user["id"])
        # Menangani kesalahan jika proses sebelumnya gagal.
        except Exception as exc:
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.error(db_error_message(exc))
            # Membuat daftar untuk menyimpan beberapa nilai.
            contacts = []
        # Memeriksa apakah syarat ini benar.
        if not contacts:
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.info("Belum ada kontak. Cari ID pengguna untuk memulai chat.")
        # Mengulang langkah ini untuk setiap item.
        for contact in contacts:
            # Menyimpan hasil proses ke dalam variabel.
            active = st.session_state["active_contact"] == contact["id"]
            # Memeriksa apakah syarat ini benar.
            if st.button(
                # Menentukan nilai yang menjadi bagian dari data ini.
                ("● " if active else "") + contact["user_id"],
                # Menyimpan hasil proses ke dalam variabel.
                key=f"contact_{contact['id']}", use_container_width=True,
            # Menutup daftar nilai atau pemanggilan fungsi.
            ):
                # Menampilkan atau memproses bagian antarmuka Streamlit.
                st.session_state["active_contact"] = contact["id"]
                # Menampilkan atau memproses bagian antarmuka Streamlit.
                st.rerun()

    # Membuka proses atau sumber daya yang akan ditutup otomatis.
    with right:
        # Menyimpan hasil proses ke dalam variabel.
        contact_id = st.session_state.get("active_contact")
        # Menyimpan hasil proses ke dalam variabel.
        selected = next((c for c in contacts if c["id"] == contact_id), None)
        # Memeriksa apakah syarat ini benar.
        if not selected:
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.subheader("Percakapan")
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.info("Pilih kontak di sebelah kiri untuk mulai mengobrol.")
        # Menjalankan bagian ini jika syarat sebelumnya tidak terpenuhi.
        else:
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.subheader(selected["user_id"])
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.caption("Pesan diperbarui otomatis setiap 2 detik.")
            # Memanggil fungsi untuk menjalankan tugas tertentu.
            render_conversation(user, selected)


# Menampilkan pesan secara berkala; setiap pesan bisa dibuka untuk melihat tabel ASCII dan grafik NRZ-I.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def render_conversation(user: dict, contact: dict):
    # Mengatur cara fungsi di bawahnya dijalankan.
    # @st.fragment(run_every="2s")
    # Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
    def conversation():
        # Mencoba menjalankan bagian ini sambil menangani jika terjadi kesalahan.
        try:
            # Menyimpan hasil proses ke dalam variabel.
            messages = list_messages(user["id"], contact["id"])
        # Menangani kesalahan jika proses sebelumnya gagal.
        except Exception as exc:
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.error(db_error_message(exc))
            # Membuat daftar untuk menyimpan beberapa nilai.
            messages = []
        # Mengulang langkah ini untuk setiap item.
        for msg in messages:
            # Menyimpan hasil proses ke dalam variabel.
            mine = msg["sender_id"] == user["id"]
            # Menyimpan hasil proses ke dalam variabel.
            align = "flex-end" if mine else "flex-start"
            # Menyimpan hasil proses ke dalam variabel.
            bubble = "#DDF7E8" if mine else "#F0F2F5"
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.markdown(
                # Menambahkan teks atau potongan gambar ke hasil.
                f'<div style="display:flex;justify-content:{align};margin:7px 0">'
                # Menambahkan teks atau potongan gambar ke hasil.
                f'<div style="max-width:82%;background:{bubble};padding:9px 12px;'
                # Menambahkan teks atau potongan gambar ke hasil.
                f'border-radius:12px;color:#202124;overflow-wrap:anywhere">'
                # Menambahkan teks atau potongan gambar ke hasil.
               #f'<div>{"*" * len(msg["body"])}</div>'
                # Menambahkan teks atau potongan gambar ke hasil.
                f'</div></div>',
                # Menyimpan hasil proses ke dalam variabel.
                unsafe_allow_html=True,
            # Menutup daftar nilai atau pemanggilan fungsi.
            )
            # Membuka proses atau sumber daya yang akan ditutup otomatis.
            with st.expander(f"Lihat sinyal · {len(msg['body'])} karakter"):
                # Menyiapkan daftar hasil yang akan ditampilkan.
                rows = signal_table(msg["body"])
                # Menampilkan atau memproses bagian antarmuka Streamlit.
                # st.dataframe(
                #     # Menentukan nilai yang menjadi bagian dari data ini.
                #     [{"Karakter": "spasi" if r["char"] == " " else r["char"],
                #       # Menambahkan teks atau potongan gambar ke hasil.
                #       "Kode ASCII (desimal)": r["ascii"], "Hex": r["hex"],
                #       # Menambahkan teks atau potongan gambar ke hasil.
                #       "Biner 7 bit (MSB dulu)": r["bits"],
                #       # Menambahkan teks atau potongan gambar ke hasil.
                #       "Parity Even": r["parity"], "End": r["end"]} for r in rows],
                #     # Menyimpan hasil proses ke dalam variabel.
                #     hide_index=True, use_container_width=True,
                # Menutup daftar nilai atau pemanggilan fungsi.
                # )
                # Menampilkan atau memproses bagian antarmuka Streamlit.
                st.subheader("NRZ-I")
                # Memanggil fungsi untuk menjalankan tugas tertentu.
                show_signal(msg["body"])

        # Membuka proses atau sumber daya yang akan ditutup otomatis.
        with st.form(f"send_{contact['id']}", clear_on_submit=True):
            # Menyimpan hasil proses ke dalam variabel.
            body = st.text_input("Pesan", max_chars=2000, key=f"body_{contact['id']}")
            # Menyimpan hasil proses ke dalam variabel.
            sent = st.form_submit_button("Kirim", use_container_width=True)
        # Memeriksa apakah syarat ini benar.
        if sent:
            # Mencoba menjalankan bagian ini sambil menangani jika terjadi kesalahan.
            try:
                # Bagian ini membantu menjalankan proses aplikasi.
                ok, message = send_message(user["id"], contact["id"], body)
                # Memeriksa apakah syarat ini benar.
                if ok:
                    # Menampilkan atau memproses bagian antarmuka Streamlit.
                    st.rerun()
                # Menjalankan bagian ini jika syarat sebelumnya tidak terpenuhi.
                else:
                    # Menampilkan atau memproses bagian antarmuka Streamlit.
                    st.error(message)
            # Menangani kesalahan jika proses sebelumnya gagal.
            except Exception as exc:
                # Menampilkan atau memproses bagian antarmuka Streamlit.
                st.error(db_error_message(exc))
    # Memanggil fungsi untuk menjalankan tugas tertentu.
    conversation()


# Panel uji mandiri: periksa kode ASCII karakter dan tampilkan sinyal jika teks valid.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def ascii_test_panel():
    # Menampilkan atau memproses bagian antarmuka Streamlit.
    st.subheader("Uji karakter")
    # Menyimpan hasil proses ke dalam variabel.
    sample = st.text_input("Ketik teks untuk menguji ASCII", key="ascii_test", placeholder="Contoh: IBNU")
    # Memeriksa apakah syarat ini benar.
    if sample:
        # Membuat daftar untuk menyimpan beberapa nilai.
        rows = []
        # Mengulang langkah ini untuk setiap item.
        for item in inspect_ascii(sample):
            # Memeriksa apakah syarat ini benar.
            if item["supported"]:
                # Menyimpan hasil proses ke dalam variabel.
                enc = encode_character(item["char"])
                # Bagian ini membantu menjalankan proses aplikasi.
                rows.append({
                    # Menambahkan teks atau potongan gambar ke hasil.
                    "Karakter": "spasi" if item["char"] == " " else item["char"],
                    # Menambahkan teks atau potongan gambar ke hasil.
                    "Kode ASCII (desimal)": item["code"], "Hex": enc["hex"],
                    # Menambahkan teks atau potongan gambar ke hasil.
                    "Biner 7 bit (MSB dulu)": enc["bits"], "Parity Even": enc["parity"],
                    # Menambahkan teks atau potongan gambar ke hasil.
                    "Status": "didukung",
                # Menutup daftar nilai atau pemanggilan fungsi.
                })
            # Menjalankan bagian ini jika syarat sebelumnya tidak terpenuhi.
            else:
                # Bagian ini membantu menjalankan proses aplikasi.
                rows.append({
                    # Menambahkan teks atau potongan gambar ke hasil.
                    "Karakter": repr(item["char"]), "Kode ASCII (desimal)": item["code"],
                    # Menambahkan teks atau potongan gambar ke hasil.
                    "Hex": f"{item['code']:02X}", "Biner 7 bit (MSB dulu)": "—",
                    # Menambahkan teks atau potongan gambar ke hasil.
                    "Parity Even": "—",
                    # Menambahkan teks atau potongan gambar ke hasil.
                    "Status": f"{item['reason']} (U+{item['code']:04X})",
                # Menutup daftar nilai atau pemanggilan fungsi.
                })
        # Menampilkan atau memproses bagian antarmuka Streamlit.
        st.dataframe(rows, hide_index=True, use_container_width=True)
        # Bagian ini membantu menjalankan proses aplikasi.
        ok, reason = validate_message(sample)
        # Memeriksa apakah syarat ini benar.
        if ok:
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.success("Semua karakter didukung oleh ASCII tercetak.")
            # Membuka proses atau sumber daya yang akan ditutup otomatis.
            with st.expander("Lihat sinyal NRZ-I untuk teks uji"):
                # Memanggil fungsi untuk menjalankan tugas tertentu.
                show_signal(sample)
        # Menjalankan bagian ini jika syarat sebelumnya tidak terpenuhi.
        else:
            # Menampilkan atau memproses bagian antarmuka Streamlit.
            st.warning(reason)


# Titik masuk aplikasi: siapkan sesi, lalu tampilkan halaman login atau halaman chat.
# Membuat fungsi untuk menjalankan tugas yang disebut pada namanya.
def main():
    # Memanggil fungsi untuk menjalankan tugas tertentu.
    init_state()
    # Memeriksa apakah syarat ini benar.
    if st.session_state["user"] is None:
        # Memanggil fungsi untuk menjalankan tugas tertentu.
        auth_page()
    # Menjalankan bagian ini jika syarat sebelumnya tidak terpenuhi.
    else:
        # Memanggil fungsi untuk menjalankan tugas tertentu.
        chat_page()
        # Menampilkan atau memproses bagian antarmuka Streamlit.
        st.divider()
        # Memanggil fungsi untuk menjalankan tugas tertentu.
        ascii_test_panel()


# Menjalankan bagian utama hanya saat file dibuka langsung.
if __name__ == "__main__":
    # Memanggil fungsi untuk menjalankan tugas tertentu.
    main()
