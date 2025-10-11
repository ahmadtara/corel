import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# ==================== KONFIG =====================
SPREADSHEET_ID = "1zrgkTKGcq6_fdGRBkHYj5Km8nuyOdM6d3Wjetq8ucpk" # ID spreadsheet kamu
SHEET_NAME = "Stok"

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
        else:
            st.info("Belum ada data barang di Sheet 'Stok'.")
    except Exception as e:
        st.error(f"Gagal memuat data dari Sheet: {e}")

# Jalankan Streamlit
if __name__ == "__main__":
    show()
