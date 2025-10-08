import streamlit as st
import pandas as pd
import os
import json
import requests
import datetime
import io

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

# ===================== KONFIGURASI =====================
DATA_FILE = "service_data.csv"
CONFIG_FILE = "config.json"

GDRIVE_FOLDER_ID = "12DDRZahmr5pkrmoasagsAvWPoFVNJ6Ze"
CLIENT_SECRET_FILE = "credentials.json"
TOKEN_FILE = "token.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# ===================== GOOGLE DRIVE =====================
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
        st.success("✅ Login Google Drive berhasil! Klik ulang tombol Simpan.")
        st.rerun()

    auth_url, _ = flow.authorization_url(
        prompt='consent', access_type='offline', include_granted_scopes='true'
    )
    st.markdown(f"[🔐 Login Google Drive]({auth_url})", unsafe_allow_html=True)
    st.stop()

def get_file_id_by_name(filename):
    service = get_drive_service()
    results = service.files().list(
        q=f"name='{filename}' and '{GDRIVE_FOLDER_ID}' in parents and trashed=false",
        fields="files(id, name)"
    ).execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    return None

def upload_to_drive(local_path, filename):
    try:
        service = get_drive_service()
        file_id = get_file_id_by_name(filename)

        file_metadata = {'name': filename, 'parents': [GDRIVE_FOLDER_ID]}
        media = MediaFileUpload(local_path, resumable=True)

        if file_id:
            # update file jika sudah ada
            service.files().update(fileId=file_id, media_body=media).execute()
        else:
            # upload baru
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()

        link = f"https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}"
        st.info(f"✅ File **{filename}** berhasil disimpan ke [Google Drive]({link})")
    except HttpError as error:
        st.error("❌ Gagal upload ke Google Drive.")
        st.exception(error)
    except Exception as e:
        st.error("❌ Terjadi kesalahan tak terduga saat upload.")
        st.exception(e)

def download_from_drive(filename, local_path):
    try:
        service = get_drive_service()
        file_id = get_file_id_by_name(filename)
        if not file_id:
            return False

        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(local_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return True
    except:
        return False

# ===================== KONFIG TOKO =====================
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Buluh Cina, Panam",
        "telepon": "0851-7217-4759"
    }

