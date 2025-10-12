# pelanggan.py (v1.5) - Menu Antrian / Siap Diambil / Selesai / Batal
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

# ------------------- OPTIMASI BACA SHEET -------------------
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

def format_rp(n):
    try:
        nnum = int(n)
        return f"Rp {nnum:,.0f}".replace(",", ".")
    except:
        return str(n)

def get_waktu_jakarta():
    tz = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz)

# ------------------- VIEW DATA -------------------
def render_data(df, status_filter, cfg):
    filtered = df[df["Status"] == status_filter] if status_filter != "Semua" else df
    if filtered.empty:
        st.info(f"Belum ada data di status **{status_filter}**.")
        return

    for idx, row in filtered.iterrows():
        no_nota = row.get("No Nota", "")
        nama = row.get("Nama Pelanggan", "")
        barang = row.get("Barang", "")
        status = row.get("Status", "")
        harga_jasa_existing = row.get("Harga Jasa", "")
        harga_modal_existing = row.get("Harga Modal", "")
        jenis_existing = row.get("Jenis Transaksi", "Cash") if pd.notna(row.get("Jenis Transaksi", "")) else "Cash"
        no_hp = row.get("No HP", "")

        with st.expander(f"{no_nota} — {nama} — {barang} ({status})", expanded=False):
            st.write(f"**No Nota:** {no_nota}")
            st.write(f"**Nama:** {nama}")
            st.write(f"**Barang:** {barang}")
            st.write(f"**Status:** {status}")
            st.write(f"**No HP:** {no_hp}")

            # input harga hanya di tab Antrian
            if status_filter == "Antrian":
                col1, col2 = st.columns(2)
                with col1:
                    harga_jasa_input = st.text_input("Harga Jasa", value=str(harga_jasa_existing).replace("Rp","").replace(".",""), key=f"hj_{no_nota}")
                    harga_modal_input = st.text_input("Harga Modal", value=str(harga_modal_existing).replace("Rp","").replace(".",""), key=f"hm_{no_nota}")
                with col2:
                    jenis_transaksi = st.radio("Jenis Transaksi:", ["Cash", "Transfer"], index=0 if str(jenis_existing).lower()!="transfer" else 1, key=f"jenis_{no_nota}", horizontal=True)

                if st.button("✅ Simpan & Kirim WA", key=f"kirim_{no_nota}"):
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

                    updates = {
                        "Harga Jasa": hj_str,
                        "Harga Modal": hm_str,
                        "Jenis Transaksi": jenis_transaksi,
                        "Status": "Siap Diambil"
                    }
                    ok = update_sheet_row_by_nota(SHEET_SERVIS, no_nota, updates)
                    if ok:
                        st.success(f"✅ Nota {no_nota} dipindahkan ke 'Siap Diambil'.")
                        send_wa(no_hp, nama, no_nota, hj_str, jenis_transaksi, cfg)
                        st.cache_data.clear()
                        st.rerun()

            # tombol aksi di tab Siap Diambil
            elif status_filter == "Siap Diambil":
                col_a, col_b = st.columns(2)
                if col_a.button("✔️ Selesai", key=f"selesai_{no_nota}"):
                    update_sheet_row_by_nota(SHEET_SERVIS, no_nota, {"Status": "Selesai"})
                    st.success(f"Nota {no_nota} ditandai Selesai.")
                    st.cache_data.clear()
                    st.rerun()
                if col_b.button("❌ Batal", key=f"batal_{no_nota}"):
                    update_sheet_row_by_nota(SHEET_SERVIS, no_nota, {"Status": "Batal"})
                    st.warning(f"Nota {no_nota} ditandai Batal.")
                    st.cache_data.clear()
                    st.rerun()

def send_wa(no_hp, nama, no_nota, hj_str, jenis_transaksi, cfg):
    msg = f"""Assalamualaikum {nama},

Unit anda dengan nomor nota *{no_nota}* sudah *selesai servis* dan siap untuk diambil.

Total Biaya Servis: *{hj_str if hj_str else '(Cek Dulu)'}*

Pembayaran: *{jenis_transaksi}*

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

# ------------------- APP -------------------
def show():
    cfg = load_config()
    st.title("📱 Pelanggan — Antrian & WA Otomatis")

    if st.button("🔄 Reload Data Sheet"):
        st.cache_data.clear()
        st.rerun()

    df = read_sheet(SHEET_SERVIS)
    if df.empty:
        st.info("Belum ada data di sheet Servis.")
        return

    # pastikan kolom penting ada
    for col in ["Tanggal Masuk","No Nota","Nama Pelanggan","No HP","Barang","Status","Harga Jasa","Harga Modal","Jenis Transaksi"]:
        if col not in df.columns:
            df[col] = ""

    tab1, tab2, tab3, tab4 = st.tabs(["🧾 Antrian", "📦 Siap Diambil", "✅ Selesai", "🚫 Batal"])

    with tab1:
        render_data(df, "Antrian", cfg)
    with tab2:
        render_data(df, "Siap Diambil", cfg)
    with tab3:
        render_data(df, "Selesai", cfg)
    with tab4:
        render_data(df, "Batal", cfg)

if __name__ == "__main__":
    show()
