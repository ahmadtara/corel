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
    st.title("📊 Laporan Servis Capslock Komputer")

    df = load_data()
    if df.empty:
        st.info("Belum ada data servis.")
        return

    # Konversi tanggal
    try:
        df["Tanggal"] = pd.to_datetime(df["Tanggal"])
    except:
        pass

    # Statistik umum
    total_servis = len(df)
    total_selesai = len(df[df["Status"] == "Selesai"])
    total_proses = len(df[df["Status"] != "Selesai"])

    # Hitung total pemasukan
    def to_number(x):
        try:
            return float(str(x).replace(",", "").replace(".", ""))
        except:
            return 0

    df["HargaNum"] = df["Harga Jasa"].apply(to_number)
    total_pemasukan = df[df["Status"] == "Selesai"]["HargaNum"].sum()

    # Ringkasan
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Total Servis", total_servis)
    col2.metric("✅ Selesai", total_selesai)
    col3.metric("🛠️ Proses", total_proses)
    col4.metric("💰 Total Pemasukan", f"Rp {total_pemasukan:,.0f}")

    st.divider()

    # Filter laporan
    status_filter = st.multiselect("Filter berdasarkan status:", ["Selesai", "Diterima", "Cek Dulu", "DP", "Lunas"], default=[])
    if status_filter:
        df = df[df["Status"].isin(status_filter)]

    date_filter = st.date_input("Filter berdasarkan tanggal masuk", [])
    if date_filter:
        df = df[df["Tanggal"].dt.date.isin(date_filter)]

    # Tabel
    st.dataframe(df.drop(columns=["HargaNum"]), use_container_width=True)

    # Tombol hapus data tertentu
    st.divider()
    st.subheader("🗑️ Hapus Beberapa Data")
    pilih_hapus = st.multiselect(
        "Pilih data servis yang ingin dihapus:",
        options=df.index,
        format_func=lambda x: f"{df.loc[x,'Nama Pelanggan']} - {df.loc[x,'Barang']} ({df.loc[x,'Status']})"
    )

    if st.button("🚮 Hapus Data Terpilih"):
        if len(pilih_hapus) > 0:
            df = df.drop(pilih_hapus).reset_index(drop=True)
            df.to_csv(DATA_FILE, index=False)
            st.success("✅ Data yang dipilih telah dihapus.")
            st.rerun()
        else:
            st.warning("Pilih data terlebih dahulu.")

    # Download CSV
    st.divider()
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Laporan CSV",
        data=csv,
        file_name=f"Laporan_Servis_{datetime.date.today()}.csv",
        mime="text/csv"
    )
