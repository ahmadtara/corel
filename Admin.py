# ==================== ADMIN.PY (v2.1 - Notif Telegram Stok Menipis) ====================
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import requests  # <--- untuk kirim pesan ke Telegram

# ==================== KONFIG =====================
SPREADSHEET_ID = "1OsnO1xQFniBtEFCvGksR2KKrPt-9idE-w6-poM-wXKU"
SHEET_NAME = "Stok"

# Telegram bot config
TELEGRAM_TOKEN = "7656007924:AAGi1it2M7jE0Sen28myiPhEmYPd1-jsI_Q"
TELEGRAM_CHAT_ID = "6122753506"

# ==================== AUTH GOOGLE =====================
def authenticate_google():
    creds_dict = st.secrets["gcp_service_account"]
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(credentials)
    return client

def get_worksheet(sheet_name=SHEET_NAME):
    client = authenticate_google()
    sh = client.open_by_key(SPREADSHEET_ID)
    return sh.worksheet(sheet_name)

# ==================== SPREADSHEET OPS =====================
def append_to_sheet(sheet_name, data: dict):
    ws = get_worksheet(sheet_name)
    headers = ws.row_values(1)
    row = [data.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")

def read_sheet(sheet_name):
    ws = get_worksheet(sheet_name)
    df = pd.DataFrame(ws.get_all_records())
    return df

# ==================== TELEGRAM OPS =====================
def send_telegram_message(message: str):
    """Kirim pesan ke Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        st.warning(f"Gagal kirim notifikasi Telegram: {e}")

# ==================== CEK STOK DAN KIRIM NOTIF =====================
def check_and_notify_stock(df):
    """Kirim notifikasi kalau stok kritis (1) atau habis (0)."""
    for _, row in df.iterrows():
        nama = row.get("nama_barang", "")
        qty = row.get("qty", 0)

        if str(qty).isdigit():
            qty = int(qty)
        else:
            continue

        if qty == 1:
            message = f"⚠️ <b>Peringatan!</b>\nStok barang <b>{nama}</b> tinggal <b>1</b>.\nSegera siapkan restock."
            send_telegram_message(message)
        elif qty == 0:
            message = f"🚨 <b>Stok Habis!</b>\nBarang <b>{nama}</b> sudah <b>kosong</b>.\nSegera lakukan restock!"
            send_telegram_message(message)

# ==================== PAGE =====================
def show():
    st.title("📦 Manajemen Barang (Admin)")

    with st.form("barang_form"):
        nama = st.text_input("Nama Barang", placeholder="Contoh: Mouse Logitech")
        modal = st.number_input("Modal (Rp)", min_value=0.0, format="%.0f")
        harga = st.number_input("Harga Jual (Rp)", min_value=0.0, format="%.0f")
        qty = st.number_input("Stok Barang", min_value=0, format="%d")
        submitted = st.form_submit_button("💾 Simpan Barang")

    if submitted:
        if not nama:
            st.warning("Nama barang wajib diisi!")
            return

        data = {
            "nama_barang": nama,
            "modal": modal,
            "harga_jual": harga,
            "qty": qty
        }

        try:
            append_to_sheet("Stok", data)
            st.success(f"✅ Barang *{nama}* berhasil disimpan ke Google Sheet!")
        except Exception as e:
            st.error(f"❌ Gagal menyimpan ke Sheet: {e}")

    # ==================== TABEL DATA =====================
    st.divider()
    st.subheader("📋 Daftar Barang di Google Sheet")

    try:
        df = read_sheet("Stok")
        if not df.empty:
            df["modal"] = df["modal"].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
            df["harga_jual"] = df["harga_jual"].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
            st.dataframe(df, use_container_width=True)

            # 🔔 Cek stok kritis dan kirim notifikasi
            check_and_notify_stock(df)
        else:
            st.info("Belum ada data barang di Sheet 'Stok'.")
    except Exception as e:
        st.error(f"Gagal memuat data dari Sheet: {e}")

# Jalankan Streamlit
if __name__ == "__main__":
    show()
