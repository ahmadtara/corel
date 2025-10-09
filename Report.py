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

# ------------------- DATA SERVIS -------------------
def load_data():
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
            df = pd.DataFrame(rows)
            df.to_csv(DATA_FILE, index=False)
            return df
    except Exception as e:
        st.warning(f"Gagal ambil data dari Firebase: {e}")

    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=[
        "FirebaseID","No Nota","Tanggal Masuk","Estimasi Selesai","Nama Pelanggan","No HP",
        "Barang","Kerusakan","Kelengkapan","Status","Harga Jasa","Harga Modal"
    ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ------------------- DATA BARANG -------------------
def load_data_barang():
    try:
        r = requests.get(f"{FIREBASE_URL}/stok_barang.json")
        if r.status_code == 200 and r.text != "null":
            data = r.json()
            df = pd.DataFrame.from_dict(data, orient="index").reset_index(names="FirebaseID")
            for col in ["nama_barang","modal","harga_jual","qty"]:
                if col not in df.columns:
                    df[col] = ""
            return df
    except Exception as e:
        st.warning(f"Gagal ambil data stok_barang: {e}")
    return pd.DataFrame(columns=["FirebaseID","nama_barang","modal","harga_jual","qty"])

# ------------------- UPDATE FIREBASE -------------------
def update_firebase(firebase_id, data):
    try:
        r = requests.patch(f"{FIREBASE_URL}/servis/{firebase_id}.json", json=data)
        if r.status_code != 200:
            st.warning(f"Gagal update Firebase: {r.text}")
    except Exception as e:
        st.error(f"Error update Firebase: {e}")

# =========================================================
#                        HALAMAN REPORT
# =========================================================
def show():
    cfg = load_config()
    st.title("📊 Laporan Servis & Barang")

    # ------------------- LOAD DATA -------------------
    df = load_data()
    if df.empty:
        st.info("Belum ada data servis.")
        return

    # ------------------- KONVERSI TANGGAL -------------------
    df["Tanggal Masuk"] = pd.to_datetime(df["Tanggal Masuk"], format="%d/%m/%Y", errors="coerce").dt.date
    df = df.dropna(subset=["Tanggal Masuk"])

    # ------------------- PARSE HARGA -------------------
    def parse_rp_to_int(x):
        try:
            s = str(x).replace("Rp","").replace(".","").replace(",","").strip()
            return int(s) if s else 0
        except:
            return 0

    df["Harga Jasa Num"] = df["Harga Jasa"].apply(parse_rp_to_int)
    df["Harga Modal Num"] = df["Harga Modal"].apply(parse_rp_to_int)
    df["Keuntungan"] = df["Harga Jasa Num"] - df["Harga Modal Num"]

    # ------------------- FILTER PER HARI / BULAN -------------------
    st.sidebar.header("📅 Filter Servis")
    filter_mode = st.sidebar.radio("Pilih mode filter:", ["Per Hari", "Per Bulan"], index=0)

    if filter_mode == "Per Hari":
        tanggal_filter = st.sidebar.date_input("Pilih Tanggal:", value=datetime.date.today())
        df_filtered = df[df["Tanggal Masuk"] == tanggal_filter]
    else:
        bulan_unik = df["Tanggal Masuk"].apply(lambda x: x.replace(day=1)).dropna().unique()
        pilih_bulan = st.sidebar.selectbox(
            "Pilih Bulan:",
            options=["Semua Bulan"] + [str(b) for b in bulan_unik],
            index=0
        )
        if pilih_bulan != "Semua Bulan":
            pilih_bulan_date = pd.to_datetime(pilih_bulan).date()
            df_filtered = df[df["Tanggal Masuk"].apply(
                lambda x: x.year == pilih_bulan_date.year and x.month == pilih_bulan_date.month)]
        else:
            df_filtered = df.copy()

    # ------------------- REKAP KEUNTUNGAN -------------------
    total_servis = df_filtered["Keuntungan"].sum()

    # Data barang
    df_barang = load_data_barang()
    if not df_barang.empty:
        df_barang["modal"] = pd.to_numeric(df_barang["modal"], errors="coerce").fillna(0)
        df_barang["harga_jual"] = pd.to_numeric(df_barang["harga_jual"], errors="coerce").fillna(0)
        df_barang["qty"] = pd.to_numeric(df_barang["qty"], errors="coerce").fillna(0)
        df_barang["Potensi Laba"] = (df_barang["harga_jual"] - df_barang["modal"]) * df_barang["qty"]
        total_barang = df_barang["Potensi Laba"].sum()
    else:
        total_barang = 0

    # ------------------- TAMPILKAN TOTAL DI ATAS -------------------
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Keuntungan Servis", f"Rp {total_servis:,.0f}".replace(",", "."))
    col2.metric("📦 Potensi Laba Barang", f"Rp {total_barang:,.0f}".replace(",", "."))
    col3.metric("📊 Total Gabungan", f"Rp {(total_servis + total_barang):,.0f}".replace(",", "."))

    st.divider()

    # ------------------- TABEL SERVIS -------------------
    if df_filtered.empty:
        st.info("Tidak ada data servis untuk filter yang dipilih.")
        return

    st.dataframe(
        df_filtered[["No Nota","Tanggal Masuk","Nama Pelanggan","Barang","Status",
                     "Harga Modal","Harga Jasa","Keuntungan"]],
        use_container_width=True
    )

    # ------------------- LOOP WA -------------------
    st.divider()
    st.subheader("📱 Klik Pelanggan Untuk Kirim WA Otomatis")

    for i, row in df_filtered.iterrows():
        with st.expander(f"{row['Nama Pelanggan']} - {row['Barang']} ({row['Status']})"):

            harga_jasa_input = st.text_input(
                "Masukkan Harga Jasa (Rp):",
                value=str(row["Harga Jasa Num"]) if row["Harga Jasa Num"] else "",
                key=f"harga_{i}"
            )
            harga_modal_input = st.text_input(
                "Masukkan Harga Modal (Rp) - tidak dikirim ke WA",
                value=str(row["Harga Modal Num"]) if row["Harga Modal Num"] else "",
                key=f"modal_{i}"
            )

            if st.button("✅ Update & Kirim WA", key=f"btn_{i}"):
                try:
                    harga_modal_num = int(str(harga_modal_input).replace(".","").strip())
                except:
                    harga_modal_num = 0
                try:
                    harga_jasa_num = int(str(harga_jasa_input).replace(".","").strip())
                except:
                    harga_jasa_num = 0

                harga_jasa_str = f"Rp {harga_jasa_num:,}".replace(",", ".")
                harga_modal_str = f"Rp {harga_modal_num:,}".replace(",", ".")

                df.at[i,"Harga Jasa"] = harga_jasa_str
                df.at[i,"Harga Modal"] = harga_modal_str
                df.at[i,"Status"] = "Lunas"
                df.at[i,"Keuntungan"] = harga_jasa_num - harga_modal_num
                save_data(df)

                firebase_data = {
                    "harga_jasa": harga_jasa_str,
                    "harga_modal": harga_modal_str,
                    "status": "Lunas",
                    "keuntungan": harga_jasa_num - harga_modal_num
                }
                update_firebase(row["FirebaseID"], firebase_data)

                msg = f"""Assalamualaikum {row['Nama Pelanggan']},

Unit anda dengan nomor nota *{row['No Nota']}* sudah selesai dan siap untuk diambil.

Total Biaya Servis: *{harga_jasa_str}*

Terima Kasih 🙏
{cfg['nama_toko']}"""

                no_hp = str(row["No HP"]).replace("+","").replace(" ","").strip()
                if no_hp.startswith("0"):
                    no_hp = "62" + no_hp[1:]
                link = f"https://wa.me/{no_hp}?text={requests.utils.quote(msg)}"

                st.success(f"✅ Servis {row['Barang']} ditandai lunas & membuka WhatsApp...")
                st.markdown(f"[📲 Buka WhatsApp]({link})", unsafe_allow_html=True)

                js = f"""
                <script>
                    setTimeout(function(){{
                        window.open("{link}", "_blank");
                    }}, 800);
                </script>
                """
                st.markdown(js, unsafe_allow_html=True)
                st.stop()

    # ------------------- HAPUS MASSAL -------------------
    st.divider()
    st.subheader("🗑️ Hapus Beberapa Data Sekaligus")
    pilih = st.multiselect(
        "Pilih servis untuk dihapus:",
        df_filtered.index,
        format_func=lambda x: f"{df_filtered.loc[x, 'Nama Pelanggan']} - {df_filtered.loc[x, 'Barang']}"
    )

    if st.button("🚮 Hapus Terpilih"):
        if pilih:
            for idx in pilih:
                fid = df_filtered.loc[idx, "FirebaseID"]
                try:
                    requests.delete(f"{FIREBASE_URL}/servis/{fid}.json")
                except:
                    pass
            df = df.drop(pilih).reset_index(drop=True)
            save_data(df)
            st.success("Data terpilih berhasil dihapus.")
            st.rerun()
        else:
            st.warning("Belum ada data yang dipilih.")

    # ------------------- DOWNLOAD CSV -------------------
    st.divider()
    st.download_button(
        label="⬇️ Download CSV Laporan",
        data=df_filtered.to_csv(index=False).encode('utf-8'),
        file_name="laporan_servis.csv",
        mime="text/csv"
    )
