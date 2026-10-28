"""Chat realtime untuk praktikum Komunikasi Data — ASCII 7 bit dan NRZ-I."""
from __future__ import annotations

import html
import re
import uuid
from datetime import datetime
from typing import Any

import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(page_title="ASCII Chat | Komunikasi Data", page_icon="💬", layout="wide")


# ---------- Koneksi dan sesi ----------
def db_connect():
    """Buka koneksi PostgreSQL menggunakan URL rahasia dari Streamlit Secrets."""
    try:
        database_url = st.secrets["database"]["url"]
    except Exception as exc:
        raise RuntimeError(
            "Rahasia database belum diatur. Tambahkan [database] url pada Secrets."
        ) from exc
    return psycopg2.connect(database_url, connect_timeout=10, cursor_factory=RealDictCursor)


def query_one(sql: str, params: tuple = ()) -> Any:
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def execute(sql: str, params: tuple = ()) -> None:
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def init_state():
    defaults = {
        "user": None, "active_contact": None, "auth_tab": "Masuk",
        "register_ok": False, "flash": None, "message_draft": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------- Validasi ASCII dan encoding ----------
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


def encode_character(char: str) -> dict:
    value = ord(char)
    bits = f"{value:07b}"
    parity = bits.count("1") % 2  # parity bit membuat jumlah 1 genap
    frame = "0" + bits + str(parity) + "1"
    return {
        "char": char, "hex": f"{value:02X}", "bits": bits,
        "parity": parity, "end": 1, "frame": frame,
    }


def signal_table(text: str) -> list[dict]:
    return [encode_character(ch) for ch in text]


# ---------- Penggambar sinyal SVG ----------
def nrzi_svg(text: str, initial_high: bool = False) -> str:
    """SVG NRZ-I: 1 membalik level di awal bit; 0 mempertahankan level."""
    if not text:
        return '<p style="font:14px sans-serif;color:#777">Belum ada karakter untuk divisualisasikan.</p>'

    frames = signal_table(text)
    bits = "".join(item["frame"] for item in frames)
    start_level = 1 if initial_high else 0
    level = start_level
    levels = []
    for bit in bits:
        if bit == "1":
            level = 1 - level
        levels.append(level)

    bit_w, left, top = 42, 24, 72
    high_y, low_y = 108, 168
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

    # Batas frame dan judul tiap karakter.
    for i, frame in enumerate(frames):
        x = left + i * 10 * bit_w
        char_label = "spasi" if frame["char"] == " " else f"Huruf {frame['char']}"
        parts.append(
            f'<text class="frame-title" x="{x + 5*bit_w}" y="24" text-anchor="middle">'
            f'{html.escape(char_label)}</text>'
        )
        if i > 0:
            parts.append(f'<line x1="{x}" y1="34" x2="{x}" y2="224" stroke="#555" stroke-width="2.5"/>')

    # Kolom bit tipis dan label bit.
    for i, bit in enumerate(bits):
        x = left + i * bit_w
        parts.append(f'<line x1="{x}" y1="36" x2="{x}" y2="224" stroke="#d9d9d9" stroke-width="1"/>')
        parts.append(
            f'<text class="bit" x="{x+bit_w/2}" y="205" text-anchor="middle">{bit}</text>'
        )
    parts.append(f'<line x1="{left+plot_w}" y1="36" x2="{left+plot_w}" y2="224" stroke="#d9d9d9" stroke-width="1"/>')

    # Gelombang siku: level sebelumnya dipertahankan hingga tepi bit,
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

    # Kurung/kelompok S, Data, P, E berada tepat di kolom masing-masing.
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


def show_signal(text: str):
    level_choice = st.selectbox(
        "Level awal NRZ-I", ["Rendah (-V)", "Tinggi (+V)"],
        key=f"level_{st.session_state.get('active_contact')}_{hash(text)}",
        help="Level akhir satu frame diteruskan ke frame berikutnya.",
    )
    svg = nrzi_svg(text, initial_high=level_choice == "Tinggi (+V)")
    components.html(
        f'<div style="overflow-x:auto;max-width:100%;padding:8px 0">{svg}</div>',
        height=330, scrolling=True,
    )


# ---------- Autentikasi ----------
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


def login_user(user_id: str, email: str, password: str) -> tuple[bool, str, dict | None]:
    row = query_one(
        "SELECT id, user_id, email, password_hash FROM ascii_chat.users "
        "WHERE lower(user_id)=lower(%s) AND lower(email)=lower(%s)",
        (user_id.strip(), email.strip().lower()),
    )
    if not row or not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        return False, "ID, email, atau password tidak cocok.", None
    return True, "Berhasil masuk.", {"id": str(row["id"]), "user_id": row["user_id"], "email": row["email"]}


def auth_page():
    st.title("ASCII Chat")
    st.caption("Praktikum Komunikasi Data · Chat satu lawan satu")
    tab_daftar, tab_masuk = st.tabs(["Daftar", "Masuk"])
    with tab_daftar:
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
                    st.success(message)
                    st.session_state["auth_tab"] = "Masuk"
                    st.info("Buka tab Masuk untuk melanjutkan.")
                else:
                    st.error(message)
            except Exception as exc:
                st.error(db_error_message(exc))
    with tab_masuk:
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
    st.caption("Encoding: ASCII 7 bit. ANSI, UTF-8, dan UTF-16 tidak didukung sebagai encoding aplikasi.")


def db_error_message(exc: Exception) -> str:
    # Pesan umum menghindari kebocoran detail koneksi/kredensial.
    if isinstance(exc, (psycopg2.Error, RuntimeError)):
        return "Database tidak dapat diakses. Periksa Secrets dan pastikan skema SQL sudah dijalankan."
    return f"Terjadi kesalahan: {type(exc).__name__}. Silakan coba lagi."


# ---------- Kontak dan percakapan ----------
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
        "INSERT INTO ascii_chat.contacts (owner_id, contact_id) VALUES (%s, %s) "
        "ON CONFLICT (owner_id, contact_id) DO NOTHING",
        (owner_id, str(target["id"])),
    )
    return True, f"Kontak {target['user_id']} ditambahkan."


