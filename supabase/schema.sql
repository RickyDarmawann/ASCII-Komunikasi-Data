-- Jalankan di Supabase SQL Editor pada project Komunikasi-Data.
-- Skema terpisah supaya tabel public.messages/profiles dari proyek lama tidak disentuh.
CREATE SCHEMA IF NOT EXISTS ascii_chat;

CREATE TABLE IF NOT EXISTS ascii_chat.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id text NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT users_user_id_format CHECK (user_id ~ '^[A-Za-z0-9_]{3,24}$'),
    CONSTRAINT users_email_format CHECK (position('@' in email) > 1)
);
CREATE UNIQUE INDEX IF NOT EXISTS ascii_chat_users_user_id_lower_uq
    ON ascii_chat.users (lower(user_id));
CREATE UNIQUE INDEX IF NOT EXISTS ascii_chat_users_email_lower_uq
    ON ascii_chat.users (lower(email));

CREATE TABLE IF NOT EXISTS ascii_chat.contacts (
    owner_id uuid NOT NULL REFERENCES ascii_chat.users(id) ON DELETE CASCADE,
    contact_id uuid NOT NULL REFERENCES ascii_chat.users(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (owner_id, contact_id),
    CONSTRAINT contacts_no_self CHECK (owner_id <> contact_id)
);
CREATE INDEX IF NOT EXISTS ascii_chat_contacts_contact_id_idx
    ON ascii_chat.contacts(contact_id);

CREATE TABLE IF NOT EXISTS ascii_chat.messages (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sender_id uuid NOT NULL REFERENCES ascii_chat.users(id) ON DELETE CASCADE,
    recipient_id uuid NOT NULL REFERENCES ascii_chat.users(id) ON DELETE CASCADE,
    body text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT messages_body_length CHECK (char_length(body) BETWEEN 1 AND 2000),
    CONSTRAINT messages_no_self CHECK (sender_id <> recipient_id),
    CONSTRAINT messages_ascii_printable CHECK (body !~ '[^ -~]')
);
CREATE INDEX IF NOT EXISTS ascii_chat_messages_conversation_idx
    ON ascii_chat.messages(sender_id, recipient_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ascii_chat_messages_recipient_idx
    ON ascii_chat.messages(recipient_id, created_at DESC);

-- Backend Streamlit memakai koneksi PostgreSQL privat, bukan Data API publik.
-- Jangan menambahkan ascii_chat ke daftar exposed schemas Data API.
REVOKE ALL ON SCHEMA ascii_chat FROM PUBLIC, anon, authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA ascii_chat FROM PUBLIC, anon, authenticated;
GRANT USAGE ON SCHEMA ascii_chat TO postgres;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ascii_chat TO postgres;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ascii_chat TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA ascii_chat REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA ascii_chat GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA ascii_chat GRANT USAGE, SELECT ON SEQUENCES TO postgres;
