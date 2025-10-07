import streamlit as st
import requests
import json
import os
import zipfile
from io import BytesIO

st.set_page_config(page_title="ArcGIS ➜ GeoJSON Extractor", page_icon="🗺️", layout="centered")

st.title("🗺️ ArcGIS ➜ GeoJSON Extractor")
st.markdown("""
Masukkan **ArcGIS Web App ID** (contoh: `51aa6e2a1b7d4cf1a551e1258c7f05c1`)  
Aplikasi ini akan:
1. Mendapatkan konfigurasi webmap dari AppID  
2. Mengambil semua layer (`FeatureServer/MapServer`)  
3. Mengunduhnya otomatis sebagai **GeoJSON**
""")

appid = st.text_input("Masukkan AppID", "51aa6e2a1b7d4cf1a551e1258c7f05c1")

if st.button("🚀 Ekstrak GeoJSON"):
    try:
        st.info("Mengambil metadata aplikasi...")

        # 1️⃣ Ambil metadata aplikasi
        app_url = f"https://www.arcgis.com/sharing/rest/content/items/{appid}/data?f=json"
        app_data = requests.get(app_url).json()

        webmap_id = app_data.get("values", {}).get("webmap")
        if not webmap_id:
            st.error("❌ Gagal mendapatkan WebMap ID dari AppID.")
            st.stop()

        st.success(f"WebMap ID: {webmap_id}")

        # 2️⃣ Ambil definisi webmap
        webmap_url = f"https://www.arcgis.com/sharing/rest/content/items/{webmap_id}/data?f=json"
        webmap_data = requests.get(webmap_url).json()

        # 3️⃣ Ekstrak semua layer
        layers = [lyr["url"] for lyr in webmap_data.get("operationalLayers", []) if "url" in lyr]

        if not layers:
            st.warning("Tidak ditemukan layer dalam WebMap ini.")
            st.stop()

        st.write("### 🌍 Ditemukan Layer:")
        for i, l in enumerate(layers, 1):
            st.write(f"{i}. {l}")

        # 4️⃣ Unduh dan simpan tiap layer
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for i, layer_url in enumerate(layers, 1):
                query_url = f"{layer_url}/query?where=1%3D1&outFields=*&f=geojson"
                st.write(f"⬇️ Mengunduh Layer {i}...")
                geojson_data = requests.get(query_url).text
                zipf.writestr(f"layer_{i}.geojson", geojson_data)

        zip_buffer.seek(0)
        st.success("✅ Semua layer berhasil diunduh!")

        st.download_button(
            label="📦 Unduh Semua Layer (ZIP)",
            data=zip_buffer,
            file_name=f"arcgis_{appid}_layers.zip",
            mime="application/zip"
        )

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
