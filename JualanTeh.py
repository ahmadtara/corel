# ==================== TEH APP (v2.2 — Tanpa Grafik + Filter Harian & Bulanan) ====================
import streamlit as st
import pandas as pd
import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import requests
import urllib.parse

# ================= CONFIG ==================
SPREADSHEET_ID = "1OsnO1xQFniBtEFCvGksR2KKrPt-9idE-w6-poM-wXKU"
SHEET_JUALAN = "Jualan"
CONFIG_FILE = "config.json"
OFFLINE_CACHE = "offline_cache.json"  # cache lokal

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

# =============== OFFLINE CACHE ===============
def save_offline(data):
    if os.path.exists(OFFLINE_CACHE):
        with open(OFFLINE_CACHE, "r") as f:
            cache = json.load(f)
    else:
        cache = []
    cache.append(data)
    with open(OFFLINE_CACHE, "w") as f:
        json.dump(cache, f, indent=2)

def sync_offline_data():
    if not os.path.exists(OFFLINE_CACHE):
        return

    with open(OFFLINE_CACHE, "r") as f:
        cache = json.load(f)

    if not cache:
        return

    st.info(f"🔄 Sinkronisasi {len(cache)} data offline...")
    success = 0
    failed = 0

    for item in cache:
        try:
            append_to_sheet(SHEET_JUALAN, item)
            success += 1
        except Exception as e:
            print("Gagal kirim data offline:", e)
            failed += 1

    if failed == 0:
        os.remove(OFFLINE_CACHE)
        st.success(f"✅ {success} data offline berhasil disinkron!")
    else:
        with open(OFFLINE_CACHE, "w") as f:
            json.dump(cache[failed:], f, indent=2)
        st.warning(f"⚠️ {failed} data belum berhasil terkirim.")

# =============== REALTIME WIB ===============
@st.cache_data(ttl=300)
def get_cached_internet_date():
    try:
        res = requests.get("https://worldtimeapi.org/api/timezone/Asia/Jakarta", timeout=5)
        if res.status_code == 200:
            data = res.json()
            dt = datetime.datetime.fromisoformat(data["datetime"].replace("Z", "+00:00"))
            return dt.date()
    except Exception as e:
        print("⚠️ Gagal ambil waktu internet:", e)
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
    return pd.DataFrame(ws.get_all_records())

