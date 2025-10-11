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
SHEET_SERVIS = "Servis"
SHEET_TRANSAKSI = "Transaksi"
SHEET_STOK = "Stok"
CONFIG_FILE = "config.json"
DATA_FILE = "service_data.csv"  # cache lokal

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

# =============== CACHE CSV ===============
def load_local_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=[
        "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan", "No HP",
        "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Jasa", "Harga Modal",
        "Jenis Transaksi", "uploaded"
    ])

def save_local_data(df):
    df.to_csv(DATA_FILE, index=False)

# =============== NOMOR NOTA DARI SHEET ===============
def get_next_nota_from_sheet():
    try:
        ws = get_worksheet(SHEET_SERVIS)
        data = ws.col_values(1)  # kolom A = "No Nota"

        if len(data) <= 1:
            return "TRX/0000001"

        last_nota = None
        for val in reversed(data):
            if val.strip():
                last_nota = val.strip()
                break

        if not last_nota:
            return "TRX/0000001"

        if last_nota.startswith("TRX/"):
            num = int(last_nota.replace("TRX/", ""))
        else:
            num = int(last_nota) if last_nota.isdigit() else 0

        next_num = num + 1
        return f"TRX/{next_num:07d}"
    except Exception as e:
        st.error(f"Gagal membaca nomor nota dari Google Sheet: {e}")
        return "TRX/0000001"

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

# =============== UPLOAD ULANG CACHE ===============
def sync_local_cache():
    df = load_local_data()
    if df.empty:
        return
    not_uploaded = df[df["uploaded"] == False]
    if not not_uploaded.empty:
        st.info(f"🔁 Mengupload ulang {len(not_uploaded)} data tersimpan lokal...")
        for _, row in not_uploaded.iterrows():
            try:
                append_to_sheet(SHEET_SERVIS, row.to_dict())
                df.loc[df["No Nota"] == row["No Nota"], "uploaded"] = True
            except Exception as e:
                st.warning(f"Gagal upload {row['No Nota']}: {e}")
        save_local_data(df)
        st.success("✅ Sinkronisasi cache selesai!")

