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

    # Pastikan kolom tanggal terbaca datetime
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
    st.dataframe(df, use_container_width=True)
    st.divider()
    st.subheader("🧰 Update Status & Kirim WhatsApp")

    for i, row in df.iterrows():
        with st.expander(f"{row['Nama Pelanggan']} - {row['Barang']} ({row['Status']})"):
            st.write(f"📅 Masuk : {row['Tanggal Masuk']}")
            st.write(f"⏰ Estimasi : {row['Estimasi Selesai']}")
            st.write(f"📞 HP : {row['No HP']}")
            st.write(f"💻 Barang : {row['Barang']}")
            st.write(f"🔧 Kerusakan : {row['Kerusakan']}")
            st.write(f"🎒 Kelengkapan : {row['Kelengkapan']}")
            st.write(f"💰 Harga Sekarang : {row['Harga Jasa'] if pd.notna(row['Harga Jasa']) else '-'}")

            # Input harga dengan format Rp otomatis
            harga_input = st.text_input(
                f"Masukkan Harga (otomatis format Rp)",
                value=str(row["Harga Jasa"]) if pd.notna(row["Harga Jasa"]) else "",
                key=f"harga_{i}",
                placeholder="Rp 100.000"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"✅ Tandai Selesai & Kirim WA #{i}", key=f"done_{i}"):

                    if harga_input.strip() == "":
                        st.warning("Masukkan harga jasa terlebih dahulu.")
                        st.stop()

                    # Format harga Rp (hapus huruf dan format)
                    harga_baru = harga_input.replace("Rp", "").replace(".", "").replace(",", "").strip()
                    try:
                        harga_baru = f"Rp {int(harga_baru):,}".replace(",", ".")
                    except:
                        harga_baru = harga_input

                    # Update data
                    df.at[i, "Status"] = "Lunas"
                    df.at[i, "Harga Jasa"] = harga_baru
                    save_data(df)

                    # Format pesan WhatsApp
                    msg = f"""Assalamualaikum {row['Nama Pelanggan']},

Unit anda dengan nomor nota {row['No Nota']} sudah selesai dan siap untuk diambil.

Terima Kasih,
{cfg['nama_toko']}"""

                    no_hp = str(row["No HP"]).replace("+", "").replace(" ", "").strip()
                    link = f"https://wa.me/{no_hp}?text={requests.utils.quote(msg)}"

                    # Notifikasi berhasil
                    st.success(f"✅ Servis {row['Barang']} selesai dan tersimpan ({harga_baru}).")

                    # Auto-buka WA via JavaScript
                    js = f"""
                    <script>
                    window.open('{link}', '_blank');
                    </script>
                    """
                    st.components.v1.html(js, height=0, width=0)

                    st.rerun()

            with col2:
                if st.button(f"🗑️ Hapus Data Ini #{i}", key=f"del_{i}"):
                    df = df.drop(index=i).reset_index(drop=True)
                    save_data(df)
                    st.success("Data berhasil dihapus.")
                    st.rerun()

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