# =============== PAGE APP ===============
def show():
    cfg = load_config()
    st.title("🧾 Transaksi Teh")

    # Cek koneksi dan sinkronisasi data offline
    if is_online():
        sync_offline_data()
    else:
        st.warning("⚠️ Tidak ada koneksi internet — mode offline aktif.")

    (tab1,) = st.tabs(["🫖 Jualan Teh & Pengeluaran"])

    with tab1:
        st.subheader("🫖 Penjualan Minuman Teh & Pengeluaran")

        col1, col2 = st.columns(2)

        # ================== PENJUALAN ==================
        with col1:
            st.markdown("### 🧋 Input Penjualan")
            pilihan_teh = st.radio(
                "Pilih Jenis Teh:",
                ["Teh Hijau (Rp 5.000)", "Teh Ori (Rp 4.000)"],
                horizontal=True
            )
            qty = st.number_input("Jumlah Gelas", min_value=1, value=1)
            tanggal_jual = get_cached_internet_date()

            if st.button("💾 Simpan Penjualan"):
                if "Hijau" in pilihan_teh:
                    jenis = "Teh Hijau"
                    harga = 5000
                else:
                    jenis = "Teh Ori"
                    harga = 4000
                total = harga * qty

                data = {
                    "Tanggal": tanggal_jual.strftime("%d/%m/%Y"),
                    "Jenis": jenis,
                    "Qty": qty,
                    "Harga Satuan": harga,
                    "Total": total,
                    "Kategori": "Penjualan"
                }
                if is_online():
                    try:
                        append_to_sheet(SHEET_JUALAN, data)
                        st.success(f"✅ Penjualan {qty}x {jenis} berhasil disimpan (Total Rp {total:,})")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"❌ Gagal simpan online: {e}, simpan ke cache.")
                        save_offline(data)
                else:
                    save_offline(data)
                    st.info("📦 Data disimpan offline, akan terkirim otomatis saat online.")

        # ================== PENGELUARAN ==================
        with col2:
            st.markdown("### 📉 Input Pengeluaran")
            pilihan_pengeluaran = st.selectbox(
                "Pilih Pengeluaran",
                ["Beli Cup/Es Batu", "Beli Plastik", "Beli Bubuk Teh Ori", "Beli Bubuk Teh Hijau", "Beli Galon"]
            )
            nominal = st.number_input("Nominal (Rp)", min_value=0.0, format="%.0f")
            tanggal_pengeluaran = get_cached_internet_date()

            if st.button("💰 Simpan Pengeluaran"):
                if nominal <= 0:
                    st.warning("Nominal tidak boleh 0")
                else:
                    data = {
                        "Tanggal": tanggal_pengeluaran.strftime("%d/%m/%Y"),
                        "Jenis": pilihan_pengeluaran,
                        "Qty": "-",
                        "Harga Satuan": "-",
                        "Total": nominal,
                        "Kategori": "Pengeluaran"
                    }
                    if is_online():
                        try:
                            append_to_sheet(SHEET_JUALAN, data)
                            st.success(f"✅ Pengeluaran {pilihan_pengeluaran} Rp {nominal:,.0f} tersimpan")
                            st.cache_data.clear()
                        except Exception as e:
                            st.error(f"❌ Gagal simpan online: {e}, simpan ke cache.")
                            save_offline(data)
                    else:
                        save_offline(data)
                        st.info("📦 Data pengeluaran disimpan offline, akan terkirim saat online.")

        st.markdown("---")

        # ================== REKAP ==================
        st.subheader("📊 Rekap Penjualan & Pengeluaran")

        try:
            jualan_df = read_sheet_cached(SHEET_JUALAN)
        except Exception as e:
            st.error(f"❌ Gagal baca data online: {e}")
            return

        if jualan_df.empty:
            st.info("📭 Belum ada data jualan atau pengeluaran.")
            return

        jualan_df["Tanggal"] = pd.to_datetime(jualan_df["Tanggal"], format="%d/%m/%Y", errors="coerce")
        jualan_df["Total"] = pd.to_numeric(jualan_df["Total"], errors="coerce").fillna(0)

        # Default tampil hari ini
        today = get_cached_internet_date()
        filtered_df = jualan_df[jualan_df["Tanggal"].dt.date == today]

        st.info(f"📅 Menampilkan transaksi tanggal **{today.strftime('%d/%m/%Y')}** (otomatis)")

        # Filter tambahan per bulan
        st.markdown("### 🔍 Filter Per Bulan")
        months = jualan_df["Tanggal"].dt.strftime("%Y-%m").unique()
        selected_month = st.selectbox("Pilih Bulan", sorted(months, reverse=True))

        if selected_month:
            month_df = jualan_df[jualan_df["Tanggal"].dt.strftime("%Y-%m") == selected_month]
            total_jual = month_df[month_df["Kategori"] == "Penjualan"]["Total"].sum()
            total_keluar = month_df[month_df["Kategori"] == "Pengeluaran"]["Total"].sum()
            laba_bersih = total_jual - total_keluar

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Total Penjualan", f"Rp {total_jual:,.0f}")
            col_b.metric("Total Pengeluaran", f"Rp {total_keluar:,.0f}")
            col_c.metric("Laba Bersih", f"Rp {laba_bersih:,.0f}")

            st.markdown(f"### 📄 Data Transaksi Bulan {selected_month}")
            st.dataframe(month_df.sort_values(by="Tanggal", ascending=False), use_container_width=True)

        st.markdown("---")
        st.markdown("### 📄 Data Transaksi Hari Ini")
        st.dataframe(filtered_df.sort_values(by="Tanggal", ascending=False), use_container_width=True)

if __name__ == "__main__":
    show()