def list_contacts(owner_id: str) -> list[dict]:
    return query_all(
        "SELECT u.id::text AS id, u.user_id FROM ascii_chat.contacts c "
        "JOIN ascii_chat.users u ON u.id=c.contact_id "
        "WHERE c.owner_id=%s ORDER BY u.user_id",
        (owner_id,),
    )


def list_messages(owner_id: str, contact_id: str) -> list[dict]:
    return query_all(
        "SELECT id, sender_id::text AS sender_id, recipient_id::text AS recipient_id, "
        "body, created_at FROM ascii_chat.messages "
        "WHERE (sender_id=%s AND recipient_id=%s) OR (sender_id=%s AND recipient_id=%s) "
        "ORDER BY created_at DESC LIMIT 100",
        (owner_id, contact_id, contact_id, owner_id),
    )[::-1]


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


def chat_page():
    user = st.session_state["user"]
    st.title("ASCII Chat")
    head1, head2 = st.columns([5, 1])
    head1.caption(f"Masuk sebagai **{user['user_id']}**")
    if head2.button("Keluar", use_container_width=True):
        st.session_state["user"] = None
        st.session_state["active_contact"] = None
        st.rerun()
    st.caption("Encoding: ASCII 7 bit. ANSI, UTF-8, dan UTF-16 tidak didukung sebagai encoding aplikasi.")
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
            timestamp = msg["created_at"]
            if isinstance(timestamp, datetime):
                timestamp = timestamp.astimezone().strftime("%H:%M")
            else:
                timestamp = str(timestamp)[11:16]
            st.markdown(
                f'<div style="display:flex;justify-content:{align};margin:7px 0">'
                f'<div style="max-width:82%;background:{bubble};padding:9px 12px;'
                f'border-radius:12px;color:#202124;overflow-wrap:anywhere">'
                f'<div>{html.escape(msg["body"])}</div>'
                f'<div style="font-size:11px;text-align:right;color:#667085;margin-top:4px">{timestamp}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            with st.expander(f"Lihat sinyal · {timestamp} · {len(msg['body'])} karakter"):
                rows = signal_table(msg["body"])
                st.dataframe(
                    [{"Karakter": r["char"], "Hex": r["hex"], "Biner 7 bit (MSB dulu)": r["bits"],
                      "Parity Even": r["parity"], "End": r["end"]} for r in rows],
                    hide_index=True, use_container_width=True,
                )
                st.caption("NRZ-I: bit 1 membalik level di awal bit; bit 0 mempertahankan level.")
                show_signal(msg["body"])

        with st.form(f"send_{contact['id']}", clear_on_submit=True):
            body = st.text_input("Pesan (hanya ASCII tercetak)", max_chars=2000, key=f"body_{contact['id']}")
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
                    "Desimal": item["code"], "Hex": enc["hex"],
                    "Biner 7 bit (MSB dulu)": enc["bits"], "Parity Even": enc["parity"],
                    "Status": "didukung",
                })
            else:
                rows.append({
                    "Karakter": repr(item["char"]), "Desimal": item["code"],
                    "Hex": f"{item['code']:02X}", "Biner 7 bit (MSB dulu)": "—",
                    "Parity Even": "—",
                    "Status": f"{item['reason']} (U+{item['code']:04X})",
                })
        st.dataframe(rows, hide_index=True, use_container_width=True)
        ok, reason = validate_message(sample)
        if ok:
            st.success("Semua karakter didukung oleh ASCII tercetak.")
            with st.expander("Lihat sinyal NRZ-I untuk teks uji"):
                show_signal(sample)
        else:
            st.warning(reason)


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
