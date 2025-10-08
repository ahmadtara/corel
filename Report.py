import streamlit as st
import pandas as pd
import datetime
import os
import urllib.parse
import json

DATA_FILE = "service_data.csv"
CONFIG_FILE = "config.json"

# === Helper Functions ===
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=[
        "No Nota", "Tanggal Masuk", "Estimasi Selesai",
        "Nama Pelanggan", "No HP", "Barang", "Kerusakan",
        "Kelengkapan", "Status", "Harga Jasa"
    ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Sudirman No. 123, Pekanbaru",
        "footer_nota": "Terima kasih sudah servis di Capslock Komputer 🙏",
        "template_wa": "Assalamualaikum {nama}, unit anda dengan nomor Nota {nota} sudah selesai dan siap untuk diambil.\n\nTerima kasih,\n{toko}"
    }

# === MAIN APP ===
def show():
    st.title("📊 Laporan Servis")

    df = load_data()
    cfg = load_config()

    if df.empty:
        st.info("Belum ada data servis.")
        return

    # === Tampilkan tabel utama ===
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("✏️ Update Harga & Kirim Pesan WhatsApp")

    for i, row in df.iterrows():
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            st.markdown(f"**{row['Nama Pelanggan']}** — {row['Barang']}")
            st.caption(f"Status: {row['Status']}")
        with col2:
            # Format harga tampilan
            harga_display = ""
            if pd.notna(row["Harga Jasa"]) and str(row["Harga Jasa"]).strip() != "":
                try:
                    harga_display = f"Rp {int(float(row['Harga Jasa'])):,.0f}".replace(",", ".")
                except:
                    harga_display = str(row["Harga Jasa"])

            harga_input = st.text_input(
                "💰 Harga Jasa",
                value=harga_display,
                key=f"harga_{i}"
            )

            # Bersihkan format untuk disimpan
            harga_baru = (
                harga_input.replace("Rp", "")
                .replace(".", "")
                .replace(",", "")
                .strip()
            )
        with col3:
            nohp = str(row["No HP"]).replace("+", "").replace(" ", "").strip()
            nota = row["No Nota"]
            nama = row["Nama Pelanggan"]

            if st.button("✅ Selesai & Kirim WA", key=f"selesai_{i}"):
                df.at[i, "Harga Jasa"] = harga_baru
                df.at[i, "Status"] = "Selesai"
                save_data(df)

                # Format pesan WA
                pesan = cfg["template_wa"].format(
                    nama=nama,
                    nota=nota,
                    toko=cfg["nama_toko"]
                )
                encoded_pesan = urllib.parse.quote(pesan)
                wa_link = f"https://wa.me/{nohp}?text={encoded_pesan}"

                st.success(f"Pesan terkirim ke {nama}")
                st.markdown(f"[💬 Buka WhatsApp]({wa_link})", unsafe_allow_html=True)
                st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Hapus Data Selesai")

    selesai_df = df[df["Status"] == "Selesai"]
    if selesai_df.empty:
        st.info("Tidak ada data selesai untuk dihapus.")
    else:
        pilih = st.multiselect(
            "Pilih data selesai yang ingin dihapus:",
            selesai_df.index,
            format_func=lambda x: f"{df.loc[x, 'Nama Pelanggan']} - {df.loc[x, 'Barang']}"
        )

        if st.button("🗑️ Hapus Terpilih"):
            if pilih:
                df = df.drop(pilih).reset_index(drop=True)
                save_data(df)
                st.success("Data berhasil dihapus.")
                st.rerun()
            else:
                st.warning("Belum ada data yang dipilih.")
