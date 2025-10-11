# =================== REPORT.PY (v2 Sinkron Spreadsheet) ===================
import streamlit as st
import pandas as pd
import datetime
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ------------------- CONFIG -------------------
CONFIG_FILE = "config.json"

SPREADSHEET_ID = "1uTVKVIuhqSiGU8vqE0cVGWdsd7cqSzTA"
SHEET_SERVIS = "Servis"
SHEET_TRANSAKSI = "Transaksi"
SHEET_STOK = "Stok"

# ------------------- AUTH GOOGLE -------------------
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

def read_sheet(sheet_name):
    try:
        ws = get_worksheet(sheet_name)
        df = pd.DataFrame(ws.get_all_records())
        return df
    except Exception as e:
        st.warning(f"Gagal membaca sheet {sheet_name}: {e}")
        return pd.DataFrame()

# ------------------- CONFIG -------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Buluh Cina, Panam",
        "telepon": "0851-7217-4759"
    }

# ------------------- UTIL -------------------
def parse_rp_to_int(x):
    try:
        s = str(x).replace("Rp", "").replace(".", "").replace(",", "").strip()
        return int(s) if s else 0
    except:
        return 0

# ------------------- MAIN PAGE -------------------
def show():
    cfg = load_config()
    st.title("📊 Laporan Servis & Barang (Google Sheet Sync)")

    # ========== LOAD DATA ==========
    df_servis = read_sheet(SHEET_SERVIS)
    df_transaksi = read_sheet(SHEET_TRANSAKSI)
    df_stok = read_sheet(SHEET_STOK)

    if df_servis.empty and df_transaksi.empty:
        st.info("Belum ada data transaksi atau servis di spreadsheet.")
        return

    # ========== PARSE SERVIS ==========
    if not df_servis.empty:
        df_servis["Tanggal Masuk"] = pd.to_datetime(df_servis["Tanggal Masuk"], format="%d/%m/%Y", errors="coerce").dt.date
        df_servis["Estimasi Selesai"] = pd.to_datetime(df_servis["Estimasi Selesai"], format="%d/%m/%Y", errors="coerce").dt.date
        df_servis["Harga Jasa Num"] = df_servis["Harga Jasa"].apply(parse_rp_to_int)
        df_servis["Harga Modal Num"] = df_servis.get("Harga Modal", 0).apply(parse_rp_to_int) if "Harga Modal" in df_servis else 0
        df_servis["Keuntungan"] = df_servis["Harga Jasa Num"] - df_servis["Harga Modal Num"]

    # ========== PARSE TRANSAKSI ==========
    if not df_transaksi.empty:
        df_transaksi["Tanggal"] = pd.to_datetime(df_transaksi["Tanggal"], format="%d/%m/%Y", errors="coerce").dt.date
        for c in ["Modal", "Harga Jual", "Qty", "Untung"]:
            if c in df_transaksi.columns:
                df_transaksi[c] = pd.to_numeric(df_transaksi[c], errors="coerce").fillna(0)
        df_transaksi["Total"] = df_transaksi["Harga Jual"] * df_transaksi["Qty"]
        df_transaksi["Untung"] = df_transaksi["Untung"].fillna((df_transaksi["Harga Jual"] - df_transaksi["Modal"]) * df_transaksi["Qty"])

    # ========== FILTER ==========
    st.sidebar.header("📅 Filter Data")
    filter_mode = st.sidebar.radio("Mode Filter:", ["Per Hari", "Per Bulan"], index=0)

    if filter_mode == "Per Hari":
        tanggal_filter = st.sidebar.date_input("Tanggal:", value=datetime.date.today())
        df_servis_f = df_servis[df_servis["Tanggal Masuk"] == tanggal_filter] if not df_servis.empty else pd.DataFrame()
        df_transaksi_f = df_transaksi[df_transaksi["Tanggal"] == tanggal_filter] if not df_transaksi.empty else pd.DataFrame()
    else:
        bulan_unik = sorted(set(df_servis["Tanggal Masuk"].dropna().map(lambda d: d.strftime("%Y-%m"))) |
                            set(df_transaksi["Tanggal"].dropna().map(lambda d: d.strftime("%Y-%m"))))
        pilih_bulan = st.sidebar.selectbox("Pilih Bulan:", ["Semua Bulan"] + bulan_unik, index=0)
        if pilih_bulan == "Semua Bulan":
            df_servis_f = df_servis.copy()
            df_transaksi_f = df_transaksi.copy()
        else:
            tahun, bulan = map(int, pilih_bulan.split("-"))
            df_servis_f = df_servis[df_servis["Tanggal Masuk"].apply(lambda d: d and d.year == tahun and d.month == bulan)]
            df_transaksi_f = df_transaksi[df_transaksi["Tanggal"].apply(lambda d: d and d.year == tahun and d.month == bulan)]

    # ========== HITUNG LABA ==========
    total_servis = df_servis_f["Keuntungan"].sum() if not df_servis_f.empty else 0
    total_barang = df_transaksi_f["Untung"].sum() if not df_transaksi_f.empty else 0
    total_gabungan = total_servis + total_barang

    # ========== POTENSI LABA STOK ==========
    potensi_laba = 0
    if not df_stok.empty:
        df_stok["modal"] = pd.to_numeric(df_stok["modal"], errors="coerce").fillna(0)
        df_stok["harga_jual"] = pd.to_numeric(df_stok["harga_jual"], errors="coerce").fillna(0)
        df_stok["qty"] = pd.to_numeric(df_stok["qty"], errors="coerce").fillna(0)
        df_stok["Potensi Laba"] = (df_stok["harga_jual"] - df_stok["modal"]) * df_stok["qty"]
        potensi_laba = df_stok["Potensi Laba"].sum()

    # ========== METRIK ==========
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Laba Servis", f"Rp {total_servis:,.0f}".replace(",", "."))
    col2.metric("📦 Laba Barang", f"Rp {total_barang:,.0f}".replace(",", "."))
    col3.metric("📊 Total Gabungan", f"Rp {total_gabungan:,.0f}".replace(",", "."))
    st.caption(f"Potensi Laba Stok: Rp {potensi_laba:,.0f}".replace(",", "."))

    st.divider()

    # ========== TABEL SERVIS ==========
    st.subheader("🧾 Data Servis")
    if not df_servis_f.empty:
        st.dataframe(
            df_servis_f[["No Nota","Tanggal Masuk","Nama Pelanggan","Barang","Status","Harga Jasa","Keuntungan"]],
            use_container_width=True
        )
    else:
        st.info("Tidak ada data servis untuk periode ini.")

    # ========== TABEL BARANG ==========
    st.divider()
    st.subheader("📦 Data Transaksi Barang")
    if not df_transaksi_f.empty:
        st.dataframe(
            df_transaksi_f[["No Nota","Tanggal","Nama Barang","Qty","Harga Jual","Modal","Untung","Pembeli"]],
            use_container_width=True
        )
    else:
        st.info("Tidak ada transaksi barang pada periode ini.")

    # ========== DOWNLOAD CSV ==========
    st.divider()
    if not df_servis_f.empty or not df_transaksi_f.empty:
        gabung = pd.concat([
            df_servis_f[["No Nota","Tanggal Masuk","Nama Pelanggan","Barang","Keuntungan"]].rename(columns={"Tanggal Masuk":"Tanggal"}),
            df_transaksi_f[["No Nota","Tanggal","Nama Barang","Untung"]].rename(columns={"Nama Barang":"Barang","Untung":"Keuntungan"})
        ], ignore_index=True)
        csv = gabung.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Laporan Gabungan (CSV)", csv, "laporan_gabungan.csv", "text/csv")
