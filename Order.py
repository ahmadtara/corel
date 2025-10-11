import streamlit as st
import pandas as pd
import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ================= CONFIG ==================
DATA_FILE = "service_data.csv"
CONFIG_FILE = "config.json"
COUNTER_FILE = "nota_counter.txt"

SPREADSHEET_ID = "1zrgkTKGcq6_fdGRBkHYj5Km8nuyOdM6d3Wjetq8ucpk"
SHEET_SERVIS = "Servis"
SHEET_TRANSAKSI = "Transaksi"
SHEET_STOK = "Stok"

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

# =============== NOMOR NOTA ===============
def get_next_nota():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w") as f:
            f.write("1")
        return "TRX/0000001"
    else:
        with open(COUNTER_FILE, "r") as f:
            current = int(f.read().strip() or 0)
        next_num = current + 1
        with open(COUNTER_FILE, "w") as f:
            f.write(str(next_num))
        return f"TRX/{next_num:07d}"

# =============== SPREADSHEET OPS ===============
def append_to_sheet(sheet_name, data: dict):
    ws = get_worksheet(sheet_name)
    headers = ws.row_values(1)
    row = [data.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")

def read_sheet(sheet_name):
    ws = get_worksheet(sheet_name)
    df = pd.DataFrame(ws.get_all_records())
    return df

# =============== PAGE APP ===============
def show():
    cfg = load_config()
    st.title("🧾 Transaksi Servis & Barang")

    tab1, tab2 = st.tabs(["🛠️ Servis Baru", "🧰 Transaksi Barang"])

    # --------------------------------------
    # TAB 1 : SERVIS BARU
    # --------------------------------------
    with tab1:
        with st.form("form_service"):
            tanggal_masuk = st.date_input("Tanggal Masuk", value=datetime.date.today())
            estimasi = st.date_input("Estimasi Selesai", value=datetime.date.today() + datetime.timedelta(days=3))
            nama = st.text_input("Nama Pelanggan", placeholder="King Dion")
            no_hp = st.text_input("Nomor WhatsApp", placeholder="081234567890")
            barang = st.text_input("Nama Barang", placeholder="Laptop ASUS A409")
            kerusakan = st.text_area("Detail Kerusakan", placeholder="Tidak bisa booting, Install Ulang")
            kelengkapan = st.text_area("Kelengkapan", placeholder="Charger, Tas")
            submitted = st.form_submit_button("💾 Simpan Servis")

        if submitted:
            if not all([nama, no_hp, barang]):
                st.error("Nama, Nomor HP, dan Barang wajib diisi!")
                return

            nota = get_next_nota()
            tanggal_masuk_str = tanggal_masuk.strftime("%d/%m/%Y")
            estimasi_selesai = estimasi.strftime("%d/%m/%Y")

            service_data = {
                "No Nota": nota,
                "Tanggal Masuk": tanggal_masuk_str,
                "Estimasi Selesai": estimasi_selesai,
                "Nama Pelanggan": nama,
                "No HP": no_hp,
                "Barang": barang,
                "Kerusakan": kerusakan,
                "Kelengkapan": kelengkapan,
                "Status": "Cek Dulu",
                "Harga Jasa": "",
                "Jenis Transaksi": "Servis"
            }

            append_to_sheet(SHEET_SERVIS, service_data)
            st.success(f"✅ Servis {barang} berhasil disimpan ke Google Sheet!")

            msg = f"""🧾 *{cfg['nama_toko']}*
{cfg['alamat']}
HP: {cfg['telepon']}

=======================
*No Nota* : {nota}
*Pelanggan* : {nama}
*Tanggal Masuk* : {tanggal_masuk_str}
*Estimasi Selesai* : {estimasi_selesai}
=======================
{barang}
{kerusakan}
{kelengkapan}
=======================
*Harga* : (Cek Dulu)
*Status* : Cek Dulu
=======================

Best Regard
Admin {cfg['nama_toko']}
Terima Kasih 🙏"""

            no_hp = str(no_hp).replace(" ", "").replace("-", "").replace("+", "").strip()
            if no_hp.startswith("0"):
                no_hp = "62" + no_hp[1:]
            elif not no_hp.startswith("62"):
                no_hp = "62" + no_hp

            link = f"https://wa.me/{no_hp}?text={msg.replace(' ', '%20')}"
            st.markdown(f"[📲 KIRIM NOTA SERVIS VIA WHATSAPP]({link})", unsafe_allow_html=True)

    # --------------------------------------
    # TAB 2 : TRANSAKSI BARANG
    # --------------------------------------
    with tab2:
        st.subheader("🧰 Penjualan Accessories / Sparepart")
        try:
            stok_df = read_sheet(SHEET_STOK)
        except:
            st.warning("Belum ada Sheet bernama 'Stok'.")
            return

        if stok_df.empty:
            st.warning("Belum ada data stok barang di Sheet 'Stok'")
            return

        nama_barang = st.selectbox("Pilih Barang", stok_df["nama_barang"])
        barang_row = stok_df[stok_df["nama_barang"] == nama_barang].iloc[0]

        modal = float(barang_row.get("modal", 0))
        harga_default = float(barang_row.get("harga_jual", 0))
        stok = int(barang_row.get("qty", 0))

        harga_jual = st.number_input("Harga Jual (boleh ubah manual)", value=harga_default)
        qty = st.number_input("Jumlah Beli", min_value=1, max_value=stok if stok > 0 else 1)
        nama_pembeli = st.text_input("Nama Pembeli (opsional)")
        no_hp_pembeli = st.text_input("Nomor WhatsApp Pembeli (opsional)")
        tanggal = datetime.date.today()

        if st.button("💾 Simpan Transaksi"):
            nota = get_next_nota()
            total = harga_jual * qty
            untung = (harga_jual - modal) * qty

            transaksi_data = {
                "No Nota": nota,
                "Tanggal": tanggal.strftime("%d/%m/%Y"),
                "Nama Barang": nama_barang,
                "Modal": modal,
                "Harga Jual": harga_jual,
                "Qty": qty,
                "Total": total,
                "Untung": untung,
                "Pembeli": nama_pembeli,
                "Jenis Transaksi": "Barang"
            }

            append_to_sheet(SHEET_TRANSAKSI, transaksi_data)

            # Update stok
            stok_baru = stok - qty
            ws = get_worksheet(SHEET_STOK)
            cell = ws.find(nama_barang)
            if cell:
                qty_col = [i for i, c in enumerate(stok_df.columns) if c.lower() == "qty"]
                if qty_col:
                    ws.update_cell(cell.row, qty_col[0] + 1, stok_baru)

            st.success(f"✅ Transaksi {nama_barang} tersimpan! Untung: Rp {untung:,.0f}".replace(",", "."))

            # Buat nota WA
            msg = f"""🧾 *{cfg['nama_toko']}*
{cfg['alamat']}
HP: {cfg['telepon']}

No Nota : {nota}
Tanggal : {tanggal.strftime('%d/%m/%Y')}
Barang  : {nama_barang}
Qty     : {qty}
Harga   : Rp {harga_jual:,.0f}
Total   : Rp {total:,.0f}

Terima kasih sudah berbelanja!
"""

            if no_hp_pembeli:
                no_hp = str(no_hp_pembeli).replace(" ", "").replace("-", "").replace("+", "")
                if no_hp.startswith("0"):
                    no_hp = "62" + no_hp[1:]
                elif not no_hp.startswith("62"):
                    no_hp = "62" + no_hp
                link = f"https://wa.me/{no_hp}?text={msg.replace(' ', '%20')}"
                st.markdown(f"[📲 KIRIM NOTA VIA WHATSAPP]({link})", unsafe_allow_html=True)


# Jalankan di Streamlit
if __name__ == "__main__":
    show()
