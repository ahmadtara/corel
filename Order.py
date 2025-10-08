import streamlit as st
import pandas as pd
import datetime
import os
import json
import requests
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from drive_auth import get_drive_service  # ✅ Login Google cukup di app.py

# =============== KONFIGURASI FILE ===============
DATA_FILE = "service_data.csv"
CONFIG_FILE = "config.json"
COUNTER_FILE = "nota_counter.txt"

# Folder Drive tujuan
GDRIVE_FOLDER_ID = "12DDRZahmr5pkrmoasagsAvWPoFVNJ6Ze"

# =============== UPLOAD FILE KE DRIVE ===============
def upload_to_drive(local_path, filename):
    """Upload file lokal ke Google Drive."""
    try:
        service = get_drive_service()
        if not service:
            st.error("❌ Belum login Google Drive.")
            return

        # Cek apakah file sudah ada → update bukan buat baru
        query = f"name='{filename}' and '{GDRIVE_FOLDER_ID}' in parents and trashed=false"
        result = service.files().list(q=query, fields="files(id, name)").execute()
        files = result.get('files', [])

        file_metadata = {'name': filename, 'parents': [GDRIVE_FOLDER_ID]}
        media = MediaFileUpload(local_path, resumable=True)

        if files:
            file_id = files[0]['id']
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        link = f"https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}"
        st.info(f"✅ File **{filename}** berhasil disinkronkan ke [Google Drive]({link})")

    except HttpError as error:
        st.error("❌ Gagal upload ke Google Drive.")
        st.exception(error)
    except Exception as e:
        st.error("❌ Terjadi kesalahan tak terduga.")
        st.exception(e)

# =============== CONFIG TOKO ===============
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Buluh Cina, Panam",
        "telepon": "0851-7217-4759"
    }

# =============== NOMOR NOTA ===============
def get_next_nota():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w") as f:
            f.write("1")
        return "TRX/0000001"
    else:
        with open(COUNTER_FILE, "r") as f:
            content = f.read().strip()
            current = int(content) if content.isdigit() else 0
        next_num = current + 1
        with open(COUNTER_FILE, "w") as f:
            f.write(str(next_num))
        return f"TRX/{next_num:07d}"

# =============== DATA SERVIS ===============
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=[
        "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan", "No HP",
        "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Modal", "Harga Jasa"
    ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)
    upload_to_drive(DATA_FILE, "service_data.csv")
    upload_to_drive(COUNTER_FILE, "nota_counter.txt")

# =============== UI FORM SERVIS ===============
def show():
    cfg = load_config()
    st.title("🧾 Servis Baru")

    with st.form("form_service"):
        tanggal_masuk_manual = st.date_input("Tanggal Masuk", value=datetime.date.today())
        nama = st.text_input("Nama Pelanggan")
        no_hp = st.text_input("Nomor WhatsApp", placeholder="6281234567890 (tanpa +)")
        barang = st.text_input("Nama Barang", placeholder="Laptop ASUS A409")
        kerusakan = st.text_area("Detail Kerusakan", placeholder="Tidak bisa booting")
        kelengkapan = st.text_area("Kelengkapan", placeholder="Charger, Tas")
        estimasi = st.date_input("Estimasi Selesai", value=datetime.date.today() + datetime.timedelta(days=3))
        submitted = st.form_submit_button("💾 Simpan Servis")

    if submitted:
        if not all([nama.strip(), no_hp.strip(), barang.strip()]):
            st.error("❌ Nama, Nomor HP, dan Barang wajib diisi!")
            return

        df = load_data()
        nota = get_next_nota()
        now = datetime.datetime.now()
        tanggal_masuk_fmt = datetime.datetime.combine(tanggal_masuk_manual, now.time()).strftime("%d/%m/%Y - %H:%M")
        estimasi_selesai_fmt = datetime.datetime.combine(estimasi, now.time()).strftime("%d/%m/%Y - %H:%M")

        new = pd.DataFrame([{
            "No Nota": nota,
            "Tanggal Masuk": tanggal_masuk_fmt,
            "Estimasi Selesai": estimasi_selesai_fmt,
            "Nama Pelanggan": nama,
            "No HP": no_hp,
            "Barang": barang,
            "Kerusakan": kerusakan,
            "Kelengkapan": kelengkapan,
            "Status": "Cek Dulu",
            "Harga Modal": "",
            "Harga Jasa": ""
        }])

        df = pd.concat([df, new], ignore_index=True)
        save_data(df)

        # ========== WhatsApp Message ==========
        msg = f"""NOTA ELEKTRONIK

💻 *{cfg['nama_toko']}* 💻
{cfg['alamat']}
HP : {cfg['telepon']}

=======================
*No Nota* : {nota}
*Pelanggan* : {nama}

*Tanggal Masuk* : {tanggal_masuk_fmt}
*Estimasi Selesai* : {estimasi_selesai_fmt}
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

        no_hp_fmt = str(no_hp).replace("+", "").replace(" ", "").strip()
        link = f"https://wa.me/{no_hp_fmt}?text={requests.utils.quote(msg)}"

        st.success(f"✅ Servis {barang} berhasil disimpan & disinkronkan ke Google Drive.")
        st.markdown(f"[📲 KIRIM NOTA SERVIS VIA WHATSAPP]({link})", unsafe_allow_html=True)