# =============== PAGE APP ===============
def show():
    cfg = load_config()
    sync_local_cache()
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
            harga_jasa = st.number_input("Harga Jasa (opsional)", min_value=0.0, format="%.0f")
            harga_modal = st.number_input("Harga Modal (opsional)", min_value=0.0, format="%.0f")
            submitted = st.form_submit_button("💾 Simpan Servis")

        if submitted:
            if not all([nama, no_hp, barang]):
                st.error("Nama, Nomor HP, dan Barang wajib diisi!")
                return

            nota = get_next_nota_from_sheet()
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
                "Harga Jasa": harga_jasa,
                "Harga Modal": harga_modal,
                "Jenis Transaksi": "Servis",
                "uploaded": False
            }

            df = load_local_data()
            df = pd.concat([df, pd.DataFrame([service_data])], ignore_index=True)

            try:
                append_to_sheet(SHEET_SERVIS, service_data)
                df.loc[df["No Nota"] == nota, "uploaded"] = True
                st.success(f"✅ Servis {barang} berhasil disimpan ke Google Sheet!")
            except Exception as e:
                st.warning(f"⚠️ Gagal upload ke Sheet: {e}. Disimpan lokal dulu.")

            save_local_data(df)

            msg = f"""*NOTA ELEKTRONIK*

```{cfg['nama_toko']}```
 {cfg['alamat']}
HP :  {cfg['telepon']}

=======================
*No Nota* : {nota}
*Pelanggan* : {nama}
*Tanggal Masuk* : {tanggal_masuk_str}
*Estimasi Selesai* : {estimasi_selesai}
=======================
Barang : {barang}
Kerusakan : {kerusakan}
Kelengkapan : {kelengkapan}
=======================
*Harga* : (Cek Dulu)
*Status* : Cek Dulu
_Dapatkan Promo Mahasiswa_
=======================

Best Regard,
Admin {cfg['nama_toko']}
Terima Kasih 🙏
"""

            no_hp_clean = str(no_hp).replace("+", "").replace(" ", "").replace("-", "").strip()
            if no_hp_clean.startswith("0"):
                no_hp_clean = "62" + no_hp_clean[1:]
            elif not no_hp_clean.startswith("62"):
                no_hp_clean = "62" + no_hp_clean

            encoded_msg = urllib.parse.quote(msg)
            wa_link = f"https://wa.me/{no_hp_clean}?text={requests.utils.quote(msg)}"
            st.markdown(f"[📲 KIRIM NOTA SERVIS VIA WHATSAPP]({wa_link})", unsafe_allow_html=True)

    # --------------------------------------
    # TAB 2 : TRANSAKSI BARANG
    # --------------------------------------
    with tab2:
        st.subheader("🧰 Penjualan Accessories / Sparepart")

        # --- Baca Stok ---
        try:
            stok_df = read_sheet(SHEET_STOK)
        except:
            stok_df = pd.DataFrame(columns=["nama_barang", "modal", "harga_jual", "qty"])

        if stok_df.empty:
            st.warning("Belum ada data stok barang di Sheet 'Stok'")

        pilihan_input = st.radio(
            "Pilih Cara Input Transaksi:",
            ["📦 Pilih dari Stok", "✍️ Input Manual"],
            horizontal=True
        )

        # =============== CARA 1: PILIH DARI STOK ===============
        if pilihan_input == "📦 Pilih dari Stok" and not stok_df.empty:
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

            if st.button("💾 Simpan Transaksi dari Stok"):
                nota = get_next_nota_from_sheet()
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

                msg = f"""NOTA PENJUALAN

💻 *{cfg['nama_toko']}* 💻
{cfg['alamat']}
HP : {cfg['telepon']}

No Nota : {nota}
Tanggal : {tanggal.strftime('%d/%m/%Y')}
Barang  : {nama_barang}
Qty     : {qty}
Harga   : Rp {harga_jual:,.0f}
Total   : Rp {total:,.0f}

Terima kasih sudah berbelanja!
"""

                if no_hp_pembeli:
                    hp = str(no_hp_pembeli).replace("+", "").replace(" ", "").replace("-", "")
                    if hp.startswith("0"):
                        hp = "62" + hp[1:]
                    elif not hp.startswith("62"):
                        hp = "62" + hp

                    encoded_msg = urllib.parse.quote(msg)
                    wa_link = f"https://wa.me/{hp}?text={requests.utils.quote(msg)}"
                    st.markdown(f"[📲 KIRIM NOTA VIA WHATSAPP]({wa_link})", unsafe_allow_html=True)

        # =============== CARA 2: INPUT MANUAL ===============
        if pilihan_input == "✍️ Input Manual":
            nama_barang_manual = st.text_input("Nama Barang")
            modal_manual = st.number_input("Harga Modal", min_value=0.0, format="%.0f")
            harga_manual = st.number_input("Harga Jual", min_value=0.0, format="%.0f")
            qty_manual = st.number_input("Jumlah Beli", min_value=1)
            nama_pembeli_manual = st.text_input("Nama Pembeli (opsional)")
            no_hp_pembeli_manual = st.text_input("Nomor WhatsApp Pembeli (opsional)")
            tanggal_manual = datetime.date.today()

            if st.button("💾 Simpan Transaksi Manual"):
                if not nama_barang_manual or harga_manual <= 0:
                    st.error("Nama barang dan harga jual wajib diisi!")
                else:
                    nota = get_next_nota_from_sheet()
                    total = harga_manual * qty_manual
                    untung = (harga_manual - modal_manual) * qty_manual

                    transaksi_data = {
                        "No Nota": nota,
                        "Tanggal": tanggal_manual.strftime("%d/%m/%Y"),
                        "Nama Barang": nama_barang_manual,
                        "Modal": modal_manual,
                        "Harga Jual": harga_manual,
                        "Qty": qty_manual,
                        "Total": total,
                        "Untung": untung,
                        "Pembeli": nama_pembeli_manual,
                        "Jenis Transaksi": "Barang"
                    }

                    append_to_sheet(SHEET_TRANSAKSI, transaksi_data)

                    # Cek apakah barang sudah ada di stok
                    ws = get_worksheet(SHEET_STOK)
                    try:
                        cell = ws.find(nama_barang_manual)
                        if cell:
                            # update qty stok bertambah (karena manual dianggap stok tersedia)
                            current_qty = int(stok_df.loc[stok_df['nama_barang'] == nama_barang_manual, 'qty'].iloc[0])
                            ws.update_cell(cell.row, stok_df.columns.get_loc('qty') + 1, current_qty - qty_manual)
                        else:
                            # barang belum ada → buat baru dengan stok awal = 0 - qty_manual
                            headers = ws.row_values(1)
                            row_data = ["" for _ in headers]
                            for idx, h in enumerate(headers):
                                if h.lower() == "nama_barang":
                                    row_data[idx] = nama_barang_manual
                                elif h.lower() == "modal":
                                    row_data[idx] = modal_manual
                                elif h.lower() == "harga_jual":
                                    row_data[idx] = harga_manual
                                elif h.lower() == "qty":
                                    row_data[idx] = 0 - qty_manual
                            ws.append_row(row_data, value_input_option="USER_ENTERED")
                    except Exception as e:
                        st.warning(f"Gagal update stok: {e}")

                    st.success(f"✅ Transaksi manual {nama_barang_manual} tersimpan! Untung: Rp {untung:,.0f}".replace(",", "."))

                    msg = f"""NOTA PENJUALAN

💻 *{cfg['nama_toko']}* 💻
{cfg['alamat']}
HP : {cfg['telepon']}

No Nota : {nota}
Tanggal : {tanggal_manual.strftime('%d/%m/%Y')}
Barang  : {nama_barang_manual}
Qty     : {qty_manual}
Harga   : Rp {harga_manual:,.0f}
Total   : Rp {total:,.0f}

Terima kasih sudah berbelanja!
"""

                    if no_hp_pembeli_manual:
                        hp = str(no_hp_pembeli_manual).replace("+", "").replace(" ", "").replace("-", "")
                        if hp.startswith("0"):
                            hp = "62" + hp[1:]
                        elif not hp.startswith("62"):
                            hp = "62" + hp

                        encoded_msg = urllib.parse.quote(msg)
                        wa_link = f"https://wa.me/{hp}?text={requests.utils.quote(msg)}"
                        st.markdown(f"[📲 KIRIM NOTA VIA WHATSAPP]({wa_link})", unsafe_allow_html=True)



# Jalankan di Streamlit
if __name__ == "__main__":
    show()
