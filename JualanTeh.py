# ==================== TEH APP (v2.4 — Default Hari Ini + Tombol Reload) ====================
import streamlit as st
import pandas as pd
import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import requests

# ================= CONFIG ==================
SPREADSHEET_ID = "1OsnO1xQFniBtEFCvGksR2KKrPt-9idE-w6-poM-wXKU"
SHEET_JUALAN = "Jualan"
CONFIG_FILE = "config.json"

# =============== AUTH GOOGLE ===============
def authenticate_google():
    creds_dict = st.secrets["gcp_service_account"]
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(credentials)
    return client

def get_worksheet(sheet_name):
    client = authenticate_google()
    sh = client.open_by_key(SPREADSHEET_ID)
    return sh.worksheet(sheet_name)

# =============== CONFIG FILE ===============
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Buluh Cina, Panam",
        "telepon": "085172174759"
    }

# =============== CEK INTERNET ===============
def is_online():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except:
        return False

# =============== REALTIME WIB ===============
@st.cache_data(ttl=300)
def get_cached_internet_date():
    try:
        res = requests.get("https://worldtimeapi.org/api/timezone/Asia/Jakarta", timeout=5)
        if res.status_code == 200:
            data = res.json()
            dt = datetime.datetime.fromisoformat(data["datetime"].replace("Z", "+00:00"))
            return dt.date()
    except:
        pass
    return datetime.date.today()

