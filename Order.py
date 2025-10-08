import streamlit as st
import pandas as pd
import datetime
import os
import requests
import json

DATA_FILE = "service_data.csv"
CONFIG_FILE = "config.json"
COUNTER_FILE = "nota_counter.txt"

# ---------------------- CONFIG ----------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Computer",
        "alamat": "Jl. Buluh Cina, Panam",
        "telepon": "0851-7217-4759",
        "footer_nota": "Terima kasih sudah servis di Capslock Computer 🙏",
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
        df = pd.read_csv(DATA_FILE)
    else:
        df = pd.DataFrame(columns=[
            "No Nota", "Tanggal Masuk", "Estimasi Selesai",
            "Nama Pelanggan", "No HP", "Barang",
            "Kerusakan", "Kelengkapan", "Status", "Harga Jasa"
        ])

    for col in [
        "No Nota", "Tanggal Masuk", "Estimasi Selesai",
        "Nama Pelanggan", "No HP", "Barang",
        "Kerusakan", "Kelengkapan", "Status", "Harga Jasa"
    ]:
        if col not in df.columns:
            df[col] = ""

    return df


def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ---------------------- PAGE ----------------------
def show():
    cfg = load_config()
    st.title("🧾 Input Servis Baru")

    with st.form("form_service"):
        nama = st.text_input("Nama Pelanggan")
        no_hp = st.text_input("Nomor WhatsApp", placeholder="6281234567890 (tanpa +)")
        barang = st.text_input("Nama Barang", placeholder="Laptop ASUS A409")
        kerusakan = st.text_area("Detail Kerusakan", placeholder="Tidak bisa booting")
        kelengkapan = st.text_area("Kelengkapan", placeholder="Charger, Tas")
        estimasi = st.datetime_input("Estimasi Selesai", value=datetime.datetime.now() + datetime.timedelta(days=3))
        submitted = st.form_submit_button("📲 Kirim Nota Servis")

    if submitted:
        if not all([nama, no_hp, barang]):
            st.error("Nama, Nomor HP, dan Barang wajib diisi!")
            return

        df = load_data()
        nota = get_next_nota()
        now = datetime.datetime.now()
        tanggal_masuk = now.strftime("%d/%m/%Y - %H:%M")
        estimasi_selesai = estimasi.strftime("%d/%m/%Y - %H:%M")

        new = pd.DataFrame([{
            "No Nota": nota,
            "Tanggal Masuk": tanggal_masuk,
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

        # Format pesan WhatsApp (Sesuai format kamu)
        msg = f"""NOTA ELEKTRONIK

💻*{cfg['nama_toko']}*💻
{cfg['alamat']}
HP : {cfg['telepon']}

=======================
*No Nota :* {nota}

*Pelanggan :* {nama}

*Tanggal Masuk :* {tanggal_masuk}
*Estimasi Selesai :* {estimasi_selesai}
=======================
*{barang}*
{kerusakan}
{kelengkapan}
=======================
*Harga :* 
*Status :* Cek Dulu
Dapatkan Promo Mahasiswa
=======================

Best Regard
Admin {cfg['nama_toko']}
Terima Kasih 🙏
"""

        # Kirim langsung ke WhatsApp
        no_hp = str(no_hp).replace("+", "").replace(" ", "").strip()
        link = f"https://wa.me/{no_hp}?text={requests.utils.quote(msg)}"

        st.success(f"✅ Nota {nota} berhasil dibuat untuk {nama}.")
        st.markdown(f"[📲 Klik di sini untuk Kirim WhatsApp]({link})", unsafe_allow_html=True)
        st.markdown("---")

    # ===========================
    st.subheader("📋 Daftar Servis Masuk")

    df = load_data()
    if df.empty:
        st.info("Belum ada data servis.")
        return

    # Pilih beberapa data yang ingin dihapus
    st.markdown("### 🗑️ Hapus Beberapa Data")
    pilih_hapus = st.multiselect(
        "Pilih servis yang ingin dihapus:",
        options=df.index,
        format_func=lambda x: f"{df.loc[x, 'Nama Pelanggan']} - {df.loc[x, 'Barang']} ({df.loc[x, 'Status']})"
    )
    if st.button("🚮 Hapus yang Dipilih"):
        if pilih_hapus:
            df = df.drop(pilih_hapus).reset_index(drop=True)
            save_data(df)
            st.success("✅ Data terpilih berhasil dihapus.")
            st.rerun()
        else:
            st.warning("Pilih data yang ingin dihapus dulu!")

    st.divider()

    for i, row in df.iterrows():
        with st.expander(f"{row['Nama Pelanggan']} - {row['Barang']} ({row['Status']})"):
            st.write(f"🧾 **No Nota:** {row['No Nota']}")
            st.write(f"📅 **Masuk:** {row['Tanggal Masuk']}")
            st.write(f"⏰ **Estimasi Selesai:** {row['Estimasi Selesai']}")
            st.write(f"📞 **No HP:** {row['No HP']}")
            st.write(f"💻 **Barang:** {row['Barang']}")
            st.write(f"🧩 **Kerusakan:** {row['Kerusakan']}")
            st.write(f"🎒 **Kelengkapan:** {row['Kelengkapan']}")
            st.write(f"💰 **Harga Jasa:** {row['Harga Jasa'] if row['Harga Jasa'] else '-'}")
            st.write(f"📦 **Status:** {row['Status']}")

            col1, col2, col3 = st.columns(3)
            with col1:
                harga_input = st.text_input(
                    f"Harga Jasa #{i}",
                    value=str(row["Harga Jasa"]) if row["Harga Jasa"] else "",
                    key=f"harga_{i}"
                )
                if st.button(f"✅ Tandai Lunas #{i}", key=f"done_{i}"):
                    if harga_input.strip() == "":
                        st.warning("Masukkan harga jasa terlebih dahulu.")
                    else:
                        df.at[i, "Status"] = "Lunas"
                        df.at[i, "Harga Jasa"] = harga_input
                        save_data(df)
                        st.success(f"Servis {row['Barang']} selesai (Rp {harga_input}).")
                        st.rerun()

            with col2:
                if st.button(f"💬 Kirim Ulang WA #{i}", key=f"wa_{i}"):
                    msg = f"""NOTA ELEKTRONIK

💻*{cfg['nama_toko']}*💻
{cfg['alamat']}
HP : {cfg['telepon']}

=======================
*No Nota :* {row['No Nota']}

*Pelanggan :* {row['Nama Pelanggan']}

*Tanggal Masuk :* {row['Tanggal Masuk']}
*Estimasi Selesai :* {row['Estimasi Selesai']}
=======================
*{row['Barang']}*
{row['Kerusakan']}
{row['Kelengkapan']}
=======================
*Harga :* {row['Harga Jasa'] if row['Harga Jasa'] else '(Cek Dulu)'}
*Status :* {row['Status']}
Dapatkan Promo Mahasiswa
=======================

Best Regard
Admin {cfg['nama_toko']}
Terima Kasih 🙏
"""
                    no_hp = str(row["No HP"]).replace("+", "").replace(" ", "").strip()
                    link = f"https://wa.me/{no_hp}?text={requests.utils.quote(msg)}"
                    st.markdown(f"[📲 Kirim WhatsApp ke {no_hp}]({link})", unsafe_allow_html=True)

            with col3:
                if st.button(f"🗑️ Hapus #{i}", key=f"del_{i}"):
                    df = df.drop(index=i).reset_index(drop=True)
                    save_data(df)
                    st.success(f"Data servis {row['Barang']} dihapus.")
                    st.rerun()
