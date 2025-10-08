import streamlit as st
import pandas as pd
import datetime
import os

DATA_FILE = "service_data.csv"

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=[
            "Tanggal","Nama Pelanggan","No HP","Barang",
            "Kerusakan","Kelengkapan","Status","Harga Jasa"
        ])

def show():
    st.title("📊 Laporan Servis")

    df = load_data()
    if df.empty:
        st.info("Belum ada data servis.")
        return

    # Statistik
    total_selesai = df[df["Status"] == "Selesai"].shape[0]
    total_pemasukan = df.loc[df["Status"] == "Selesai", "Harga Jasa"].apply(
        lambda x: float(str(x).replace(",", "").replace(".", "")) if str(x).isdigit() else 0
    ).sum()

    st.metric("Servis Selesai", total_selesai)
    st.metric("Total Pemasukan", f"Rp {total_pemasukan:,.0f}")

    # Tabel data
    st.dataframe(df)

    # Unduh CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Laporan CSV",
        data=csv,
        file_name=f"Laporan_Servis_{datetime.date.today()}.csv",
        mime="text/csv"
    )