# =============== SPREADSHEET OPS ===============
def append_to_sheet(sheet_name, data: dict):
    ws = get_worksheet(sheet_name)
    headers = ws.row_values(1)
    row = [data.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")

@st.cache_data(ttl=600)
def read_sheet_cached(sheet_name):
    ws = get_worksheet(sheet_name)
    df = pd.DataFrame(ws.get_all_records())
    return df

# =============== PAGE APP ===============
def show():
    cfg = load_config()
    st.title("🧾 Transaksi Teh Harian")

    if not is_online():
        st.error("⚠️ Tidak ada koneksi internet. Pastikan koneksi aktif untuk menulis ke Google Sheet.")
        return

    # Tombol reload data sheet
    if st.button("🔁 Reload Data Sheet"):
        st.cache_data.clear()
        st.success("✅ Data sheet berhasil dimuat ulang!")

    (tab1,) = st.tabs(["🫖 Penjualan & Pengeluaran"])

    with tab1:
        st.subheader("🫖 Input Transaksi Teh")

        col1, col2 = st.columns(2)

        # ================== PENJUALAN ==================
        with col1:
            st.markdown("### 🧋 Penjualan Teh")
            pilihan_teh = st.radio(
                "Pilih Jenis Teh:",
                ["Teh Hijau (Rp 5.000)", "Teh Ori (Rp 4.000)"],
                horizontal=True
            )
            qty = st.number_input("Jumlah Gelas", min_value=1, value=1)
            tanggal_jual = get_cached_internet_date()

            if st.button("💾 Simpan Penjualan"):
                jenis = "Teh Hijau" if "Hijau" in pilihan_teh else "Teh Ori"
                harga = 5000 if jenis == "Teh Hijau" else 4000
                total = harga * qty
                data = {
                    "Tanggal": tanggal_jual.strftime("%d/%m/%Y"),
                    "Jenis": jenis,
                    "Qty": qty,
                    "Harga Satuan": harga,
                    "Total": total,
                    "Kategori": "Penjualan"
                }
                try:
                    append_to_sheet(SHEET_JUALAN, data)
                    st.success(f"✅ {qty}x {jenis} disimpan! (Rp {total:,.0f})")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ Gagal simpan: {e}")

        # ================== PENGELUARAN ==================
        with col2:
            st.markdown("### 📉 Pengeluaran")
            pilihan_pengeluaran = st.selectbox(
                "Pilih Pengeluaran",
                ["Beli Cup/Es Batu", "Beli Plastik", "Beli Bubuk Teh Ori", "Beli Bubuk Teh Hijau", "Beli Galon"]
            )
            nominal = st.number_input("Nominal (Rp)", min_value=0.0, format="%.0f")
            tanggal_pengeluaran = get_cached_internet_date()

            if st.button("💰 Simpan Pengeluaran"):
                if nominal <= 0:
                    st.warning("Nominal tidak boleh 0.")
                else:
                    data = {
                        "Tanggal": tanggal_pengeluaran.strftime("%d/%m/%Y"),
                        "Jenis": pilihan_pengeluaran,
                        "Qty": "-",
                        "Harga Satuan": "-",
                        "Total": nominal,
                        "Kategori": "Pengeluaran"
                    }
                    try:
                        append_to_sheet(SHEET_JUALAN, data)
                        st.success(f"✅ Pengeluaran '{pilihan_pengeluaran}' Rp {nominal:,.0f} disimpan!")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ Gagal simpan: {e}")

        # ================== DATA TRANSAKSI ==================
        st.markdown("---")
        st.subheader("📊 Rekap Transaksi Hari Ini")

        try:
            df = read_sheet_cached(SHEET_JUALAN)
        except Exception as e:
            st.error(f"❌ Gagal baca data: {e}")
            return

        if df.empty:
            st.info("📭 Belum ada data transaksi.")
            return

        df["Tanggal"] = pd.to_datetime(df["Tanggal"], format="%d/%m/%Y", errors="coerce")
        df["Total"] = pd.to_numeric(df["Total"], errors="coerce").fillna(0)

        today = get_cached_internet_date()
        hari_ini_df = df[df["Tanggal"].dt.date == today]

        st.info(f"📅 Menampilkan transaksi hari ini (**{today.strftime('%d/%m/%Y')}**)")

        total_jual = hari_ini_df[hari_ini_df["Kategori"] == "Penjualan"]["Total"].sum()
        total_keluar = hari_ini_df[hari_ini_df["Kategori"] == "Pengeluaran"]["Total"].sum()
        laba_bersih = total_jual - total_keluar

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Penjualan Hari Ini", f"Rp {total_jual:,.0f}")
        col_b.metric("Pengeluaran Hari Ini", f"Rp {total_keluar:,.0f}")
        col_c.metric("Laba Bersih", f"Rp {laba_bersih:,.0f}")

        st.dataframe(hari_ini_df.sort_values(by="Tanggal", ascending=False), use_container_width=True)

        # ================= FILTER MANUAL ==================
        st.markdown("---")
        st.subheader("🔍 Filter Manual")

        filter_mode = st.radio("Filter berdasarkan:", ["Per Tanggal", "Per Bulan"], horizontal=True)

        if filter_mode == "Per Tanggal":
            selected_date = st.date_input("Pilih Tanggal")
            if selected_date:
                filtered = df[df["Tanggal"].dt.date == selected_date]
        else:
            bulan = st.selectbox("Pilih Bulan", sorted(df["Tanggal"].dt.strftime("%Y-%m").unique(), reverse=True))
            filtered = df[df["Tanggal"].dt.strftime("%Y-%m") == bulan]

        if 'filtered' in locals() and not filtered.empty:
            total_jual_f = filtered[filtered["Kategori"] == "Penjualan"]["Total"].sum()
            total_keluar_f = filtered[filtered["Kategori"] == "Pengeluaran"]["Total"].sum()
            laba_bersih_f = total_jual_f - total_keluar_f

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Penjualan", f"Rp {total_jual_f:,.0f}")
            col2.metric("Total Pengeluaran", f"Rp {total_keluar_f:,.0f}")
            col3.metric("Laba Bersih", f"Rp {laba_bersih_f:,.0f}")

            st.dataframe(filtered.sort_values(by="Tanggal", ascending=False), use_container_width=True)
        elif 'filtered' in locals():
            st.warning("Tidak ada data untuk periode yang dipilih.")

if __name__ == "__main__":
    show()
