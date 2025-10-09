import streamlit as st
import pandas as pd
import requests
import json
import os

FIREBASE_URL = "https://toko-4960c-default-rtdb.asia-southeast1.firebasedatabase.app"

def save_barang_to_firebase(data):
    r = requests.post(f"{FIREBASE_URL}/stok_barang.json", json=data)
    return r.status_code == 200

def load_barang():
    r = requests.get(f"{FIREBASE_URL}/stok_barang.json")
    if r.status_code == 200 and r.text != "null":
        data = r.json()
        df = pd.DataFrame.from_dict(data, orient="index")
        return df
    return pd.DataFrame(columns=["nama_barang", "modal", "harga_jual", "qty"])

def show():
    st.title("📦 Manajemen Barang (Admin)")

    with st.form("barang_form"):
        nama = st.text_input("Nama Barang", placeholder="Contoh: Mouse Logitech")
        modal = st.number_input("Modal", min_value=0)
        harga = st.number_input("Harga Jual", min_value=0)
        qty = st.number_input("Stok Barang", min_value=0)
        submitted = st.form_submit_button("💾 Simpan Barang")

    if submitted:
        data = {
            "nama_barang": nama,
            "modal": modal,
            "harga_jual": harga,
            "qty": qty
        }
        if save_barang_to_firebase(data):
            st.success("Barang berhasil disimpan ke Firebase!")
        else:
            st.error("Gagal menyimpan ke Firebase")

    st.divider()
    st.subheader("📋 Daftar Barang")
    df = load_barang()
    st.dataframe(df)
