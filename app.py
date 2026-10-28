"""Chat realtime untuk praktikum Komunikasi Data — ASCII 7 bit dan NRZ-I."""
from __future__ import annotations

import html
import re
from contextlib import closing
import uuid
from datetime import datetime
from typing import Any

import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(page_title="ASCII Chat | Komunikasi Data", page_icon="💬", layout="wide")


# ---------- Koneksi database dan sesi pengguna ----------
# Bagian ini mengatur koneksi PostgreSQL dan data sesi Streamlit.
# Membuat koneksi ke database Supabase PostgreSQL dari Streamlit Secrets.
def db_connect():
    """Buka koneksi PostgreSQL menggunakan URL rahasia dari Streamlit Secrets."""
    try:
        database_url = st.secrets["database"]["url"]
    except Exception as exc:
        raise RuntimeError(
            "Rahasia database belum diatur. Tambahkan [database] url pada Secrets."
        ) from exc
    return psycopg2.connect(database_url, connect_timeout=10, cursor_factory=RealDictCursor)


# Menjalankan SQL yang menghasilkan satu baris data, misalnya pencarian pengguna.
def query_one(sql: str, params: tuple = ()) -> Any:
    with closing(db_connect()) as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()


# Menjalankan SQL yang menghasilkan banyak baris data, misalnya daftar pesan.
def query_all(sql: str, params: tuple = ()) -> list[dict]:
    with closing(db_connect()) as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())


# Menjalankan SQL perubahan data yang tidak perlu mengembalikan baris.
def execute(sql: str, params: tuple = ()) -> None:
    with closing(db_connect()) as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)


