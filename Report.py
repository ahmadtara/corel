# =================== REPORT.PY (v5.6 FINAL FIX FILTER PER HARI + BULAN LENGKAP) ===================
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
SHEET_PENGELUARAN = "Pengeluaran"   # ✅ Tambahan sheet baru


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
        try:
            cell = ws.find(str(nota))
        except Exception:
            cell = None

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
    st.title("📊 Laporan Servis & Barang (Sinkron No Nota dari Google Sheet)")

    # ========== LOAD DATA ==========
    df_servis = read_sheet(SHEET_SERVIS)
    df_transaksi = read_sheet(SHEET_TRANSAKSI)
    df_stok = read_sheet(SHEET_STOK)
    df_pengeluaran = read_sheet(SHEET_PENGELUARAN)   # ✅ Tambahan

    if df_servis.empty and df_transaksi.empty:
        st.info("Belum ada data transaksi atau servis di spreadsheet.")
        return

    # ========== PARSE PENGELUARAN ==========
    if not df_pengeluaran.empty:
        for c in ["Tanggal", "Keterangan", "Nominal"]:
            if c not in df_pengeluaran.columns:
                df_pengeluaran[c] = ""
        df_pengeluaran["Tanggal"] = pd.to_datetime(df_pengeluaran["Tanggal"], dayfirst=True, errors="coerce").dt.date
        df_pengeluaran["Nominal"] = pd.to_numeric(df_pengeluaran["Nominal"], errors="coerce").fillna(0)
        df_pengeluaran = df_pengeluaran.dropna(subset=["Tanggal"])


    # ========== PARSE SERVIS ==========
    if not df_servis.empty:
        for col in ["Tanggal Masuk", "Estimasi Selesai", "Harga Jasa", "Harga Modal", "Status", "No Nota", "Nama Pelanggan", "No HP", "Barang"]:
            if col not in df_servis.columns:
                df_servis[col] = ""
        df_servis["Tanggal Masuk"] = pd.to_datetime(df_servis["Tanggal Masuk"], dayfirst=True, errors="coerce").dt.date
        df_servis["Estimasi Selesai"] = pd.to_datetime(df_servis["Estimasi Selesai"], dayfirst=True, errors="coerce").dt.date
        df_servis["Harga Jasa Num"] = df_servis["Harga Jasa"].apply(parse_rp_to_int)
        df_servis["Harga Modal Num"] = df_servis["Harga Modal"].apply(parse_rp_to_int)
        df_servis["Keuntungan"] = df_servis["Harga Jasa Num"] - df_servis["Harga Modal Num"]
        df_servis = df_servis.dropna(subset=["Tanggal Masuk"])

    # ========== PARSE TRANSAKSI ==========
    if not df_transaksi.empty:
        for c in ["Tanggal", "Modal", "Harga Jual", "Qty", "Untung"]:
            if c not in df_transaksi.columns:
                df_transaksi[c] = ""
        df_transaksi["Tanggal"] = pd.to_datetime(df_transaksi["Tanggal"], dayfirst=True, errors="coerce").dt.date
        for c in ["Modal", "Harga Jual", "Qty", "Untung"]:
            df_transaksi[c] = pd.to_numeric(df_transaksi[c], errors="coerce").fillna(0)
        df_transaksi["Total"] = df_transaksi["Harga Jual"] * df_transaksi["Qty"]
        df_transaksi["Untung"] = df_transaksi["Untung"].fillna(
            (df_transaksi["Harga Jual"] - df_transaksi["Modal"]) * df_transaksi["Qty"]
        )
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
        # -------------- DAFTAR BULAN 1 - 12 TETAP MUNCUL --------------
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

    # ========== HITUNG LABA ==========
    total_servis = df_servis_f["Keuntungan"].sum() if not df_servis_f.empty else 0
    total_barang = df_transaksi_f["Untung"].sum() if not df_transaksi_f.empty else 0
    total_pengeluaran = df_pengeluaran_f["Nominal"].sum() if not df_pengeluaran_f.empty else 0
    total_gabungan = total_servis + total_barang - total_pengeluaran

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

    # ========== METRIK ==========
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
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 8px 12px;
        border-radius: 8px;
        min-width: 120px;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        transition: all 0.2s ease-in-out;
    }}
    .metric-card:hover {{
        transform: scale(1.03);
        background: rgba(255, 255, 255, 0.08);
    }}
    .metric-label {{
        font-size: 0.8rem;
        opacity: 0.8;
    }}
    .metric-value {{
        font-size: 1rem;
        font-weight: 600;
        margin-top: 2px;
    }}
    </style>

    <div class="metric-container">
        <div class="metric-card">
            <div class="metric-label">💰 Laba Servis</div>
            <div class="metric-value">{format_rp(total_servis)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">📦 Laba Barang</div>
            <div class="metric-value">{format_rp(total_barang)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">💸 Pengeluaran</div>
            <div class="metric-value" style="color:#ff6b6b;">- {format_rp(total_pengeluaran)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">📊 Total Bersih</div>
            <div class="metric-value" style="color:#4ade80;">{format_rp(total_gabungan)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


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

        # ========== WA OTOMATIS (MODERN + HIDE + STATUS ICON) ==========
        # ========== WA OTOMATIS (HIDE SAMPAI DIKLIK) ==========
        # ========== WA OTOMATIS (MODERN UI) ==========
        # ========== WA OTOMATIS ==========
    st.divider()
    st.subheader("📱 Klik Pelanggan Untuk Input Harga & Kirim WA Otomatis")

    st.markdown("""
    <style>
    .pelanggan-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid rgba(255,255,255,0.1);
        padding: 15px 20px;
        border-radius: 12px;
        margin-bottom: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.25);
        transition: all 0.2s ease-in-out;
    }
    .pelanggan-card:hover {
        transform: scale(1.01);
        background: linear-gradient(135deg, #334155, #1e293b);
    }
    .pelanggan-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .pelanggan-nama {
        font-weight: 600;
        font-size: 1rem;
        color: #fff;
    }
    .pelanggan-barang {
        font-size: 0.85rem;
        color: #cbd5e1;
    }
    .pelanggan-status {
        background: #3b82f6;
        color: white;
        font-size: 0.75rem;
        padding: 4px 8px;
        border-radius: 6px;
    }
    .harga-input {
        width: 100%;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        color: white;
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 0.9rem;
    }
    .btn-wa {
        background: linear-gradient(90deg, #22c55e, #16a34a);
        color: white !important;
        text-align: center;
        display: inline-block;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 600;
        text-decoration: none;
        transition: 0.2s;
    }
    .btn-wa:hover {
        opacity: 0.9;
        transform: scale(1.03);
    }
    </style>
    """, unsafe_allow_html=True)

    if not df_servis_f.empty:
        for idx, row in df_servis_f.iterrows():
            nota = row.get("No Nota", "")
            nama_pelanggan = row.get("Nama Pelanggan", "")
            barang = row.get("Barang", "")
            no_hp = row.get("No HP", "")
            status_now = row.get("Status", "")

            existing_hj = str(row.get("Harga Jasa","")).replace("Rp","").replace(".","").strip() if pd.notna(row.get("Harga Jasa","")) else ""
            existing_hm = str(row.get("Harga Modal","")).replace("Rp","").replace(".","").strip() if pd.notna(row.get("Harga Modal","")) else ""

            with st.container():
                st.markdown(f"""
                <div class="pelanggan-card">
                    <div class="pelanggan-header">
                        <div>
                            <div class="pelanggan-nama">{nama_pelanggan}</div>
                            <div class="pelanggan-barang">{barang}</div>
                        </div>
                        <div class="pelanggan-status">{status_now}</div>
                    </div>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    harga_jasa_input = st.text_input("💰 Harga Jasa (Rp):", value=existing_hj, key=f"hj_{nota}")
                with col2:
                    harga_modal_input = st.text_input("📦 Harga Modal (Rp):", value=existing_hm, key=f"hm_{nota}")

                kirim = st.button("✅ Simpan & Kirim WA", key=f"kirim_{nota}")
                st.markdown("</div>", unsafe_allow_html=True)

                if kirim:
                    try:
                        hj_num = int(harga_jasa_input.replace(".","").replace(",","").strip()) if harga_jasa_input.strip() else 0
                    except:
                        hj_num = 0
                    try:
                        hm_num = int(harga_modal_input.replace(".","").replace(",","").strip()) if harga_modal_input.strip() else 0
                    except:
                        hm_num = 0

                    hj_str = format_rp(hj_num) if hj_num else ""
                    hm_str = format_rp(hm_num) if hm_num else ""

                    updates = {"Harga Jasa": hj_str, "Harga Modal": hm_str, "Status": "Lunas"}
                    ok = update_sheet_row_by_nota(SHEET_SERVIS, nota, updates)
                    if ok:
                        st.success(f"✅ Nota {nota} diperbarui di Google Sheet.")

                        msg = f"""Assalamualaikum {nama_pelanggan},

Unit anda dengan nomor nota *{nota}* sudah selesai dan siap untuk diambil.

Total Biaya Servis: *{hj_str if hj_str else '(Cek Dulu)'}*

Terima Kasih 🙏
{cfg['nama_toko']}"""

                        no_hp_clean = str(no_hp).replace("+","").replace(" ","").replace("-","").strip()
                        if no_hp_clean.startswith("0"):
                            no_hp_clean = "62" + no_hp_clean[1:]
                        elif not no_hp_clean.startswith("62"):
                            no_hp_clean = "62" + no_hp_clean

                        if no_hp_clean.isdigit() and len(no_hp_clean) >= 10:
                            wa_link = f"https://wa.me/{no_hp_clean}?text={urllib.parse.quote(msg)}"
                            st.markdown(f'<a class="btn-wa" href="{wa_link}" target="_blank">📲 Kirim ke WhatsApp</a>', unsafe_allow_html=True)
                        else:
                            st.warning("⚠️ Nomor HP pelanggan kosong atau tidak valid.")
    else:
        st.info("Tidak ada data servis untuk periode ini.")




    # ========== TABEL TRANSAKSI ==========
    st.divider()
    st.subheader("📦 Data Transaksi Barang")
    if not df_transaksi_f.empty:
        st.dataframe(
            df_transaksi_f[["No Nota","Tanggal","Nama Barang","Qty","Harga Jual","Modal","Untung","Pembeli"]],
            use_container_width=True
        )
    else:
        st.info("Tidak ada transaksi barang pada periode ini.")

    # ========== TABEL PENGELUARAN ==========
    st.divider()
    st.subheader("💸 Data Pengeluaran")
    if not df_pengeluaran_f.empty:
        st.dataframe(
            df_pengeluaran_f[["Tanggal", "Keterangan", "Nominal"]],
            use_container_width=True
        )
    else:
        st.info("Tidak ada data pengeluaran pada periode ini.")


    # ========== DOWNLOAD CSV ==========
    st.divider()
    if not df_servis_f.empty or not df_transaksi_f.empty:
        gabung = pd.concat([
            df_servis_f[["No Nota","Tanggal Masuk","Nama Pelanggan","Barang","Keuntungan"]].rename(columns={"Tanggal Masuk":"Tanggal"}),
            df_transaksi_f[["No Nota","Tanggal","Nama Barang","Untung"]].rename(columns={"Nama Barang":"Barang","Untung":"Keuntungan"})
        ], ignore_index=True)
        csv = gabung.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Laporan Gabungan (CSV)", csv, "laporan_gabungan.csv", "text/csv")

# ------------------- MAIN -------------------
if __name__ == "__main__":
    show()
