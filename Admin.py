import streamlit as st
import pandas as pd
import requests
import json
import os

# ---------------------- KONFIG ----------------------
FIREBASE_URL = "https://toko-4960c-default-rtdb.asia-southeast1.firebasedatabase.app"


# ---------------------- SIMPAN DATA ----------------------
def save_barang_to_firebase(data):
    try:
        r = requests.post(f"{FIREBASE_URL}/stok_barang.json", json=data)
        return r.status_code == 200
    except Exception as e:
        st.error(f"Gagal koneksi ke Firebase: {e}")
        return False


# ---------------------- MUAT DATA ----------------------
def load_barang():
    try:
        r = requests.get(f"{FIREBASE_URL}/stok_barang.json")
        if r.status_code == 200 and r.text != "null":
            data = r.json()
            df = pd.DataFrame.from_dict(data, orient="index")
            df.reset_index(drop=True, inplace=True)
            return df
    except Exception as e:
        st.warning(f"Gagal mengambil data: {e}")
    return pd.DataFrame(columns=["nama_barang", "modal", "harga_jual", "qty"])


# ---------------------- PAGE ----------------------
def show():
    st.title("📦 Manajemen Barang (Admin)")

    with st.form("barang_form"):
        nama = st.text_input("Nama Barang", placeholder="Contoh: Mouse Logitech")
        modal = st.number_input("Modal (Rp)", min_value=0.0, format="%.0f")
        harga = st.number_input("Harga Jual (Rp)", min_value=0.0, format="%.0f")
        qty = st.number_input("Stok Barang", min_value=0, format="%d")
        submitted = st.form_submit_button("💾 Simpan Barang")

    if submitted:
        if not nama:
            st.warning("Nama barang wajib diisi!")
            return

        data = {
            "nama_barang": nama,
            "modal": modal,
            "harga_jual": harga,
            "qty": qty
        }

        if save_barang_to_firebase(data):
            st.success(f"✅ Barang *{nama}* berhasil disimpan ke Firebase!")
        else:
            st.error("❌ Gagal menyimpan ke Firebase")

    # ---------------------- TABEL DATA ----------------------
    st.divider()
    st.subheader("📋 Daftar Barang di Database")

    df = load_barang()
    if not df.empty:
        # Tambahkan kolom ke format rupiah agar enak dibaca
        df["modal"] = df["modal"].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
        df["harga_jual"] = df["harga_jual"].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Belum ada data barang di Firebase.")