# ===================== DATA =====================
# download data dari google drive saat load
download_from_drive(DATA_FILE, DATA_FILE)

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        if "Harga Modal" not in df.columns:
            df["Harga Modal"] = ""
        return df
    return pd.DataFrame(columns=[
        "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan", "No HP",
        "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Jasa", "Harga Modal"
    ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)
    upload_to_drive(DATA_FILE, "service_data.csv")

# ===================== PAGE =====================
def show():
    cfg = load_config()
    st.title("📊 Laporan Servis")

    df = load_data()
    if df.empty:
        st.info("Belum ada data servis.")
        return

    # konversi tanggal
    try:
        df["Tanggal Masuk"] = pd.to_datetime(df["Tanggal Masuk"], errors="coerce")
    except:
        pass

    # ===================== FILTER BULAN =====================
    st.sidebar.header("📅 Filter Laporan per Bulan")
    bulan_unik = sorted(df["Tanggal Masuk"].dropna().dt.to_period("M").unique())
    if len(bulan_unik) > 0:
        pilih_bulan = st.sidebar.selectbox(
            "Pilih Bulan:",
            options=["Semua Bulan"] + [str(b) for b in bulan_unik],
            index=0
        )
        if pilih_bulan != "Semua Bulan":
            df = df[df["Tanggal Masuk"].dt.to_period("M") == pd.Period(pilih_bulan)]

    # ===================== HITUNG REKAP =====================
    def parse_rupiah(s):
        try:
            return int(str(s).replace("Rp", "").replace(".", "").strip())
        except:
            return 0

    total_jasa = df["Harga Jasa"].apply(parse_rupiah).sum()
    total_modal = df["Harga Modal"].apply(parse_rupiah).sum()
    total_untung = total_jasa - total_modal

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Modal", f"Rp {total_modal:,}".replace(",", "."))
    col2.metric("💵 Total Jasa", f"Rp {total_jasa:,}".replace(",", "."))
    col3.metric("📈 Total Untung", f"Rp {total_untung:,}".replace(",", "."))

    # ===================== TAMPIL DATA =====================
    st.dataframe(df, use_container_width=True)
    st.divider()
    st.subheader("📱 Klik Pelanggan Untuk Kirim WA Otomatis")

    for i, row in df.iterrows():
        with st.expander(f"{row['Nama Pelanggan']} - {row['Barang']} ({row['Status']})"):
            # input modal
            modal_input = st.text_input(
                "Harga Modal (tidak dikirim ke WA)",
                value=str(row["Harga Modal"]).replace("Rp ", "").replace(".", "") if pd.notna(row["Harga Modal"]) else "",
                key=f"modal_{i}"
            )
            # input jasa
            harga_input = st.text_input(
                "Harga Jasa (akan dikirim ke WA)",
                value=str(row["Harga Jasa"]).replace("Rp ", "").replace(".", "") if pd.notna(row["Harga Jasa"]) else "",
                key=f"harga_{i}"
            )

            if harga_input.strip():
                # format jasa
                try:
                    harga_num = int(harga_input.replace("Rp", "").replace(".", "").replace(",", "").strip())
                    harga_baru = f"Rp {harga_num:,}".replace(",", ".")
                except:
                    harga_baru = harga_input

                # format modal
                try:
                    if modal_input.strip():
                        modal_num = int(modal_input.replace("Rp", "").replace(".", "").replace(",", "").strip())
                        modal_baru = f"Rp {modal_num:,}".replace(",", ".")
                    else:
                        modal_baru = ""
                except:
                    modal_baru = modal_input

                # update data
                df.at[i, "Status"] = "Lunas"
                df.at[i, "Harga Jasa"] = harga_baru
                df.at[i, "Harga Modal"] = modal_baru
                save_data(df)

                # WA
                msg = f"""Assalamualaikum {row['Nama Pelanggan']},

Unit anda dengan nomor nota *{row['No Nota']}* sudah selesai dan siap untuk diambil.

Total Biaya Servis: *{harga_baru}*

Terima Kasih 🙏
{cfg['nama_toko']}"""

                no_hp = str(row["No HP"]).replace("+", "").replace(" ", "").strip()
                if no_hp.startswith("0"):
                    no_hp = "62" + no_hp[1:]

                link = f"https://wa.me/{no_hp}?text={requests.utils.quote(msg)}"
                st.success(f"✅ Servis {row['Barang']} ditandai lunas & membuka WhatsApp...")
                st.markdown(f"[📲 Buka WhatsApp]({link})", unsafe_allow_html=True)

                js = f"""
                <script>
                    setTimeout(function(){{
                        window.open("{link}", "_blank");
                    }}, 800);
                </script>
                """
                st.markdown(js, unsafe_allow_html=True)
                st.stop()

            st.info("Harga modal hanya untuk laporan internal — tidak dikirim ke WA pelanggan.")

    # ===================== HAPUS MASSAL =====================
    st.divider()
    st.subheader("🗑️ Hapus Beberapa Data Sekaligus")

    pilih = st.multiselect(
        "Pilih servis untuk dihapus:",
        df.index,
        format_func=lambda x: f"{df.loc[x, 'Nama Pelanggan']} - {df.loc[x, 'Barang']}"
    )

    if st.button("🚮 Hapus Terpilih"):
        if pilih:
            df = df.drop(pilih).reset_index(drop=True)
            save_data(df)
            st.success("Data terpilih berhasil dihapus.")
            st.rerun()
        else:
            st.warning("Belum ada data yang dipilih.")

# ===================== RUN =====================
show()
