# pelanggan.py (v1.0) - Cari pelanggan, input Harga Jasa/Harga Modal/Jenis Transaksi, simpan & kirim WA
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
        return pd.DataFrame(ws.get_all_records())
    except Exception as e:
        st.warning(f"Gagal membaca sheet {sheet_name}: {e}")
        return pd.DataFrame()

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

def format_rp(n):
    try:
        nnum = int(n)
        return f"Rp {nnum:,.0f}".replace(",", ".")
    except:
        return str(n)

# ------------------- APP -------------------
def show():
    cfg = load_config()
    st.title("📱 Pelanggan — Input Harga & Kirim WA Otomatis")

    df = read_sheet(SHEET_SERVIS)
    if df.empty:
        st.info("Belum ada data di sheet Servis.")
        return

    # normalisasi header (pastikan beberapa kolom ada)
    for col in ["No Nota", "Nama Pelanggan", "No HP", "Barang", "Status", "Harga Jasa", "Harga Modal", "Jenis Transaksi"]:
        if col not in df.columns:
            df[col] = ""

    # Search input
    st.markdown("### 🔎 Cari Pelanggan")
    q = st.text_input("Cari berdasarkan Nama atau No Nota (ketik lalu Enter)")

    if q.strip():
        q_lower = q.strip().lower()
        mask = df["Nama Pelanggan"].astype(str).str.lower().str.contains(q_lower) | df["No Nota"].astype(str).str.lower().str.contains(q_lower)
        results = df[mask].copy()
        if results.empty:
            st.info("Tidak ditemukan pelanggan dengan kata kunci tersebut.")
            return
    else:
        # jika kosong, tampilkan beberapa entri terakhir untuk navigasi
        results = df.tail(50).copy()

    # Tampilkan daftar hasil (expanders)
    st.markdown(f"Menampilkan {len(results)} hasil.")
    for idx, row in results.iterrows():
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

            col1, col2 = st.columns(2)
            with col1:
                harga_jasa_input = st.text_input("Masukkan Harga Jasa (Rp):", value=str(harga_jasa_existing).replace("Rp","").replace(".",""), key=f"hj_{no_nota}")
                harga_modal_input = st.text_input("Masukkan Harga Modal (Rp):", value=str(harga_modal_existing).replace("Rp","").replace(".",""), key=f"hm_{no_nota}")
            with col2:
                jenis_transaksi = st.radio("Jenis Transaksi:", ["Cash", "Transfer"], index=0 if str(jenis_existing).lower()!="transfer" else 1, key=f"jenis_{no_nota}", horizontal=True)
                status_select = st.selectbox("Status:", options=["Cek Dulu","Proses","Selesai","Lunas"], index=0 if status not in ["Proses","Selesai","Lunas"] else ["Cek Dulu","Proses","Selesai","Lunas"].index(status), key=f"status_{no_nota}")

            if st.button("✅ Simpan & Kirim WA", key=f"kirim_{no_nota}"):
                # parsing numeric
                try:
                    hj_num = int(str(harga_jasa_input).replace(".","").replace(",","").strip()) if str(harga_jasa_input).strip() else 0
                except:
                    hj_num = 0
                try:
                    hm_num = int(str(harga_modal_input).replace(".","").replace(",","").strip()) if str(harga_modal_input).strip() else 0
                except:
                    hm_num = 0

                hj_str = format_rp(hj_num) if hj_num else ""
                hm_str = format_rp(hm_num) if hm_num else ""

                updates = {
                    "Harga Jasa": hj_str,
                    "Harga Modal": hm_str,
                    "Status": status_select,
                    "Jenis Transaksi": jenis_transaksi
                }

                ok = update_sheet_row_by_nota(SHEET_SERVIS, no_nota, updates)
                if ok:
                    st.success(f"✅ Nota {no_nota} diperbarui di Google Sheet.")
                else:
                    st.error("Gagal memperbarui sheet.")

                # kirim WA (pesan sesuai format lama — tidak diubah)
                msg = f"""Assalamualaikum {nama},

Unit anda dengan nomor nota *{no_nota}* sudah selesai dan siap untuk diambil.

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

if __name__ == "__main__":
    show()
