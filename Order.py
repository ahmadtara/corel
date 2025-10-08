import streamlit as st
import pandas as pd
import datetime
import os
import requests
import json

# ---------------------- CONFIG ----------------------
DATA_FILE = "service_data.csv"
CONFIG_FILE = "config.json"
COUNTER_FILE = "nota_counter.txt"
FIREBASE_URL = "https://toko-4960c-default-rtdb.asia-southeast1.firebasedatabase.app/"  # 🔥 Ganti dengan URL Firebase kamu

# ---------------------- CONFIG TOKO ----------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Buluh Cina, Panam",
        "telepon": "0851-7217-4759"
    }

# ---------------------- NOMOR NOTA ----------------------
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

# ---------------------- DATA LOCAL ----------------------
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=[
        "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan",
        "No HP", "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Jasa"
    ])

def save_data_local(df):
    df.to_csv(DATA_FILE, index=False)

# ---------------------- FIREBASE ----------------------
def save_to_firebase(record):
    """Simpan data ke Firebase Realtime Database"""
    try:
        url = f"{FIREBASE_URL}/service_data.json"
        response = requests.post(url, json=record)
        if response.status_code == 200:
            st.success("✅ Data berhasil disimpan ke Firebase!")
        else:
            st.warning(f"⚠️ Gagal simpan ke Firebase: {response.text}")
    except Exception as e:
        st.error("❌ Gagal mengirim ke Firebase")
        st.exception(e)

# ---------------------- PAGE ----------------------
def show():
    cfg = load_config()
    st.title("🧾 Servis Baru")

    with st.form("form_service"):
        tanggal_masuk = st.date_input("Tanggal Masuk", value=datetime.date.today())  # 🔹 tambahan input tanggal masuk
        estimasi = st.date_input("Estimasi Selesai", value=datetime.date.today() + datetime.timedelta(days=3))
        nama = st.text_input("Nama Pelanggan")
        no_hp = st.text_input("Nomor WhatsApp", placeholder="6281234567890 (tanpa +)")
        barang = st.text_input("Nama Barang", placeholder="Laptop ASUS A409")
        kerusakan = st.text_area("Detail Kerusakan", placeholder="Tidak bisa booting")
        kelengkapan = st.text_area("Kelengkapan", placeholder="Charger, Tas")
        submitted = st.form_submit_button("💾 Simpan Servis")

    if submitted:
        if not all([nama, no_hp, barang]):
            st.error("Nama, Nomor HP, dan Barang wajib diisi!")
            return

        df = load_data()
        nota = get_next_nota()
        now = datetime.datetime.now()
        tanggal_masuk_str = datetime.datetime.combine(tanggal_masuk, now.time()).strftime("%d/%m/%Y - %H:%M")
        estimasi_selesai = datetime.datetime.combine(estimasi, now.time()).strftime("%d/%m/%Y - %H:%M")

        new = {
            "No Nota": nota,
            "Tanggal Masuk": tanggal_masuk_str,
            "Estimasi Selesai": estimasi_selesai,
            "Nama Pelanggan": nama,
            "No HP": no_hp,
            "Barang": barang,
            "Kerusakan": kerusakan,
            "Kelengkapan": kelengkapan,
            "Status": "Cek Dulu",
            "Harga Jasa": ""
        }

        # Simpan ke CSV dan Firebase
        df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
        save_data_local(df)
        save_to_firebase(new)

        # Format pesan WhatsApp
        msg = f"""NOTA ELEKTRONIK

💻 *{cfg['nama_toko']}* 💻
{cfg['alamat']}
HP : {cfg['telepon']}

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
Dapatkan Promo Mahasiswa
=======================

Best Regard
Admin {cfg['nama_toko']}
Terima Kasih 🙏"""

        no_hp = str(no_hp).replace("+", "").replace(" ", "").strip()
        link = f"https://wa.me/{no_hp}?text={requests.utils.quote(msg)}"

        st.success(f"✅ Servis {barang} berhasil disimpan!")
        st.markdown(f"[📲 KIRIM NOTA SERVIS VIA WHATSAPP]({link})", unsafe_allow_html=True)

# Jalankan Halaman
show()
