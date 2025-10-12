# report.py (v5.9) - Laporan Servis & Barang (filter hanya Status Antrian=Selesai)
import streamlit as st
import pandas as pd
import datetime
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests

# ------------------- CONFIG -------------------
CONFIG_FILE = "config.json"

SPREADSHEET_ID = "1OsnO1xQFniBtEFCvGksR2KKrPt-9idE-w6-poM-wXKU"
SHEET_SERVIS = "Servis"
SHEET_TRANSAKSI = "Transaksi"
SHEET_STOK = "Stok"
SHEET_PENGELUARAN = "Pengeluaran"

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

# ------------------- UPDATE SHEET -------------------
def update_sheet_row_by_nota(sheet_name, nota, updates: dict):
    try:
        ws = get_worksheet(sheet_name)
        cell = ws.find(str(nota))
        if not cell:
            headers = ws.row_values(1)
            if "No Nota" in headers:
                no_nota_col = headers.index("No Nota") + 1
                vals = ws.col_values(no_nota_col)
                for i, v in enumerate(vals, start=1):
                    if str(v).strip() == str(nota).strip():
                        cell = gspread.Cell(i, no_nota_col, v)
                        break
        if not cell:
            raise ValueError(f"Tidak ditemukan No Nota '{nota}' di sheet {sheet_name}")
        row = cell.row
        headers = ws.row_values(1)
        for k, v in updates.items():
            if k in headers:
                col = headers.index(k) + 1
                ws.update_cell(row, col, v)
        return True
    except Exception as e:
        st.error(f"Gagal update sheet {sheet_name} untuk nota {nota}: {e}")
        return False

# ------------------- UTIL -------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Buluh Cina, Panam",
        "telepon": "0851-7217-4759"
    }

def parse_rp_to_int(x):
    try:
        s = str(x).replace("Rp", "").replace(".", "").replace(",", "").strip()
        return int(s) if s else 0
    except:
        return 0

def format_rp(n):
    try:
        nnum = int(n)
        return f"Rp {nnum:,.0f}".replace(",", ".")
    except:
        return str(n)

