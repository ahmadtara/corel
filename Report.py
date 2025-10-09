import streamlit as st
import pandas as pd
import datetime
import requests
import json
import os

DATA_FILE = "service_data.csv"
CONFIG_FILE = "config.json"
FIREBASE_URL = "https://toko-4960c-default-rtdb.asia-southeast1.firebasedatabase.app/"

# ------------------- CONFIG -------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Buluh Cina, Panam",
        "telepon": "0851-7217-4759"
    }

# ------------------- LOAD DATA -------------------
def load_data_servis():
    try:
        r = requests.get(f"{FIREBASE_URL}/servis.json")
        if r.status_code == 200 and r.json():
            data = r.json()
            rows = []
            for key, val in data.items():
                row = {
                    "FirebaseID": key,
                    "No Nota": val.get("no_nota",""),
                    "Tanggal Masuk": val.get("tanggal_masuk",""),
                    "Estimasi Selesai": val.get("estimasi_selesai",""),
                    "Nama Pelanggan": val.get("nama_pelanggan",""),
                    "No HP": val.get("no_hp",""),
                    "Barang": val.get("barang",""),
                    "Kerusakan": val.get("kerusakan",""),
                    "Kelengkapan": val.get("kelengkapan",""),
                    "Status": val.get("status",""),
                    "Harga Jasa": val.get("harga_jasa",""),
                    "Harga Modal": val.get("harga_modal","0")
                }
                rows.append(row)
            return pd.DataFrame(rows)
    except Exception as e:
        st.warning(f"Gagal ambil data dari Firebase: {e}")
    return pd.DataFrame()

def load_data_transaksi():
    try:
        r = requests.get(f"{FIREBASE_URL}/transaksi.json")
        if r.status_code == 200 and r.text != "null":
            data = r.json()
            df = pd.DataFrame.from_dict(data, orient="index").reset_index(names="FirebaseID")
            for col in ["tanggal","nama_barang","modal","harga_jual","qty","untung"]:
                if col not in df.columns:
                    df[col] = 0
            return df
    except Exception as e:
        st.warning(f"Gagal ambil data transaksi: {e}")
    return pd.DataFrame()

# ------------------- HALAMAN REPORT -------------------
def show():
    cfg = load_config()
    st.title("📊 Laporan Servis & Barang")

    df_servis = load_data_servis()
    df_transaksi = load_data_transaksi()

    if df_servis.empty and df_transaksi.empty:
        st.info("Belum ada data di Firebase.")
        return

    # ------------------- PROSES SERVIS -------------------
    if not df_servis.empty:
        df_servis["Tanggal Masuk"] = pd.to_datetime(df_servis["Tanggal Masuk"], format="%d/%m/%Y", errors="coerce").dt.date
        def parse_rp(x):
            try:
                return int(str(x).replace("Rp","").replace(".","").replace(",","").strip() or 0)
            except:
                return 0
        df_servis["Harga Jasa Num"] = df_servis["Harga Jasa"].apply(parse_rp)
        df_servis["Harga Modal Num"] = df_servis["Harga Modal"].apply(parse_rp)
        df_servis["Keuntungan"] = df_servis["Harga Jasa Num"] - df_servis["Harga Modal Num"]
        total_servis = df_servis["Keuntungan"].sum()
    else:
        total_servis = 0

    # ------------------- PROSES TRANSAKSI -------------------
    if not df_transaksi.empty:
        df_transaksi["tanggal"] = pd.to_datetime(df_transaksi["tanggal"], errors="coerce").dt.date
        df_transaksi["untung"] = pd.to_numeric(df_transaksi["untung"], errors="coerce").fillna(0)
        total_barang = df_transaksi["untung"].sum()
    else:
        total_barang = 0

    # ------------------- TAMPIL TOTAL -------------------
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Keuntungan Servis", f"Rp {total_servis:,.0f}".replace(",", "."))
    col2.metric("📦 Total Laba Barang", f"Rp {total_barang:,.0f}".replace(",", "."))
    col3.metric("📊 Total Gabungan", f"Rp {(total_servis + total_barang):,.0f}".replace(",", "."))

    st.divider()

    # ------------------- TAMPILKAN DATA -------------------
    if not df_servis.empty:
        st.subheader("🛠️ Data Servis")
        st.dataframe(df_servis[["No Nota","Tanggal Masuk","Nama Pelanggan","Barang","Status","Harga Jasa","Harga Modal","Keuntungan"]], use_container_width=True)

    st.divider()
    if not df_transaksi.empty:
        st.subheader("📦 Data Transaksi Barang")
        st.dataframe(df_transaksi[["tanggal","nama_barang","qty","modal","harga_jual","untung"]], use_container_width=True)
    else:
        st.info("Belum ada transaksi barang.")

    # ------------------- DOWNLOAD CSV -------------------
    st.divider()
    if not df_servis.empty or not df_transaksi.empty:
        gabung = pd.concat([
            df_servis[["Tanggal Masuk","Nama Pelanggan","Barang","Keuntungan"]].rename(columns={"Tanggal Masuk":"Tanggal"}),
            df_transaksi[["tanggal","nama_barang","untung"]].rename(columns={"tanggal":"Tanggal","nama_barang":"Barang","untung":"Keuntungan"})
        ], ignore_index=True)
        csv = gabung.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Laporan Gabungan (CSV)", data=csv, file_name="laporan_gabungan.csv", mime="text/csv")
