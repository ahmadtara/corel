import streamlit as st
import pandas as pd
import datetime
import os
import requests
import json

# ---------------------- KONFIGURASI ----------------------
DATA_FILE = "service_data.csv"
CONFIG_FILE = "config.json"
COUNTER_FILE = "nota_counter.txt"
FIREBASE_URL = "https://toko-4960c-default-rtdb.asia-southeast1.firebasedatabase.app/"  # <--- pastikan ini benar


# ---------------------- CONFIG ----------------------
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


# ---------------------- DATA ----------------------
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=[
        "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan", "No HP",
        "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Jasa"
    ])


def save_data(df):
    df.to_csv(DATA_FILE, index=False)


# ---------------------- SIMPAN KE FIREBASE ----------------------
def save_to_firebase(data):
    try:
        r = requests.post(f"{FIREBASE_URL}/servis.json", json=data)
        if r.status_code == 200:
            return True
        else:
            st.warning(f"Gagal simpan ke Firebase: {r.text}")
            return False
    except Exception as e:
        st.error(f"Error koneksi Firebase: {e}")
        return False


# ---------------------- PAGE ----------------------
def show():
    cfg = load_config()
    st.title("🧾 Servis Baru")

    with st.form("form_service"):
        tanggal_masuk = st.date_input("Tanggal Masuk", value=datetime.date.today())
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

        tanggal_masuk_str = tanggal_masuk.strftime("%d/%m/%Y")
        estimasi_selesai = estimasi.strftime("%d/%m/%Y")

        new = pd.DataFrame([{
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
        }])

        df = pd.concat([df, new], ignore_index=True)
        save_data(df)

        # --- Simpan ke Firebase ---
        firebase_data = {
            "no_nota": nota,
            "tanggal_masuk": tanggal_masuk_str,
            "estimasi_selesai": estimasi_selesai,
            "nama_pelanggan": nama,
            "no_hp": no_hp,
            "barang": barang,
            "kerusakan": kerusakan,
            "kelengkapan": kelengkapan,
            "status": "Cek Dulu",
            "harga_jasa": "",
            "timestamp": datetime.datetime.now().isoformat()
        }
        save_to_firebase(firebase_data)

        # --- Format pesan WhatsApp ---
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

        st.success(f"✅ Servis {barang} berhasil disimpan dan dikirim ke Firebase!")
        st.markdown(f"[📲 KIRIM NOTA SERVIS VIA WHATSAPP]({link})", unsafe_allow_html=True)