# ------------------- INTERNET DATE -------------------
def get_internet_date():
    try:
        resp = requests.get("https://worldtimeapi.org/api/timezone/Asia/Jakarta", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            dt = datetime.datetime.fromisoformat(data["datetime"].replace("Z", "+00:00"))
            return dt.date()
    except:
        pass
    return datetime.date.today()

# ------------------- MAIN -------------------
def show():
    cfg = load_config()
    st.title("📊 Laporan Servis & Barang Capslock Computer")
    today = get_internet_date()

    df_servis = read_sheet(SHEET_SERVIS)
    df_transaksi = read_sheet(SHEET_TRANSAKSI)
    df_stok = read_sheet(SHEET_STOK)
    df_pengeluaran = read_sheet(SHEET_PENGELUARAN)

    if df_servis.empty and df_transaksi.empty:
        st.info("Belum ada data transaksi atau servis di spreadsheet.")
        return

    # ---------------- FILTER SERVIS SELESAI SAJA ----------------
    if not df_servis.empty and "Status Antrian" in df_servis.columns:
        df_servis = df_servis[df_servis["Status Antrian"].astype(str).str.lower() == "selesai"]

    # ---------- PARSE ----------
    if not df_pengeluaran.empty:
        df_pengeluaran["Tanggal"] = pd.to_datetime(df_pengeluaran["Tanggal"], dayfirst=True, errors="coerce").dt.date
        df_pengeluaran["Nominal"] = pd.to_numeric(df_pengeluaran["Nominal"], errors="coerce").fillna(0)
        df_pengeluaran["Jenis Transaksi"] = df_pengeluaran["Jenis Transaksi"].astype(str).fillna("").replace("nan","")
        df_pengeluaran = df_pengeluaran.dropna(subset=["Tanggal"])

    if not df_servis.empty:
        for c in ["Tanggal Masuk","Estimasi Selesai","Harga Jasa","Harga Modal","Jenis Transaksi"]:
            if c not in df_servis.columns:
                df_servis[c] = ""
        df_servis["Tanggal Masuk"] = pd.to_datetime(df_servis["Tanggal Masuk"], dayfirst=True, errors="coerce").dt.date
        df_servis["Harga Jasa Num"] = df_servis["Harga Jasa"].apply(parse_rp_to_int)
        df_servis["Harga Modal Num"] = df_servis["Harga Modal"].apply(parse_rp_to_int)
        df_servis["Keuntungan"] = df_servis["Harga Jasa Num"] - df_servis["Harga Modal Num"]
        df_servis["Jenis Transaksi"] = df_servis["Jenis Transaksi"].astype(str).fillna("").replace("nan","")

    if not df_transaksi.empty:
        df_transaksi["Tanggal"] = pd.to_datetime(df_transaksi["Tanggal"], dayfirst=True, errors="coerce").dt.date
        for c in ["Modal","Harga Jual","Qty","Untung"]:
            df_transaksi[c] = pd.to_numeric(df_transaksi[c], errors="coerce").fillna(0)
        df_transaksi["Untung"] = df_transaksi["Untung"].fillna(
            (df_transaksi["Harga Jual"] - df_transaksi["Modal"]) * df_transaksi["Qty"]
        )
        df_transaksi["Jenis Transaksi"] = df_transaksi["Jenis Transaksi"].astype(str).fillna("").replace("nan","")

    # ---------- FILTER MODE ----------
    st.sidebar.header("📅 Filter Data")
    filter_mode = st.sidebar.radio("Mode Filter:", ["Per Hari", "Per Bulan"], index=0)

    if filter_mode == "Per Hari":
        tanggal_filter = st.sidebar.date_input("Tanggal:", value=today)
        df_servis_f = df_servis[df_servis["Tanggal Masuk"] == tanggal_filter] if not df_servis.empty else pd.DataFrame()
        df_transaksi_f = df_transaksi[df_transaksi["Tanggal"] == tanggal_filter] if not df_transaksi.empty else pd.DataFrame()
        df_pengeluaran_f = df_pengeluaran[df_pengeluaran["Tanggal"] == tanggal_filter] if not df_pengeluaran.empty else pd.DataFrame()
    else:
        tahun_ini = today.year
        daftar_bulan = [f"{tahun_ini}-{str(i).zfill(2)}" for i in range(1, 13)]
        bulan_servis = set(df_servis["Tanggal Masuk"].dropna().map(lambda d: d.strftime("%Y-%m"))) if not df_servis.empty else set()
        bulan_transaksi = set(df_transaksi["Tanggal"].dropna().map(lambda d: d.strftime("%Y-%m"))) if not df_transaksi.empty else set()
        semua_bulan = sorted(set(daftar_bulan) | bulan_servis | bulan_transaksi)
        pilih_bulan = st.sidebar.selectbox("Pilih Bulan:", ["Semua Bulan"] + semua_bulan, index=0)

        if pilih_bulan == "Semua Bulan":
            df_servis_f, df_transaksi_f, df_pengeluaran_f = df_servis, df_transaksi, df_pengeluaran
        else:
            y, m = map(int, pilih_bulan.split("-"))
            df_servis_f = df_servis[df_servis["Tanggal Masuk"].apply(lambda d: pd.notna(d) and d.year==y and d.month==m)]
            df_transaksi_f = df_transaksi[df_transaksi["Tanggal"].apply(lambda d: pd.notna(d) and d.year==y and d.month==m)]
            df_pengeluaran_f = df_pengeluaran[df_pengeluaran["Tanggal"].apply(lambda d: pd.notna(d) and d.year==y and d.month==m)]

    # ---------- HITUNG LABA ----------
    total_servis_cash = df_servis_f[df_servis_f["Jenis Transaksi"].str.lower()=="cash"]["Keuntungan"].sum() if not df_servis_f.empty else 0
    total_servis_tf = df_servis_f[df_servis_f["Jenis Transaksi"].str.lower()=="transfer"]["Keuntungan"].sum() if not df_servis_f.empty else 0
    total_barang_cash = df_transaksi_f[df_transaksi_f["Jenis Transaksi"].str.lower()=="cash"]["Untung"].sum() if not df_transaksi_f.empty else 0
    total_barang_tf = df_transaksi_f[df_transaksi_f["Jenis Transaksi"].str.lower()=="transfer"]["Untung"].sum() if not df_transaksi_f.empty else 0
    total_peng_cash = df_pengeluaran_f[df_pengeluaran_f["Jenis Transaksi"].str.lower()=="cash"]["Nominal"].sum() if not df_pengeluaran_f.empty else 0
    total_peng_tf = df_pengeluaran_f[df_pengeluaran_f["Jenis Transaksi"].str.lower()=="transfer"]["Nominal"].sum() if not df_pengeluaran_f.empty else 0

    total_cash = (total_servis_cash + total_barang_cash) - total_peng_cash
    total_transfer = (total_servis_tf + total_barang_tf) - total_peng_tf
    total_gabungan = total_cash + total_transfer

    # ---------- TAMPIL ----------
    st.subheader("🧾 Data Servis (Status: Selesai)")
    if not df_servis_f.empty:
        st.dataframe(df_servis_f[["No Nota","Tanggal Masuk","Nama Pelanggan","Barang","Status Antrian","Harga Jasa","Keuntungan","Jenis Transaksi"]], use_container_width=True)
    else:
        st.info("Tidak ada data servis selesai untuk periode ini.")

    # lanjut: tabel transaksi, pengeluaran, dan ringkasan tetap sama seperti sebelumnya
