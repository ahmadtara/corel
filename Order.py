import streamlit as st
import pandas as pd
import datetime
import requests
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

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def show():
    st.title("🧰 Servis Komputer / Laptop")
    st.subheader("Input Data Servis Baru")

    # === Form Input Pelanggan ===
    with st.form("form_service"):
        nama = st.text_input("Nama Pelanggan")
        no_hp = st.text_input("Nomor WhatsApp", placeholder="+6281234567890")
        barang = st.text_input("Nama Barang", placeholder="Laptop ASUS A409")
        kerusakan = st.text_area("Detail Kerusakan", placeholder="Tidak bisa booting, muncul blue screen")
        kelengkapan = st.text_area("Kelengkapan Diterima", placeholder="Charger, Tas")
        submitted = st.form_submit_button("💾 Simpan Servis")

    if submitted:
        df = load_data()
        new_data = pd.DataFrame([{
            "Tanggal": datetime.date.today().strftime("%Y-%m-%d"),
            "Nama Pelanggan": nama,
            "No HP": no_hp,
            "Barang": barang,
            "Kerusakan": kerusakan,
            "Kelengkapan": kelengkapan,
            "Status": "Diterima"
        }])
        df = pd.concat([df, new_data], ignore_index=True)
        save_data(df)
        st.success(f"✅ Data servis untuk {nama} berhasil disimpan!")
        st.balloons()

    # === Daftar Servis Masuk ===
    st.divider()
    st.subheader("📋 Daftar Servis Masuk")
    df = load_data()

    if not df.empty:
        for i, row in df.iterrows():
            with st.expander(f"{row['Nama Pelanggan']} - {row['Barang']}"):
                st.write(f"📅 **Tanggal:** {row['Tanggal']}")
                st.write(f"📞 **No HP:** {row['No HP']}")
                st.write(f"💻 **Barang:** {row['Barang']}")
                st.write(f"🧩 **Kerusakan:** {row['Kerusakan']}")
                st.write(f"🎒 **Kelengkapan:** {row['Kelengkapan']}")
                st.write(f"🟡 **Status:** {row['Status']}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✅ Tandai Selesai #{i}", key=f"done_{i}"):
                        df.at[i, "Status"] = "Selesai"
                        save_data(df)
                        st.success(f"Servis untuk {row['Nama Pelanggan']} ditandai selesai.")
                with col2:
                    if st.button(f"💬 Kirim WhatsApp #{i}", key=f"wa_{i}"):
                        message = f"""Halo {row['Nama Pelanggan']}, 
Servis {row['Barang']} Anda telah **SELESAI** ✅
Detail: {row['Kerusakan']}
Silakan diambil di toko kami. Terima kasih 🙏"""
                        wa_link = f"https://wa.me/{row['No HP'].replace('+','')}/?text={requests.utils.quote(message)}"
                        st.markdown(f"[Klik untuk kirim pesan ke WhatsApp]({wa_link})")
    else:
        st.info("Belum ada data servis masuk.")
