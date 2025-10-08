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
        df = pd.read_csv(DATA_FILE)
        # Pastikan kolom Harga Modal ada
        if "Harga Modal" not in df.columns:
            df["Harga Modal"] = ""
        return df
    return pd.DataFrame(columns=[
        "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan", "No HP",
        "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Jasa", "Harga Modal"
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

    # Konversi tanggal masuk
    try:
        df["Tanggal Masuk"] = pd.to_datetime(df["Tanggal Masuk"], errors="coerce")
    except:
        pass

    # ------------------- FILTER BULAN -------------------
    st.sidebar.header("📅 Filter Laporan per Bulan")
    bulan_unik = sorted(df["Tanggal Masuk"].dropna().dt.to_period("M").unique())

    if len(bulan_unik) > 0:
        pilih_bulan = st.sidebar.selectbox(
            "Pilih Bulan:",
            options=["Semua Bulan"] + [str(b) for b in bulan_unik],
            index=0
        )
        if pilih_bulan != "Semua Bulan":
            df = df[df["Tanggal Masuk"].dt.to_period("M") == pd.Period(pilih_bulan)]
    else:
        st.sidebar.info("Belum ada data untuk difilter.")

    # ------------------- HITUNG REKAP -------------------
    def parse_rupiah(s):
        try:
            return int(str(s).replace("Rp", "").replace(".", "").strip())
        except:
            return 0

    total_jasa = df["Harga Jasa"].apply(parse_rupiah).sum()
    total_modal = df["Harga Modal"].apply(parse_rupiah).sum()
    total_untung = total_jasa - total_modal

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Modal", f"Rp {total_modal:,}".replace(",", "."))
    col2.metric("💵 Total Jasa", f"Rp {total_jasa:,}".replace(",", "."))
    col3.metric("📈 Total Untung", f"Rp {total_untung:,}".replace(",", "."))

    # ------------------- TAMPIL DATA -------------------
    st.dataframe(df, use_container_width=True)
    st.divider()
    st.subheader("📱 Klik Pelanggan Untuk Kirim WA Otomatis")

    for i, row in df.iterrows():
        with st.expander(f"{row['Nama Pelanggan']} - {row['Barang']} ({row['Status']})"):
            # Input harga modal
            modal_input = st.text_input(
                "Harga Modal (tidak dikirim ke WA)",
                value=str(row["Harga Modal"]).replace("Rp ", "").replace(".", "") if pd.notna(row["Harga Modal"]) else "",
                key=f"modal_{i}"
            )

            # Input harga jasa
            harga_input = st.text_input(
                "Harga Jasa (akan dikirim ke WA)",
                value=str(row["Harga Jasa"]).replace("Rp ", "").replace(".", "") if pd.notna(row["Harga Jasa"]) else "",
                key=f"harga_{i}"
            )

            if harga_input.strip():
                # Format harga jasa
                try:
                    harga_num = int(harga_input.replace("Rp", "").replace(".", "").replace(",", "").strip())
                    harga_baru = f"Rp {harga_num:,}".replace(",", ".")
                except:
                    harga_baru = harga_input

                # Format harga modal
                try:
                    if modal_input.strip():
                        modal_num = int(modal_input.replace("Rp", "").replace(".", "").replace(",", "").strip())
                        modal_baru = f"Rp {modal_num:,}".replace(",", ".")
                    else:
                        modal_baru = ""
                except:
                    modal_baru = modal_input

                # Update CSV
                df.at[i, "Status"] = "Lunas"
                df.at[i, "Harga Jasa"] = harga_baru
                df.at[i, "Harga Modal"] = modal_baru
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

            st.info("Harga modal hanya untuk laporan internal — tidak dikirim ke WA pelanggan.")

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
