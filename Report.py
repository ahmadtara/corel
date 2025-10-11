# =================== REPORT.PY (v5.4 FIX FILTER PER HARI + BULAN) ===================
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

    if df_servis.empty and df_transaksi.empty:
        st.info("Belum ada data transaksi atau servis di spreadsheet.")
        return

    # ========== PARSE SERVIS ==========
    if not df_servis.empty:
        for col in ["Tanggal Masuk", "Estimasi Selesai", "Harga Jasa", "Harga Modal", "Status", "No Nota", "Nama Pelanggan", "No HP", "Barang"]:
            if col not in df_servis.columns:
                df_servis[col] = ""
        df_servis["Tanggal Masuk"] = pd.to_datetime(df_servis["Tanggal Masuk"], format="%d/%m/%Y", errors="coerce").dt.date
        df_servis["Estimasi Selesai"] = pd.to_datetime(df_servis["Estimasi Selesai"], format="%d/%m/%Y", errors="coerce").dt.date
        df_servis["Harga Jasa Num"] = df_servis["Harga Jasa"].apply(parse_rp_to_int)
        df_servis["Harga Modal Num"] = df_servis["Harga Modal"].apply(parse_rp_to_int)
        df_servis["Keuntungan"] = df_servis["Harga Jasa Num"] - df_servis["Harga Modal Num"]
        df_servis = df_servis.dropna(subset=["Tanggal Masuk"])

    # ========== PARSE TRANSAKSI ==========
    if not df_transaksi.empty:
        for c in ["Tanggal", "Modal", "Harga Jual", "Qty", "Untung"]:
            if c not in df_transaksi.columns:
                df_transaksi[c] = ""
        df_transaksi["Tanggal"] = pd.to_datetime(df_transaksi["Tanggal"], format="%d/%m/%Y", errors="coerce").dt.date
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
    else:
        bulan_unik = sorted(
            set(df_servis["Tanggal Masuk"].dropna().map(lambda d: d.strftime("%Y-%m"))) |
            set(df_transaksi["Tanggal"].dropna().map(lambda d: d.strftime("%Y-%m")))
        )
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
        for c in ["modal", "harga_jual", "qty"]:
            if c not in df_stok.columns:
                df_stok[c] = 0
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

    # ========== WA OTOMATIS ==========
    st.divider()
    st.subheader("📱 Klik Pelanggan Untuk Input Harga & Kirim WA Otomatis")
    if not df_servis_f.empty:
        for idx, row in df_servis_f.iterrows():
            nota = row.get("No Nota", "")
            nama_pelanggan = row.get("Nama Pelanggan", "")
            barang = row.get("Barang", "")
            no_hp = row.get("No HP", "")
            status_now = row.get("Status", "")

            with st.expander(f"{nama_pelanggan} - {barang} ({status_now})"):
                existing_hj = str(row.get("Harga Jasa","")).replace("Rp","").replace(".","").strip() if pd.notna(row.get("Harga Jasa","")) else ""
                existing_hm = str(row.get("Harga Modal","")).replace("Rp","").replace(".","").strip() if pd.notna(row.get("Harga Modal","")) else ""

                harga_jasa_input = st.text_input("Masukkan Harga Jasa (Rp):", value=existing_hj, key=f"hj_{nota}")
                harga_modal_input = st.text_input("Masukkan Harga Modal (Rp) - tidak dikirim ke WA:", value=existing_hm, key=f"hm_{nota}")

                if st.button("✅ Simpan & Kirim WA", key=f"kirim_{nota}"):
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
                            st.markdown(f"[📲 Buka WhatsApp]({wa_link})", unsafe_allow_html=True)
                            js = f"""
                            <script>
                                setTimeout(function(){{
                                    window.open("{wa_link}", "_blank");
                                }}, 800);
                            </script>
                            """
                            st.markdown(js, unsafe_allow_html=True)
                        else:
                            st.warning("⚠️ Nomor HP pelanggan kosong atau tidak valid.")

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
