import streamlit as st
import pandas as pd
import os

DATA_FILE = "service_data.csv"

# ---------------------- LOAD DATA ----------------------
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=[
            "Tanggal", "Nama Pelanggan", "No HP", "Barang", 
            "Kerusakan", "Kelengkapan", "Status"
        ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ---------------------- UI ----------------------
def show():
    st.title("📊 Laporan Servis")

    df = load_data()
    if df.empty:
        st.info("Belum ada data servis.")
        return

    tab1, tab2 = st.tabs(["🛠️ Aktif", "✅ Selesai"])

    # ---------------------- TAB SERVIS AKTIF ----------------------
    with tab1:
        aktif = df[df["Status"] != "Selesai"]
        st.subheader(f"🛠️ Servis Aktif ({len(aktif)})")

        if aktif.empty:
            st.warning("Tidak ada servis aktif.")
        else:
            for i, row in aktif.iterrows():
                with st.expander(f"{row['Nama Pelanggan']} - {row['Barang']}"):
                    st.write(f"📅 {row['Tanggal']}")
                    st.write(f"📞 {row['No HP']}")
                    st.write(f"🧩 {row['Kerusakan']}")
                    st.write(f"🎒 {row['Kelengkapan']}")
                    st.write(f"📦 Status: {row['Status']}")

    # ---------------------- TAB SERVIS SELESAI ----------------------
    with tab2:
        selesai = df[df["Status"] == "Selesai"]
        st.subheader(f"✅ Servis Selesai ({len(selesai)})")

        if selesai.empty:
            st.info("Belum ada servis yang selesai.")
        else:
            for i, row in selesai.iterrows():
                with st.expander(f"{row['Nama Pelanggan']} - {row['Barang']}"):
                    st.write(f"📅 {row['Tanggal']}")
                    st.write(f"📞 {row['No HP']}")
                    st.write(f"🧩 {row['Kerusakan']}")
                    st.write(f"🎒 {row['Kelengkapan']}")
                    st.write(f"📦 Status: {row['Status']}")

                    if st.button(f"🗑️ Hapus Data #{i}", key=f"hapus_{i}"):
                        df = df.drop(i).reset_index(drop=True)
                        save_data(df)
                        st.success(f"✅ Data servis '{row['Barang']}' milik {row['Nama Pelanggan']} sudah dihapus.")
                        st.rerun()
