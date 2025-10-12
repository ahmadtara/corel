# ================= pelanggan.py (v2.0) =================
import streamlit as st
import pandas as pd
import datetime
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse

# ------------------- CONFIG -------------------
CONFIG_FILE = "config.json"
SPREADSHEET_ID = "1OsnO1xQFniBtEFCvGksR2KKrPt-9idE-w6-poM-wXKU"
SHEET_SERVIS = "Servis"

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

# ------------------- BACA SHEET -------------------
@st.cache_data(ttl=120)
def read_sheet(sheet_name):
    try:
        ws = get_worksheet(sheet_name)
        df = pd.DataFrame(ws.get_all_records())
        return df
    except Exception as e:
        st.warning(f"Gagal membaca sheet {sheet_name}: {e}")
        return pd.DataFrame()

def update_sheet_row_by_nota(sheet_name, nota, updates: dict):
    try:
        ws = get_worksheet(sheet_name)
        cell = ws.find(str(nota))
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
            raise ValueError(f"Tidak ada baris dengan No Nota {nota}.")
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

def format_rp(n):
    try:
        nnum = int(n)
        return f"Rp {nnum:,.0f}".replace(",", ".")
    except:
        return str(n)

def get_waktu_jakarta():
    tz = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz)

def kirim_wa_pelanggan(nama, no_nota, no_hp, total_harga, jenis_transaksi):
    cfg = load_config()
    msg = f"""Assalamualaikum {nama},

Unit anda dengan nomor nota *{no_nota}* sudah *SIAP DIAMBIL*.

Total Biaya Servis: *{total_harga if total_harga else '(Cek Dulu)'}*
Pembayaran: *{jenis_transaksi}*

Terima Kasih 🙏
{cfg['nama_toko']}"""

    no_hp_clean = str(no_hp).replace("+", "").replace(" ", "").replace("-", "").strip()
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

# ------------------- APP -------------------
def show():
    st.title("📱 Pelanggan — Status Antrian & Kirim WA Otomatis")

    if st.button("🔄 Reload Data Sheet"):
        st.cache_data.clear()
        st.rerun()

    df = read_sheet(SHEET_SERVIS)
    if df.empty:
        st.info("Belum ada data di sheet Servis.")
        return

    # Pastikan kolom penting ada
    for col in ["Tanggal Masuk","No Nota","Nama Pelanggan","No HP","Barang","Status Antrian","Harga Jasa","Harga Modal","Jenis Transaksi"]:
        if col not in df.columns:
            df[col] = ""

    # ---------------- FILTER ----------------
    st.markdown("### 📅 Filter Data")
    today = get_waktu_jakarta().date()
    filter_tipe = st.radio("Pilih Jenis Filter:", ["Semua", "Per Hari", "Per Bulan"], horizontal=True)

    df["Tanggal_parsed"] = pd.to_datetime(df["Tanggal Masuk"], errors="coerce", dayfirst=True)
    if filter_tipe == "Per Hari":
        tanggal_pilih = st.date_input("Pilih Tanggal:", today)
        df = df[df["Tanggal_parsed"].dt.date == tanggal_pilih]
    elif filter_tipe == "Per Bulan":
        tahun = st.number_input("Tahun", value=today.year, step=1)
        bulan = st.number_input("Bulan (1–12)", value=today.month, min_value=1, max_value=12, step=1)
        df = df[(df["Tanggal_parsed"].dt.year == tahun) & (df["Tanggal_parsed"].dt.month == bulan)]

    # ---------------- PENCARIAN ----------------
    st.markdown("### 🔎 Cari Pelanggan")
    q = st.text_input("Cari berdasarkan Nama atau No Nota")
    if q.strip():
        q_lower = q.strip().lower()
        mask = df["Nama Pelanggan"].astype(str).str.lower().str.contains(q_lower) | df["No Nota"].astype(str).str.lower().str.contains(q_lower)
        results = df[mask].copy()
    else:
        results = df.tail(50).copy()

    st.markdown(f"Menampilkan **{len(results)} hasil**.")
    for idx, row in results.iterrows():
        no_nota = row.get("No Nota", "")
        nama = row.get("Nama Pelanggan", "")
        barang = row.get("Barang", "")
        no_hp = row.get("No HP", "")
        status_antrian = row.get("Status Antrian", "").strip()
        harga_jasa_existing = row.get("Harga Jasa", "")
        harga_modal_existing = row.get("Harga Modal", "")
        jenis_existing = row.get("Jenis Transaksi", "Cash") if pd.notna(row.get("Jenis Transaksi", "")) else "Cash"

        with st.expander(f"{no_nota} — {nama} — {barang} ({status_antrian if status_antrian else 'Antrian'})", expanded=False):
            st.write(f"**No Nota:** {no_nota}")
            st.write(f"**Nama:** {nama}")
            st.write(f"**Barang:** {barang}")
            st.write(f"**Status Antrian:** {status_antrian if status_antrian else 'Antrian'}")
            st.write(f"**No HP:** {no_hp}")

            col1, col2 = st.columns(2)
            with col1:
                harga_jasa_input = st.text_input("Harga Jasa (Rp)", value=str(harga_jasa_existing).replace("Rp","").replace(".",""), key=f"hj_{no_nota}")
                harga_modal_input = st.text_input("Harga Modal (Rp)", value=str(harga_modal_existing).replace("Rp","").replace(".",""), key=f"hm_{no_nota}")
            with col2:
                jenis_transaksi = st.radio("Jenis Transaksi", ["Cash", "Transfer"], index=0 if str(jenis_existing).lower()!="transfer" else 1, key=f"jenis_{no_nota}", horizontal=True)

            # KONVERSI HARGA
            try:
                hj_num = int(harga_jasa_input.replace(".","").replace(",","").strip()) if harga_jasa_input else 0
            except:
                hj_num = 0
            hj_str = format_rp(hj_num) if hj_num else ""

            # ================= LOGIKA STATUS ANTRIAN =================
            if status_antrian == "" or status_antrian == "Antrian":
                if st.button("✅ Siap Diambil (Kirim WA)", key=f"ambil_{no_nota}"):
                    update_sheet_row_by_nota(SHEET_SERVIS, no_nota, {
                        "Status Antrian": "Siap Diambil",
                        "Harga Jasa": hj_str,
                        "Harga Modal": format_rp(harga_modal_input),
                        "Jenis Transaksi": jenis_transaksi
                    })
                    kirim_wa_pelanggan(nama, no_nota, no_hp, hj_str, jenis_transaksi)
                    st.success(f"Status Nota {no_nota} diubah ke 'Siap Diambil'")
                    st.rerun()

            elif status_antrian == "Siap Diambil":
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("✔️ Selesai", key=f"selesai_{no_nota}"):
                        update_sheet_row_by_nota(SHEET_SERVIS, no_nota, {"Status Antrian": "Selesai"})
                        st.success(f"Status Nota {no_nota} diubah ke 'Selesai'")
                        st.rerun()
                with col_b:
                    if st.button("❌ Batal", key=f"batal_{no_nota}"):
                        update_sheet_row_by_nota(SHEET_SERVIS, no_nota, {"Status Antrian": "Batal"})
                        st.warning(f"Status Nota {no_nota} diubah ke 'Batal'")
                        st.rerun()

            else:
                st.info(f"📌 Status Antrian: {status_antrian}")

if __name__ == "__main__":
    show()
