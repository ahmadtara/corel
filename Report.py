import streamlit as st
import pandas as pd
import datetime
import os
import json
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# =============== KONFIGURASI FILE ===============
DATA_FILE = "service_data.csv"
CONFIG_FILE = "config.json"
COUNTER_FILE = "nota_counter.txt"

# Folder Drive tujuan
GDRIVE_FOLDER_ID = "12DDRZahmr5pkrmoasagsAvWPoFVNJ6Ze"

# Konfigurasi Google OAuth
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CLIENT_SECRET_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# =============== AUTENTIKASI GOOGLE DRIVE ===============
def save_token(creds):
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())

def load_token():
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_token(creds)
        return creds
    return None

def get_drive_service():
    creds = load_token()
    if creds:
        return build('drive', 'v3', credentials=creds)

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri="https://tara-capslock.streamlit.app/"
    )

    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]
        flow.fetch_token(code=code)
        creds = flow.credentials
        save_token(creds)
        st.success("✅ Autentikasi Google berhasil! Klik ulang tombol Simpan.")
        st.rerun()

    auth_url, _ = flow.authorization_url(
        prompt='consent', access_type='offline', include_granted_scopes='true'
    )
    st.markdown(f"[🔐 Login Google Drive]({auth_url})", unsafe_allow_html=True)
    st.stop()

# =============== UPLOAD FILE KE DRIVE ===============
def upload_to_drive(local_path, filename):
    try:
        service = get_drive_service()
        if not service:
            st.error("❌ Gagal konek ke Google Drive")
            return

        file_metadata = {'name': filename, 'parents': [GDRIVE_FOLDER_ID]}
        media = MediaFileUpload(local_path, resumable=True)
        uploaded = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        link = f"https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}"
        st.info(f"✅ File **{filename}** berhasil diupload ke [Google Drive]({link})")
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
            current = int(f.read().strip() or 0)
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
        "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Jasa"
    ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)
    # upload ke drive juga
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
        if not all([nama, no_hp, barang]):
            st.error("Nama, Nomor HP, dan Barang wajib diisi!")
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
            "Harga Jasa": ""
        }])

        df = pd.concat([df, new], ignore_index=True)
        save_data(df)

        # WhatsApp message
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
Dapatkan Promo Mahasiswa
=======================

Best Regard
Admin {cfg['nama_toko']}
Terima Kasih 🙏"""

        no_hp = str(no_hp).replace("+", "").replace(" ", "").strip()
        link = f"https://wa.me/{no_hp}?text={requests.utils.quote(msg)}"

        st.success(f"✅ Servis {barang} berhasil disimpan dan diupload ke Google Drive!")
        st.markdown(f"[📲 KIRIM NOTA SERVIS VIA WHATSAPP]({link})", unsafe_allow_html=True)


# =============== RUN PAGE ===============
show()
