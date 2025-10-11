# report.py (v5.7 clean) - Laporan Servis & Barang (tanpa fitur input harga & WA)
import streamlit as st
import pandas as pd
import datetime
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
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

# ------------------- UPDATE SHEET (dipakai juga pada pelanggan.py) -------------------
def update_sheet_row_by_nota(sheet_name, nota, updates: dict):
    """
    Update kolom di baris yang mengandung `nota`. Mencari nota langsung di seluruh sheet,
    fallback mencari di kolom header 'No Nota'.
    """
    try:
        ws = get_worksheet(sheet_name)
        try:
            cell = ws.find(str(nota))
        except Exception:
            cell = None

        # fallback: cari di kolom "No Nota"
        if not cell:
            headers = ws.row_values(1)
            if "No Nota" in headers:
                no_nota_col = headers.index("No Nota") + 1
                column_vals = ws.col_values(no_nota_col)
                for i, v in enumerate(column_vals, start=1):
                    if str(v).strip() == str(nota).strip():
                        cell = gspread.Cell(i, no_nota_col, v)
                        break

        if not cell:
            raise ValueError(f"Baris dengan No Nota '{nota}' tidak ditemukan di sheet '{sheet_name}'.")

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

# ------------------- MAIN -------------------
def show():
    cfg = load_config()
    st.title("📊 Laporan Servis & Barang Capslock Computer")

    # ========== LOAD DATA ==========
    df_servis = read_sheet(SHEET_SERVIS)
    df_transaksi = read_sheet(SHEET_TRANSAKSI)
    df_stok = read_sheet(SHEET_STOK)
    df_pengeluaran = read_sheet(SHEET_PENGELUARAN)

    if df_servis.empty and df_transaksi.empty:
        st.info("Belum ada data transaksi atau servis di spreadsheet.")
        return

    # ========== PARSE PENGELUARAN ==========
    if df_pengeluaran is None:
        df_pengeluaran = pd.DataFrame()
    if not df_pengeluaran.empty:
        for c in ["Tanggal", "Keterangan", "Nominal", "Jenis Transaksi"]:
            if c not in df_pengeluaran.columns:
                df_pengeluaran[c] = ""
        df_pengeluaran["Tanggal"] = pd.to_datetime(df_pengeluaran["Tanggal"], dayfirst=True, errors="coerce").dt.date
        df_pengeluaran["Nominal"] = pd.to_numeric(df_pengeluaran["Nominal"], errors="coerce").fillna(0)
        df_pengeluaran["Jenis Transaksi"] = df_pengeluaran["Jenis Transaksi"].astype(str).fillna("").replace("nan","")
        df_pengeluaran = df_pengeluaran.dropna(subset=["Tanggal"])

    # ========== PARSE SERVIS ==========
    if df_servis is None:
        df_servis = pd.DataFrame()
    if not df_servis.empty:
        for col in ["Tanggal Masuk", "Estimasi Selesai", "Harga Jasa", "Harga Modal", "Status", "No Nota", "Nama Pelanggan", "No HP", "Barang", "Jenis Transaksi"]:
            if col not in df_servis.columns:
                df_servis[col] = ""
        df_servis["Tanggal Masuk"] = pd.to_datetime(df_servis["Tanggal Masuk"], dayfirst=True, errors="coerce").dt.date
        df_servis["Estimasi Selesai"] = pd.to_datetime(df_servis["Estimasi Selesai"], dayfirst=True, errors="coerce").dt.date
        df_servis["Harga Jasa Num"] = df_servis["Harga Jasa"].apply(parse_rp_to_int)
        df_servis["Harga Modal Num"] = df_servis["Harga Modal"].apply(parse_rp_to_int)
        df_servis["Keuntungan"] = df_servis["Harga Jasa Num"] - df_servis["Harga Modal Num"]
        df_servis["Jenis Transaksi"] = df_servis["Jenis Transaksi"].astype(str).fillna("").replace("nan","")
        df_servis = df_servis.dropna(subset=["Tanggal Masuk"])

    # ========== PARSE TRANSAKSI ==========
    if df_transaksi is None:
        df_transaksi = pd.DataFrame()
    if not df_transaksi.empty:
        for c in ["Tanggal", "Modal", "Harga Jual", "Qty", "Untung", "Jenis Transaksi"]:
            if c not in df_transaksi.columns:
                df_transaksi[c] = ""
        df_transaksi["Tanggal"] = pd.to_datetime(df_transaksi["Tanggal"], dayfirst=True, errors="coerce").dt.date
        for c in ["Modal", "Harga Jual", "Qty", "Untung"]:
            df_transaksi[c] = pd.to_numeric(df_transaksi[c], errors="coerce").fillna(0)
        df_transaksi["Total"] = df_transaksi["Harga Jual"] * df_transaksi["Qty"]
        df_transaksi["Untung"] = df_transaksi["Untung"].fillna(
            (df_transaksi["Harga Jual"] - df_transaksi["Modal"]) * df_transaksi["Qty"]
        )
        df_transaksi["Jenis Transaksi"] = df_transaksi["Jenis Transaksi"].astype(str).fillna("").replace("nan","")
        df_transaksi = df_transaksi.dropna(subset=["Tanggal"])

    # ========== FILTER ==========
    st.sidebar.header("📅 Filter Data")
    filter_mode = st.sidebar.radio("Mode Filter:", ["Per Hari", "Per Bulan"], index=0)

    if filter_mode == "Per Hari":
        tanggal_filter = st.sidebar.date_input("Tanggal:", value=datetime.date.today())
        df_servis_f = df_servis[df_servis["Tanggal Masuk"] == tanggal_filter] if not df_servis.empty else pd.DataFrame()
        df_transaksi_f = df_transaksi[df_transaksi["Tanggal"] == tanggal_filter] if not df_transaksi.empty else pd.DataFrame()
        df_pengeluaran_f = df_pengeluaran[df_pengeluaran["Tanggal"] == tanggal_filter] if not df_pengeluaran.empty else pd.DataFrame()
    else:
        tahun_ini = datetime.date.today().year
        daftar_bulan = [f"{tahun_ini}-{str(i).zfill(2)}" for i in range(1, 13)]

        bulan_servis = set()
        bulan_transaksi = set()
        if not df_servis.empty and "Tanggal Masuk" in df_servis.columns:
            bulan_servis = set(df_servis["Tanggal Masuk"].dropna().map(lambda d: d.strftime("%Y-%m")))
        if not df_transaksi.empty and "Tanggal" in df_transaksi.columns:
            bulan_transaksi = set(df_transaksi["Tanggal"].dropna().map(lambda d: d.strftime("%Y-%m")))

        semua_bulan = sorted(set(daftar_bulan) | bulan_servis | bulan_transaksi)

        pilih_bulan = st.sidebar.selectbox("Pilih Bulan:", ["Semua Bulan"] + semua_bulan, index=0)

        if pilih_bulan == "Semua Bulan":
            df_servis_f = df_servis.copy()
            df_transaksi_f = df_transaksi.copy()
            df_pengeluaran_f = df_pengeluaran.copy()
        else:
            tahun, bulan = map(int, pilih_bulan.split("-"))
            if not df_servis.empty and "Tanggal Masuk" in df_servis.columns:
                df_servis_f = df_servis[df_servis["Tanggal Masuk"].apply(lambda d: pd.notna(d) and d.year == tahun and d.month == bulan)]
            else:
                df_servis_f = pd.DataFrame()
            if not df_transaksi.empty and "Tanggal" in df_transaksi.columns:
                df_transaksi_f = df_transaksi[df_transaksi["Tanggal"].apply(lambda d: pd.notna(d) and d.year == tahun and d.month == bulan)]
            else:
                df_transaksi_f = pd.DataFrame()
            if not df_pengeluaran.empty and "Tanggal" in df_pengeluaran.columns:
                df_pengeluaran_f = df_pengeluaran[df_pengeluaran["Tanggal"].apply(lambda d: pd.notna(d) and d.year == tahun and d.month == bulan)]
            else:
                df_pengeluaran_f = pd.DataFrame()

    # ========== HITUNG LABA (PER JENIS) ==========
    # default jika dataframe kosong
    if df_servis_f.empty:
        total_servis_cash = total_servis_tf = 0
    else:
        total_servis_cash = df_servis_f[df_servis_f["Jenis Transaksi"].str.lower() == "cash"]["Keuntungan"].sum()
        total_servis_tf = df_servis_f[df_servis_f["Jenis Transaksi"].str.lower() == "transfer"]["Keuntungan"].sum()

    if df_transaksi_f.empty:
        total_barang_cash = total_barang_tf = 0
    else:
        total_barang_cash = df_transaksi_f[df_transaksi_f["Jenis Transaksi"].str.lower() == "cash"]["Untung"].sum()
        total_barang_tf = df_transaksi_f[df_transaksi_f["Jenis Transaksi"].str.lower() == "transfer"]["Untung"].sum()

    if df_pengeluaran_f.empty:
        total_peng_cash = total_peng_tf = 0
    else:
        total_peng_cash = df_pengeluaran_f[df_pengeluaran_f["Jenis Transaksi"].str.lower() == "cash"]["Nominal"].sum()
        total_peng_tf = df_pengeluaran_f[df_pengeluaran_f["Jenis Transaksi"].str.lower() == "transfer"]["Nominal"].sum()

    total_cash = (total_servis_cash + total_barang_cash) - total_peng_cash
    total_transfer = (total_servis_tf + total_barang_tf) - total_peng_tf
    total_gabungan = total_cash + total_transfer  # keseluruhan

    # ========== POTENSI LABA STOK ==========
    potensi_laba = 0
    if not df_stok.empty:
        for c in ["modal", "harga_jual", "qty"]:
            if c not in df_stok.columns:
                df_stok[c] = 0
        df_stok["modal"] = pd.to_numeric(df_stok["modal"], errors="coerce").fillna(0)
        df_stok["harga_jual"] = pd.to_numeric(df_stok["harga_jual"], errors="coerce").fillna(0)
        df_stok["qty"] = pd.to_numeric(df_stok["qty"], errors="coerce").fillna(0)
        df_stok["Potensi Laba"] = (df_stok["harga_jual"] - df_stok["modal"]) * df_stok["qty"]
        potensi_laba = df_stok["Potensi Laba"].sum()

    # ========== METRIK (TAMPILAN) ==========
    st.markdown(f"""
    <style>
    .metric-container {{
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        justify-content: flex-start;
        margin-bottom: 10px;
    }}
    .metric-card {{
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 8px 12px;
        border-radius: 8px;
        min-width: 150px;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.12);
        transition: all 0.2s ease-in-out;
    }}
    .metric-label {{
        font-size: 0.8rem;
        opacity: 0.85;
    }}
    .metric-value {{
        font-size: 1rem;
        font-weight: 600;
        margin-top: 6px;
    }}
    </style>

    <div style="margin-bottom:6px;"><strong>Ringkasan (Cash)</strong></div>
    <div class="metric-container">
        <div class="metric-card">
            <div class="metric-label">💰 Laba Servis (Cash)</div>
            <div class="metric-value">{format_rp(total_servis_cash)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">📦 Laba Barang (Cash)</div>
            <div class="metric-value">{format_rp(total_barang_cash)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">💸 Pengeluaran (Cash)</div>
            <div class="metric-value" style="color:#ff6b6b;">- {format_rp(total_peng_cash)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">📊 Total Bersih (Cash)</div>
            <div class="metric-value" style="color:#4ade80;">{format_rp(total_cash)}</div>
        </div>
    </div>

    <div style="margin-top:14px;margin-bottom:6px;"><strong>Ringkasan (Transfer)</strong></div>
    <div class="metric-container">
        <div class="metric-card">
            <div class="metric-label">💰 Laba Servis (Transfer)</div>
            <div class="metric-value">{format_rp(total_servis_tf)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">📦 Laba Barang (Transfer)</div>
            <div class="metric-value">{format_rp(total_barang_tf)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">💸 Pengeluaran (Transfer)</div>
            <div class="metric-value" style="color:#ff6b6b;">- {format_rp(total_peng_tf)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">📊 Total Bersih (Transfer)</div>
            <div class="metric-value" style="color:#4ade80;">{format_rp(total_transfer)}</div>
        </div>
    </div>

    <div style="margin-top:14px;">
        <div class="metric-label">📦 Total Bersih Keseluruhan</div>
        <div class="metric-value" style="font-size:1.05rem;color:#9be7a3;">{format_rp(total_gabungan)}</div>
    </div>
    """, unsafe_allow_html=True)

    st.caption(f"Potensi Laba Stok: {format_rp(potensi_laba)}")

    st.divider()

    # ========== TABEL SERVIS ==========
    st.subheader("🧾 Data Servis")
    if not df_servis_f.empty:
        st.dataframe(
            df_servis_f[["No Nota","Tanggal Masuk","Nama Pelanggan","Barang","Status","Harga Jasa","Keuntungan","Jenis Transaksi"]],
            use_container_width=True
        )
    else:
        st.info("Tidak ada data servis untuk periode ini.")

    # ========== TABEL TRANSAKSI ==========
    st.divider()
    st.subheader("📦 Data Transaksi Barang")
    if not df_transaksi_f.empty:
        st.dataframe(
            df_transaksi_f[["No Nota","Tanggal","Nama Barang","Qty","Harga Jual","Modal","Untung","Pembeli","Jenis Transaksi"]],
            use_container_width=True
        )
    else:
        st.info("Tidak ada transaksi barang pada periode ini.")

    # ========== TABEL PENGELUARAN ==========
    st.divider()
    st.subheader("💸 Data Pengeluaran")
    if not df_pengeluaran_f.empty:
        st.dataframe(
            df_pengeluaran_f[["Tanggal", "Keterangan", "Nominal", "Jenis Transaksi"]],
            use_container_width=True
        )
    else:
        st.info("Tidak ada data pengeluaran pada periode ini.")

    # ========== DOWNLOAD CSV ==========
    st.divider()
    if (not df_servis_f.empty) or (not df_transaksi_f.empty):
        gabung_servis = pd.DataFrame()
        gabung_trans = pd.DataFrame()
        if not df_servis_f.empty:
            gabung_servis = df_servis_f[["No Nota","Tanggal Masuk","Nama Pelanggan","Barang","Keuntungan","Jenis Transaksi"]].rename(columns={"Tanggal Masuk":"Tanggal"})
        if not df_transaksi_f.empty:
            gabung_trans = df_transaksi_f[["No Nota","Tanggal","Nama Barang","Untung","Jenis Transaksi"]].rename(columns={"Nama Barang":"Barang","Untung":"Keuntungan"})
        gabung = pd.concat([gabung_servis, gabung_trans], ignore_index=True, sort=False).fillna("")
        csv = gabung.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Laporan Gabungan (CSV)", csv, "laporan_gabungan.csv", "text/csv")

# ------------------- MAIN -------------------
if __name__ == "__main__":
    show()