# Menyiapkan nilai awal session_state agar status login dan chat tetap terjaga saat UI diperbarui.
def init_state():
    defaults = {
        "user": None, "active_contact": None, "auth_tab": "Masuk",
        "register_ok": False, "flash": None, "message_draft": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------- Pemeriksaan karakter, konversi ASCII, dan pembentukan frame ----------
# Bagian ini mengubah karakter menjadi kode ASCII dan bit untuk dikirim sebagai frame.
# Memeriksa setiap karakter dan menandai apakah termasuk ASCII tercetak (kode 32–126).
def inspect_ascii(text: str) -> list[dict]:
    rows = []
    for char in text:
        code = ord(char)
        supported = 32 <= code <= 126
        rows.append({
            "char": char, "code": code, "supported": supported,
            "reason": "" if supported else (
                "karakter kontrol" if code < 32 or code == 127
                else "tidak didukung (kode > 127)"
            ),
        })
    return rows


# Memastikan pesan tidak kosong dan semua karakternya didukung sebelum dikirim.
def validate_message(text: str) -> tuple[bool, str]:
    if not text:
        return False, "Pesan tidak boleh kosong."
    for char in text:
        code = ord(char)
        if not 32 <= code <= 126:
            return False, (
                f"Karakter {char!r} (U+{code:04X}) tidak didukung. "
                "Hanya ASCII 7 bit (kode 32-126)."
            )
    return True, ""


# KONVERSI ASCII: ord() mengambil kode desimal; format biner menghasilkan 7 bit (MSB lebih dulu).
# Lalu dibuat parity genap dan frame: Start bit 0 + 7 bit data + parity + End bit 1.
def encode_character(char: str) -> dict:
    value = ord(char)  # Karakter -> kode ASCII desimal.
    bits = f"{value:07b}"  # Kode desimal -> representasi biner 7 bit.
    parity = bits.count("1") % 2  # Parity genap: total bit 1 termasuk parity menjadi genap.
    frame = "0" + bits + str(parity) + "1"  # Susunan frame: Start + Data + Parity + End.
    return {
        "char": char, "ascii": value, "hex": f"{value:02X}", "bits": bits,
        "parity": parity, "end": 1, "frame": frame,
    }


# Membuat tabel encoding dengan memanggil encode_character() untuk setiap karakter.
def signal_table(text: str) -> list[dict]:
    return [encode_character(ch) for ch in text]


# ---------- Logika NRZ-I dan penggambaran sinyal ----------
# Bagian ini mengubah urutan bit menjadi level tegangan, lalu menggambarnya sebagai SVG.
# Membentuk grafik NRZ-I dalam SVG berdasarkan bit frame setiap karakter.
def nrzi_svg(text: str, initial_high: bool = False) -> str:
    """SVG NRZ-I: 1 membalik level di awal bit; 0 mempertahankan level."""
    if not text:
        return '<p style="font:14px sans-serif;color:#777">Belum ada karakter untuk divisualisasikan.</p>'

    frames = signal_table(text)  # Encode tiap karakter menjadi frame bit.
    bits = "".join(item["frame"] for item in frames)  # Gabungkan semua frame menjadi satu aliran bit.
    start_level = 1 if initial_high else 0  # Level awal: rendah (0) karena initial_high=False.
    level = start_level
    levels = []
    # LOGIKA NRZ-I: bit 1 membalik level tegangan; bit 0 mempertahankan level sebelumnya.
    for bit in bits:
        if bit == "1":
            level = 1 - level  # 0 -> 1 atau 1 -> 0.
        levels.append(level)  # Simpan level untuk digambar pada kolom bit ini.

    bit_w, left, top = 42, 24, 72
    high_y, low_y = 96, 168  # Posisi level +V dinaikkan sedikit agar grafik lebih lega.
    plot_w = bit_w * len(bits)
    width = left * 2 + plot_w
    height = 300
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="Sinyal NRZ-I">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#252525}.bit{font-size:14px}.label{font-size:12px}.frame-title{font-size:13px;font-weight:600}</style>',
        f'<text x="4" y="{high_y+4}" font-size="12">+V</text>',
        f'<text x="4" y="{low_y+4}" font-size="12">-V</text>',
    ]

    # VISUALISASI: tandai batas frame dan beri judul untuk setiap karakter.
    for i, frame in enumerate(frames):
        x = left + i * 10 * bit_w
        char_label = "spasi" if frame["char"] == " " else f"Huruf {frame['char']}"
        parts.append(
            f'<text class="frame-title" x="{x + 5*bit_w}" y="24" text-anchor="middle">'
            f'{html.escape(char_label)}</text>'
        )
        if i > 0:
            parts.append(f'<line x1="{x}" y1="34" x2="{x}" y2="224" stroke="#555" stroke-width="2.5"/>')

    # VISUALISASI: gambar garis pembatas kolom dan label 0/1 di bawah grafik.
    for i, bit in enumerate(bits):
        x = left + i * bit_w
        parts.append(f'<line x1="{x}" y1="36" x2="{x}" y2="224" stroke="#d9d9d9" stroke-width="1"/>')
        parts.append(
            f'<text class="bit" x="{x+bit_w/2}" y="205" text-anchor="middle">{bit}</text>'
        )
    parts.append(f'<line x1="{left+plot_w}" y1="36" x2="{left+plot_w}" y2="224" stroke="#d9d9d9" stroke-width="1"/>')

    # VISUALISASI GELOMBANG: bentuk garis siku dari level NRZ-I yang sudah dihitung.
    # Level sebelumnya dipertahankan hingga tepi bit,
    # lalu bit 1 membalik level tepat di awal kolom bit tersebut.
    y_prev = high_y if start_level else low_y
    points = [f"{left},{y_prev}"]
    for i, level_now in enumerate(levels):
        x = left + i * bit_w
        y_now = high_y if level_now else low_y
        if i == 0 and y_now != y_prev:
            points.append(f"{x},{y_now}")
        elif y_now != y_prev:
            points.append(f"{x},{y_now}")
        points.append(f"{x+bit_w},{y_now}")
        y_prev = y_now
    parts.append(
        '<polyline points="' + " ".join(points) +
        '" fill="none" stroke="#1D9E75" stroke-width="4" stroke-linejoin="miter" stroke-linecap="square"/>'
    )

    # VISUALISASI FRAME: beri label Start (S), Data, Parity (P), dan End (E) di bawah bit.
    for i, frame in enumerate(frames):
        x = left + i * 10 * bit_w
        groups = [(0, 1, "S"), (1, 8, f'Data "{html.escape(frame["char"])}"'), (8, 9, "P"), (9, 10, "E")]
        for a, b, label in groups:
            gx1, gx2 = x + a * bit_w + 2, x + b * bit_w - 2
            gy = 238
            parts.append(
                f'<path d="M {gx1} {gy} v 6 H {gx2} v -6" fill="none" stroke="#777" stroke-width="1"/>'
            )
            parts.append(
                f'<text class="label" x="{(gx1+gx2)/2}" y="263" text-anchor="middle">{label}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


# Menampilkan SVG NRZ-I di halaman Streamlit; level awal dipatok rendah.
def show_signal(text: str, key_suffix: str = "signal"):
    # Level awal selalu rendah; tidak perlu menampilkan pilihan level ke pengguna.
    svg = nrzi_svg(text, initial_high=False)
    components.html(
        f'<div style="overflow-x:auto;max-width:100%;padding:8px 0">{svg}</div>',
        height=330, scrolling=True,
    )


# ---------- Pendaftaran, login, dan pesan kesalahan ----------
# Password disimpan sebagai hash bcrypt, bukan teks asli.
# Memvalidasi data pendaftaran, mengecek duplikasi, lalu menyimpan akun dengan hash password.
def register_user(user_id: str, email: str, password: str, confirm: str) -> tuple[bool, str]:
    user_id, email = user_id.strip(), email.strip().lower()
    if not re.fullmatch(r"[A-Za-z0-9_]{3,24}", user_id):
        return False, "ID pengguna harus 3–24 karakter: huruf, angka, atau garis bawah."
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return False, "Format email tidak valid."
    if len(password) < 6:
        return False, "Password minimal 6 karakter."
    if password != confirm:
        return False, "Konfirmasi password tidak sama."
    exists = query_one(
        "SELECT user_id FROM ascii_chat.users WHERE lower(user_id)=lower(%s) OR lower(email)=lower(%s)",
        (user_id, email),
    )
    if exists:
        return False, "ID pengguna atau email sudah digunakan."
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    query_one(
        "INSERT INTO ascii_chat.users (user_id, email, password_hash) "
        "VALUES (%s, %s, %s) RETURNING id",
        (user_id, email, hashed),
    )
    return True, "Pendaftaran berhasil. Silakan masuk menggunakan ID, email, dan password."


# Mencari akun berdasarkan ID dan email, lalu mencocokkan password dengan hash bcrypt.
def login_user(user_id: str, email: str, password: str) -> tuple[bool, str, dict | None]:
    row = query_one(
        "SELECT id, user_id, email, password_hash FROM ascii_chat.users "
        "WHERE lower(user_id)=lower(%s) AND lower(email)=lower(%s)",
        (user_id.strip(), email.strip().lower()),
    )
    if not row or not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        return False, "ID, email, atau password tidak cocok.", None
    return True, "Berhasil masuk.", {"id": str(row["id"]), "user_id": row["user_id"], "email": row["email"]}


# Menggambar UI daftar/masuk dan memproses hasil pengiriman form autentikasi.
def auth_page():
    st.title("ASCII Chat")
    st.caption("Praktikum Komunikasi Data · Chat satu lawan satu")
    auth_tab = st.radio(
        "Autentikasi", ["Daftar", "Masuk"], horizontal=True,
        label_visibility="collapsed", key="auth_tab",
    )
    if auth_tab == "Daftar":
        with st.form("form_daftar", clear_on_submit=True):
            new_id = st.text_input("ID pengguna", max_chars=24)
            new_email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Konfirmasi password", type="password")
            submitted = st.form_submit_button("Daftar", use_container_width=True)
        if submitted:
            try:
                ok, message = register_user(new_id, new_email, password, confirm)
                if ok:
                    st.session_state["flash"] = message
                    st.session_state["auth_tab"] = "Masuk"
                    st.rerun()
                else:
                    st.error(message)
            except Exception as exc:
                st.error(db_error_message(exc))
    else:
        if st.session_state.get("flash"):
            st.success(st.session_state["flash"])
            st.session_state["flash"] = None
        with st.form("form_masuk"):
            user_id = st.text_input("ID pengguna", key="login_id")
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Masuk", use_container_width=True)
        if submitted:
            try:
                ok, message, user = login_user(user_id, email, password)
                if ok:
                    st.session_state["user"] = user
                    st.session_state["active_contact"] = None
                    st.rerun()
                else:
                    st.error(message)
            except Exception as exc:
                st.error(db_error_message(exc))
    st.divider()


# Mengubah exception menjadi pesan yang aman ditampilkan kepada pengguna.
def db_error_message(exc: Exception) -> str:
    # Pesan umum menghindari kebocoran detail koneksi/kredensial.
    if isinstance(exc, (psycopg2.Error, RuntimeError)):
        return "Database tidak dapat diakses. Periksa Secrets dan pastikan skema SQL sudah dijalankan."
    return f"Terjadi kesalahan: {type(exc).__name__}. Silakan coba lagi."


# ---------- Kontak, pengiriman pesan, dan tampilan percakapan ----------
# Mencari pengguna berdasarkan ID dan menyimpan relasi kontak untuk kedua arah.
def add_contact(owner_id: str, target_id: str) -> tuple[bool, str]:
    target_id = target_id.strip()
    if not target_id:
        return False, "Masukkan ID pengguna."
    target = query_one(
        "SELECT id, user_id FROM ascii_chat.users WHERE lower(user_id)=lower(%s)",
        (target_id,),
    )
    if not target:
        return False, "ID pengguna tidak ditemukan."
    if str(target["id"]) == owner_id:
        return False, "Kamu tidak bisa menambahkan ID sendiri."
    execute(
        "INSERT INTO ascii_chat.contacts (owner_id, contact_id) VALUES (%s, %s), (%s, %s) "
        "ON CONFLICT (owner_id, contact_id) DO NOTHING",
        (owner_id, str(target["id"]), str(target["id"]), owner_id),
    )
    return True, f"Kontak {target['user_id']} ditambahkan."


# Mengambil daftar kontak yang dimiliki pengguna.
def list_contacts(owner_id: str) -> list[dict]:
    return query_all(
        "SELECT u.id::text AS id, u.user_id FROM ascii_chat.contacts c "
        "JOIN ascii_chat.users u ON u.id=c.contact_id "
        "WHERE c.owner_id=%s ORDER BY u.user_id",
        (owner_id,),
    )


# Mengambil maksimal 100 pesan di antara dua pengguna, dari yang lama ke yang baru.
def list_messages(owner_id: str, contact_id: str) -> list[dict]:
    return query_all(
        "SELECT id, sender_id::text AS sender_id, recipient_id::text AS recipient_id, "
        "body, created_at FROM ascii_chat.messages "
        "WHERE (sender_id=%s AND recipient_id=%s) OR (sender_id=%s AND recipient_id=%s) "
        "ORDER BY created_at DESC LIMIT 100",
        (owner_id, contact_id, contact_id, owner_id),
    )[::-1]


# Memvalidasi isi pesan, memastikan kedua pihak terhubung sebagai kontak, lalu menyimpan pesan.
def send_message(sender_id: str, recipient_id: str, body: str) -> tuple[bool, str]:
    ok, reason = validate_message(body)
    if not ok:
        return False, reason
    permitted = query_one(
        "SELECT 1 FROM ascii_chat.contacts WHERE owner_id=%s AND contact_id=%s "
        "UNION SELECT 1 FROM ascii_chat.contacts WHERE owner_id=%s AND contact_id=%s LIMIT 1",
        (sender_id, recipient_id, recipient_id, sender_id),
    )
    if not permitted:
        return False, "Tambahkan pengguna sebagai kontak sebelum mengirim pesan."
    execute(
        "INSERT INTO ascii_chat.messages (sender_id, recipient_id, body) VALUES (%s, %s, %s)",
        (sender_id, recipient_id, body),
    )
    return True, "Pesan terkirim."


# Membuat tampilan utama chat: status akun, daftar kontak, dan percakapan terpilih.
def chat_page():
    user = st.session_state["user"]
    st.title("ASCII Chat")
    head1, head2 = st.columns([5, 1])
    head1.caption(f"Masuk sebagai **{user['user_id']}**")
    if head2.button("Keluar", use_container_width=True):
        st.session_state["user"] = None
        st.session_state["active_contact"] = None
        st.rerun()
    left, right = st.columns([1, 2.4], gap="large")

    with left:
        st.subheader("Kontak")
        with st.form("add_contact", clear_on_submit=True):
            target = st.text_input("Tambah kontak · cari berdasarkan ID")
            add = st.form_submit_button("Tambah kontak", use_container_width=True)
        if add:
            try:
                ok, message = add_contact(user["id"], target)
                (st.success if ok else st.error)(message)
            except Exception as exc:
                st.error(db_error_message(exc))
        try:
            contacts = list_contacts(user["id"])
        except Exception as exc:
            st.error(db_error_message(exc))
            contacts = []
        if not contacts:
            st.info("Belum ada kontak. Cari ID pengguna untuk memulai chat.")
        for contact in contacts:
            active = st.session_state["active_contact"] == contact["id"]
            if st.button(
                ("● " if active else "") + contact["user_id"],
                key=f"contact_{contact['id']}", use_container_width=True,
            ):
                st.session_state["active_contact"] = contact["id"]
                st.rerun()

    with right:
        contact_id = st.session_state.get("active_contact")
        selected = next((c for c in contacts if c["id"] == contact_id), None)
        if not selected:
            st.subheader("Percakapan")
            st.info("Pilih kontak di sebelah kiri untuk mulai mengobrol.")
        else:
            st.subheader(selected["user_id"])
            st.caption("Pesan diperbarui otomatis setiap 2 detik.")
            render_conversation(user, selected)


# Menampilkan pesan secara berkala; setiap pesan bisa dibuka untuk melihat tabel ASCII dan grafik NRZ-I.
def render_conversation(user: dict, contact: dict):
    @st.fragment(run_every="2s")
    def conversation():
        try:
            messages = list_messages(user["id"], contact["id"])
        except Exception as exc:
            st.error(db_error_message(exc))
            messages = []
        for msg in messages:
            mine = msg["sender_id"] == user["id"]
            align = "flex-end" if mine else "flex-start"
            bubble = "#DDF7E8" if mine else "#F0F2F5"
            st.markdown(
                f'<div style="display:flex;justify-content:{align};margin:7px 0">'
                f'<div style="max-width:82%;background:{bubble};padding:9px 12px;'
                f'border-radius:12px;color:#202124;overflow-wrap:anywhere">'
                f'<div>{html.escape(msg["body"])}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            with st.expander(f"Lihat sinyal · {len(msg['body'])} karakter"):
                rows = signal_table(msg["body"])
                st.dataframe(
                    [{"Karakter": "spasi" if r["char"] == " " else r["char"],
                      "Kode ASCII (desimal)": r["ascii"], "Hex": r["hex"],
                      "Biner 7 bit (MSB dulu)": r["bits"],
                      "Parity Even": r["parity"], "End": r["end"]} for r in rows],
                    hide_index=True, use_container_width=True,
                )
                st.subheader("NRZ-I")
                show_signal(msg["body"], key_suffix=f"message_{msg['id']}")

        with st.form(f"send_{contact['id']}", clear_on_submit=True):
            body = st.text_input("Pesan", max_chars=2000, key=f"body_{contact['id']}")
            sent = st.form_submit_button("Kirim", use_container_width=True)
        if sent:
            try:
                ok, message = send_message(user["id"], contact["id"], body)
                if ok:
                    st.rerun()
                else:
                    st.error(message)
            except Exception as exc:
                st.error(db_error_message(exc))
    conversation()


# Panel uji mandiri: periksa kode ASCII karakter dan tampilkan sinyal jika teks valid.
def ascii_test_panel():
    st.subheader("Uji karakter")
    sample = st.text_input("Ketik teks untuk menguji ASCII", key="ascii_test", placeholder="Contoh: IBNU")
    if sample:
        rows = []
        for item in inspect_ascii(sample):
            if item["supported"]:
                enc = encode_character(item["char"])
                rows.append({
                    "Karakter": "spasi" if item["char"] == " " else item["char"],
                    "Kode ASCII (desimal)": item["code"], "Hex": enc["hex"],
                    "Biner 7 bit (MSB dulu)": enc["bits"], "Parity Even": enc["parity"],
                    "Status": "didukung",
                })
            else:
                rows.append({
                    "Karakter": repr(item["char"]), "Kode ASCII (desimal)": item["code"],
                    "Hex": f"{item['code']:02X}", "Biner 7 bit (MSB dulu)": "—",
                    "Parity Even": "—",
                    "Status": f"{item['reason']} (U+{item['code']:04X})",
                })
        st.dataframe(rows, hide_index=True, use_container_width=True)
        ok, reason = validate_message(sample)
        if ok:
            st.success("Semua karakter didukung oleh ASCII tercetak.")
            with st.expander("Lihat sinyal NRZ-I untuk teks uji"):
                show_signal(sample, key_suffix="ascii_test")
        else:
            st.warning(reason)


# Titik masuk aplikasi: siapkan sesi, lalu tampilkan halaman login atau halaman chat.
def main():
    init_state()
    if st.session_state["user"] is None:
        auth_page()
    else:
        chat_page()
        st.divider()
        ascii_test_panel()


if __name__ == "__main__":
    main()
