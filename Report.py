import streamlit as st
import pandas as pd
import os

DATA_FILE = "service_data.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=[
        "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan", "No HP",
        "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Jasa"
    ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def show():
    st.title("📊 Laporan Servis")

    df = load_data()
    if df.empty:
        st.info("Belum ada data servis.")
        return

    st.dataframe(df)

    # Hapus data
    pilih = st.multiselect("Pilih baris untuk dihapus:", df.index, format_func=lambda x: f"{df.loc[x, 'Nama Pelanggan']} - {df.loc[x, 'Barang']}")
    if st.button("🗑️ Hapus Terpilih"):
        if pilih:
            df = df.drop(pilih).reset_index(drop=True)
            save_data(df)
            st.success("Data berhasil dihapus.")
            st.rerun()
        else:
            st.warning("Belum ada data yang dipilih.")
