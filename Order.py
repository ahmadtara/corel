import streamlit as st
import pandas as pd
import datetime
import json
import requests
import base64

# ================== KONFIGURASI ==================
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]        # Contoh: "username/nama-repo"
GITHUB_FILE = st.secrets["GITHUB_FILE"]        # Contoh: "service_data.csv"
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

CONFIG_FILE = "config.json"
COUNTER_FILE = "nota_counter.txt"

# ================== FUNGSI GITHUB ==================
def github_get_file():
    """Ambil isi file CSV dari GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = r.json()
        data = base64.b64decode(content["content"]).decode("utf-8")
        sha = content["sha"]
        return data, sha
    else:
        return None, None

def github_update_file(new_content, sha):
    """Update file CSV ke GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    message = f"Update service data - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    data = {
        "message": message,
        "content": content,
        "branch": GITHUB_BRANCH,
        "sha": sha
    }
    r = requests.put(url, headers=headers, data=json.dumps(data))
    if r.status_code in [200, 201]:
        return True
    else:
        st.error(f"Gagal update GitHub: {r.text}")
        return False

# ================== CONFIG TOKO ==================
def load_config():
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Buluh Cina, Panam",
        "telepon": "0851-7217-4759"
    }

# ================== NOMOR NOTA ==================
def get_next_nota():
    import os
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

# ================== DATA ==================
def load_data():
    data, sha = github_get_file()
    if data:
        df = pd.read_csv(pd.compat.StringIO(data))
        return df, sha
    else:
        return pd.DataFrame(columns=[
            "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan", "No HP",
            "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Jasa"
        ]), None

def save_data(df, sha):
    csv_content = df.to_csv(index=False)
    return github_update_file(csv_content, sha)

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
            # Format pesan WA
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
