# Report.py
import streamlit as st
import pandas as pd
import requests
import datetime
import json

# ------------------ KONFIGURASI ------------------
FIREBASE_URL = "https://toko-4960c-default-rtdb.asia-southeast1.firebasedatabase.app/service_data.json"
CONFIG_FILE = "config.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "nama_toko": "Capslock Komputer",
            "alamat": "Jl. Buluh Cina, Panam",
            "telepon": "0851-7217-4759"
        }

# ------------------ FUNGSI FIREBASE ------------------
def get_data():
    try:
        r = requests.get(FIREBASE_URL)
        if r.status_code == 200 and r.text != "null":
            data = r.json()
            df = pd.DataFrame(data).T.reset_index().rename(columns={"index": "id"})
            return df
        return pd.DataFrame(columns=[
            "id", "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan",
            "No HP", "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Modal", "Harga Jasa"
        ])
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame()

def save_data_to_firebase(record_id, data):
    url = f"https://toko-4960c-default-rtdb.asia-southeast1.firebasedatabase.app/service_data/{record_id}.json"
    requests.patch(url, json=data)

def delete_data_from_firebase(record_id):
    url = f"https://toko-4960c-default-rtdb.asia-southeast1.firebasedatabase.app/service_data/{record_id}.json"
    requests.delete(url)

# ------------------ HALAMAN REPORT ------------------
def show():
    cfg = load_config()
    st.title("📊 Laporan Servis")

    df = get_data()
    if df.empty:
        st.info("Belum ada data servis.")
        return

    # Konversi tanggal
    df["Tanggal Masuk"] = pd.to_datetime(df["Tanggal Masuk"], errors="coerce")

    # ---------------- FILTER BULAN ----------------
    st.sidebar.header("📅 Filter Data Bulanan")
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
        st.sidebar.info("Belum ada bulan untuk difilter.")

    # ---------------- REKAP LABA BULANAN ----------------
    try:
        df["Harga Jasa (num)"] = df["Harga Jasa"].replace("[^0-9]", "", regex=True).astype(float)
        df["Harga Modal (num)"] = df["Harga Modal"].replace("[^0-9]", "", regex=True).astype(float)
        df["Laba"] = df["Harga Jasa (num)"] - df["Harga Modal (num)"]
        total_modal = df["Harga Modal (num)"].sum()
        total_jasa = df["Harga Jasa (num)"].sum()
        total_laba = df["Laba"].sum()

        st.metric("💰 Total Modal", f"Rp {total_modal:,.0f}".replace(",", "."))
        st.metric("💵 Total Pendapatan", f"Rp {total_jasa:,.0f}".replace(",", "."))
        st.metric("📈 Total Laba", f"Rp {total_laba:,.0f}".replace(",", "."))
        st.divider()
    except:
        pass

    # ---------------- TAMPIL DATA ----------------
    st.dataframe(df[[
        "No Nota", "Tanggal Masuk", "Nama Pelanggan", "Barang",
        "Harga Modal", "Harga Jasa", "Status"
    ]], use_container_width=True)

    st.subheader("📱 Kirim WA & Update Status")

    for i, row in df.iterrows():
        with st.expander(f"{row['Nama Pelanggan']} - {row['Barang']} ({row['Status']})"):
            harga_modal_input = st.text_input(
                "Harga Modal (contoh: 80000)",
                value=str(row.get("Harga Modal", "")).replace("Rp ", "").replace(".", ""),
                key=f"modal_{i}"
            )
            harga_jasa_input = st.text_input(
                "Harga Jasa (contoh: 150000)",
                value=str(row.get("Harga Jasa", "")).replace("Rp ", "").replace(".", ""),
                key=f"jasa_{i}"
            )

            if st.button("💾 Simpan & Kirim WA", key=f"kirim_{i}"):
                try:
                    # Format harga
                    harga_modal_num = int(harga_modal_input or 0)
                    harga_jasa_num = int(harga_jasa_input or 0)
                    harga_modal_fmt = f"Rp {harga_modal_num:,}".replace(",", ".")
                    harga_jasa_fmt = f"Rp {harga_jasa_num:,}".replace(",", ".")

                    # Update ke Firebase
                    update_data = {
                        "Harga Modal": harga_modal_fmt,
                        "Harga Jasa": harga_jasa_fmt,
                        "Status": "Lunas"
                    }
                    save_data_to_firebase(row["id"], update_data)

                    # Pesan WA
                    msg = f"""Assalamualaikum {row['Nama Pelanggan']},

Unit anda dengan nomor nota *{row['No Nota']}* sudah selesai dan siap untuk diambil.

Total Biaya Servis: *{harga_jasa_fmt}*

Terima Kasih 🙏
{cfg['nama_toko']}"""

                    # Format nomor WA
                    no_hp = str(row["No HP"]).replace("+", "").replace(" ", "").strip()
                    if no_hp.startswith("0"):
                        no_hp = "62" + no_hp[1:]
                    link = f"https://wa.me/{no_hp}?text={requests.utils.quote(msg)}"

                    # Buka WA otomatis
                    js = f"""
                    <script>
                        setTimeout(function(){{
                            window.open("{link}", "_blank");
                        }}, 800);
                    </script>
                    """
                    st.markdown(js, unsafe_allow_html=True)
                    st.success(f"✅ Data {row['Nama Pelanggan']} disimpan & WhatsApp dibuka.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal memperbarui data: {e}")

    # ---------------- HAPUS MASSAL ----------------
    st.divider()
    st.subheader("🗑️ Hapus Data Servis")

    pilih = st.multiselect(
        "Pilih servis untuk dihapus:",
        df["id"],
        format_func=lambda x: f"{df.loc[df['id']==x, 'Nama Pelanggan'].values[0]} - {df.loc[df['id']==x, 'Barang'].values[0]}"
    )

    if st.button("🚮 Hapus Terpilih"):
        if pilih:
            for pid in pilih:
                delete_data_from_firebase(pid)
            st.success("Data berhasil dihapus dari Firebase.")
            st.rerun()
        else:
            st.warning("Belum ada data yang dipilih untuk dihapus.")
