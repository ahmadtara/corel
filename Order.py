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
        "telepon": "085172174759"
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
def save_to_firebase(data, path="servis"):
    try:
        r = requests.post(f"{FIREBASE_URL}/{path}.json", json=data)
        if r.status_code == 200:
            return True
        else:
            st.warning(f"Gagal simpan ke Firebase ({path}): {r.text}")
            return False
    except Exception as e:
        st.error(f"Error koneksi Firebase ({path}): {e}")
        return False


# ---------------------- MUAT DATA STOK DARI FIREBASE ----------------------
def load_stok_barang():
    try:
        r = requests.get(f"{FIREBASE_URL}/stok_barang.json")
        if r.status_code == 200 and r.text != "null":
            data = r.json()
            df = pd.DataFrame.from_dict(data, orient="index")
            return df
    except:
        pass
    return pd.DataFrame(columns=["nama_barang", "modal", "harga_jual", "qty"])


# ---------------------- PAGE ----------------------
def show():
    cfg = load_config()
    st.title("🧾 Transaksi Servis & Barang")

    tab1, tab2 = st.tabs(["🛠️ Servis Baru", "🧰 Transaksi Barang"])

    # =============================================
    # TAB 1 : SERVIS (kode lama kamu utuh)
    # =============================================
    with tab1:
        with st.form("form_service"):
            tanggal_masuk = st.date_input("Tanggal Masuk", value=datetime.date.today())
            estimasi = st.date_input("Estimasi Selesai", value=datetime.date.today() + datetime.timedelta(days=3))
            nama = st.text_input("Nama Pelanggan")
            no_hp = st.text_input("Nomor WhatsApp", placeholder="6281234567890 (tanpa +)")
            barang = st.text_input("Nama Barang", placeholder="Laptop ASUS A409")
            kerusakan = st.text_area("Detail Kerusakan", placeholder="Tidak bisa booting, Install Ulang")
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
            save_to_firebase(firebase_data, "servis")

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

    # =============================================
    # TAB 2 : TRANSAKSI BARANG / ACCESSORIES
    # =============================================
    with tab2:
        st.subheader("🧰 Penjualan Accessories / Sparepart")
        stok_df = load_stok_barang()

        if stok_df.empty:
            st.warning("Belum ada data stok barang dari Admin.py")
            return

        nama_barang = st.selectbox("Pilih Barang", stok_df["nama_barang"])
        barang_row = stok_df[stok_df["nama_barang"] == nama_barang].iloc[0]

        modal = barang_row.get("modal", 0)
        harga_default = barang_row.get("harga_jual", 0)
        stok = int(barang_row.get("qty", 0))

        harga_jual = st.number_input("Harga Jual (boleh ubah manual)", value=float(harga_default))
        qty = st.number_input("Jumlah Beli", min_value=1, max_value=stok if stok > 0 else 1)
        nama_pembeli = st.text_input("Nama Pembeli (opsional)")
        tanggal = datetime.date.today()

        if st.button("💾 Simpan Transaksi"):
            total = harga_jual * qty
            transaksi_data = {
                "tanggal": tanggal.strftime("%d/%m/%Y"),
                "nama_barang": nama_barang,
                "modal": modal,
                "harga_jual": harga_jual,
                "qty": qty,
                "total": total,
                "pembeli": nama_pembeli,
                "timestamp": datetime.datetime.now().isoformat()
            }

            if save_to_firebase(transaksi_data, "transaksi"):
                st.success(f"✅ Transaksi {nama_barang} berhasil disimpan ke Firebase (Total: Rp{total:,.0f})")
            else:
                st.error("Gagal menyimpan transaksi ke Firebase.")
