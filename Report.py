import streamlit as st
import pandas as pd
import os

DATA_FILE = "service_data.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=[
            "Tanggal", "Nama Pelanggan", "No HP", "Barang", 
            "Kerusakan", "Kelengkapan", "Status"
        ])

def show():
    st.title("📊 Laporan Servis")

    df = load_data()
    if df.empty:
        st.info("Belum ada data servis.")
        return

    tab1, tab2 = st.tabs(["🛠️ Aktif", "✅ Selesai"])

    with tab1:
        aktif = df[df["Status"] != "Selesai"]
        st.dataframe(aktif, use_container_width=True)

    with tab2:
        selesai = df[df["Status"] == "Selesai"]
        st.dataframe(selesai, use_container_width=True)
