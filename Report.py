import streamlit as st
import pandas as pd
import os
import json
import requests
import datetime

DATA_FILE = "service_data.csv"
CONFIG_FILE = "config.json"

# ------------------- LOAD CONFIG -------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Buluh Cina, Panam",
        "telepon": "0851-7217-4759"
    }

# ------------------- DATA -------------------
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=[
        "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan", "No HP",
        "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Jasa"
    ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ------------------- PAGE -------------------
def show():
    cfg = load_config()
    st.title("📊 Laporan Servis")

    df = load_data()
    if df.empty:
        st.info("Belum ada data servis.")
        return

    # Konversi tanggal
    try:
        df["Tanggal Masuk"] = pd.to_datetime(df["Tanggal Masuk"], errors="coerce")
    except:
        pass

    # ------------------- FILTER -------------------
    st.sidebar.header("📅 Filter Data")
    tanggal_unik = sorted(df["Tanggal Masuk"].dropna().dt.date.unique())

    if len(tanggal_unik) > 0:
        pilih_tanggal = st.sidebar.selectbox(
            "Pilih tanggal servis:",
            options=["Semua Tanggal"] + [str(t) for t in tanggal_unik],
            index=0
        )
        if pilih_tanggal != "Semua Tanggal":
            df = df[df["Tanggal Masuk"].dt.date == datetime.date.fromisoformat(pilih_tanggal)]
    else:
        st.sidebar.info("Belum ada tanggal untuk difilter.")

    # ------------------- TAMPIL DATA -------------------
    st.dataframe(df, width="stretch")
    st.divider()
    st.subheader("📱 Klik Pelanggan Untuk Kirim WA Otomatis")

    for i, row in df.iterrows():
        with st.expander(f"{row['Nama Pelanggan']} - {row['Barang']} ({row['Status']})"):

            harga_input = st.text_input(
                "Masukkan Harga (contoh: 150000)",
                value=str(row["Harga Jasa"]).replace("Rp ", "").replace(".", "") if pd.notna(row["Harga Jasa"]) else "",
                key=f"harga_{i}"
            )

            if harga_input.strip():
                # Format harga
                try:
                    harga_num = int(harga_input.replace("Rp", "").replace(".", "").replace(",", "").strip())
                    harga_baru = f"Rp {harga_num:,}".replace(",", ".")
                except:
                    harga_baru = harga_input

                # Update CSV otomatis
                df.at[i, "Status"] = "Lunas"
                df.at[i, "Harga Jasa"] = harga_baru
                save_data(df)

                # Buat pesan WA
                msg = f"""Assalamualaikum {row['Nama Pelanggan']},

Unit anda dengan nomor nota *{row['No Nota']}* sudah selesai dan siap untuk diambil.

Total Biaya Servis: *{harga_baru}*

Terima Kasih 🙏
{cfg['nama_toko']}"""

                # Format nomor HP
                no_hp = str(row["No HP"]).replace("+", "").replace(" ", "").strip()
                if no_hp.startswith("0"):
                    no_hp = "62" + no_hp[1:]

                link = f"https://wa.me/{no_hp}?text={requests.utils.quote(msg)}"

                st.success(f"✅ Servis {row['Barang']} ditandai lunas & membuka WhatsApp...")
                st.markdown(f"[📲 Buka WhatsApp]({link})", unsafe_allow_html=True)

                # 🔥 Buka otomatis WA di tab baru
                js = f"""
                <script>
                    setTimeout(function(){{
                        window.open("{link}", "_blank");
                    }}, 800);
                </script>
                """
                st.markdown(js, unsafe_allow_html=True)
                st.stop()

            st.info("Isi harga untuk kirim WA otomatis & update status.")

    # ------------------- HAPUS MASSAL -------------------
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
