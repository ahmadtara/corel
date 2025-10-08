import streamlit as st
import pandas as pd
import datetime
import json
import requests
import base64
import io

# ================== KONFIGURASI ==================
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

SERVICE_FILE = "service_data.csv"
COUNTER_FILE = "nota_counter.txt"
CONFIG_FILE = "config.json"

# ================== FUNGSI GITHUB GENERIK ==================
def github_get_file(path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = r.json()
        data = base64.b64decode(content["content"]).decode("utf-8")
        sha = content["sha"]
        return data, sha
    return None, None

def github_update_file(path, new_content, sha=None):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    message = f"Update {path} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    data = {"message": message, "content": content, "branch": GITHUB_BRANCH}
    if sha:
        data["sha"] = sha
    r = requests.put(url, headers=headers, data=json.dumps(data))
    return r.status_code in [200, 201]

# ================== CONFIG TOKO ==================
def load_config():
    data, _ = github_get_file(CONFIG_FILE)
    if data:
        return json.loads(data)
    else:
        # Jika file belum ada, buat default dan simpan ke GitHub
        default_cfg = {
            "nama_toko": "Capslock Komputer",
            "alamat": "Jl. Buluh Cina, Panam",
            "telepon": "0851-7217-4759"
        }
        github_update_file(CONFIG_FILE, json.dumps(default_cfg, indent=2))
        return default_cfg

# ================== NOMOR NOTA ==================
def get_next_nota():
    data, sha = github_get_file(COUNTER_FILE)
    if data:
        current = int(data.strip())
    else:
        current = 0
        sha = None
    next_num = current + 1
    github_update_file(COUNTER_FILE, str(next_num), sha)
    return f"TRX/{next_num:07d}"

# ================== DATA SERVIS ==================
def load_data():
    data, sha = github_get_file(SERVICE_FILE)
    if data:
        df = pd.read_csv(io.StringIO(data))
        return df, sha
    else:
        df = pd.DataFrame(columns=[
            "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan",
            "No HP", "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Jasa"
        ])
        return df, None

def save_data(df, sha):
    csv_content = df.to_csv(index=False)
    return github_update_file(SERVICE_FILE, csv_content, sha)

# ================== PAGE ==================
def show():
    cfg = load_config()
    st.title("🧾 Servis Baru")

    df, sha = load_data()

    with st.form("form_service"):
        tanggal_masuk = st.date_input("Tanggal Masuk", value=datetime.date.today())
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

        nota = get_next_nota()
        now = datetime.datetime.now()
        tanggal_masuk_fmt = datetime.datetime.combine(tanggal_masuk, now.time()).strftime("%d/%m/%Y - %H:%M")
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
        if save_data(df, sha):
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

            no_hp_clean = str(no_hp).replace("+", "").replace(" ", "").strip()
            link = f"https://wa.me/{no_hp_clean}?text={requests.utils.quote(msg)}"

            st.success(f"✅ Servis {barang} berhasil disimpan ke GitHub!")
            st.markdown(f"[📲 KIRIM NOTA SERVIS VIA WHATSAPP]({link})", unsafe_allow_html=True)
