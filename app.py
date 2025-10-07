import streamlit as st
import requests
import json
import os
import zipfile
from io import BytesIO

st.set_page_config(page_title="ArcGIS ➜ GeoJSON Extractor", page_icon="🗺️", layout="centered")

st.title("🗺️ ArcGIS ➜ GeoJSON Extractor (Auto Deep Scan)")
st.markdown("""
Masukkan **ArcGIS Web App ID** (contoh: `51aa6e2a1b7d4cf1a551e1258c7f05c1`)  
Aplikasi ini akan:
1. Mendapatkan konfigurasi WebMap dari AppID  
2. Mendeteksi semua layer (`FeatureServer`, `MapServer`, bahkan yang tersembunyi)  
3. Mengunduh otomatis semua layer sebagai **GeoJSON**
""")

appid = st.text_input("Masukkan AppID", "51aa6e2a1b7d4cf1a551e1258c7f05c1")

def extract_urls(obj, found=None):
    """ Rekursif cari URL dari struktur dict/list JSON """
    if found is None:
        found = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "url" and isinstance(v, str) and ("FeatureServer" in v or "MapServer" in v):
                found.append(v)
            else:
                extract_urls(v, found)
    elif isinstance(obj, list):
        for i in obj:
            extract_urls(i, found)
    return found


if st.button("🚀 Ekstrak GeoJSON"):
    try:
        st.info("🔍 Mengambil metadata aplikasi...")

        # 1️⃣ Ambil metadata aplikasi
        app_url = f"https://www.arcgis.com/sharing/rest/content/items/{appid}/data?f=json"
        app_data = requests.get(app_url).json()

        webmap_id = None
        # Bisa jadi app menggunakan struktur berbeda
        if "values" in app_data and "webmap" in app_data["values"]:
            webmap_id = app_data["values"]["webmap"]
        elif "map" in app_data:
            webmap_id = app_data["map"].get("itemId")

        if not webmap_id:
            st.error("❌ Tidak bisa menemukan WebMap ID dari AppID ini.")
            st.json(app_data)
            st.stop()

        st.success(f"WebMap ID: {webmap_id}")

        # 2️⃣ Ambil definisi webmap
        webmap_url = f"https://www.arcgis.com/sharing/rest/content/items/{webmap_id}/data?f=json"
        webmap_data = requests.get(webmap_url).json()

        # 3️⃣ Cari URL layer secara mendalam
        st.info("🔎 Memindai seluruh struktur untuk menemukan layer...")
        layers = extract_urls(webmap_data)

        # 4️⃣ Jika kosong, coba fallback dari itemData (kadang pakai sub webmap)
        if not layers and "itemData" in webmap_data:
            layers = extract_urls(webmap_data["itemData"])

        if not layers:
            st.warning("❗ Tidak ditemukan layer dalam WebMap ini.")
            st.expander("Lihat isi WebMap mentah").json(webmap_data)
            st.stop()

        # Hapus duplikat
        layers = sorted(set(layers))
        st.success(f"✅ Ditemukan {len(layers)} layer:")
        for i, l in enumerate(layers, 1):
            st.write(f"{i}. {l}")

        # 5️⃣ Unduh tiap layer sebagai GeoJSON
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for i, layer_url in enumerate(layers, 1):
                query_url = f"{layer_url}/query?where=1%3D1&outFields=*&f=geojson"
                st.write(f"⬇️ Mengunduh layer {i}...")
                try:
                    geojson_data = requests.get(query_url, timeout=15).text
                    zipf.writestr(f"layer_{i}.geojson", geojson_data)
                except Exception as e:
                    st.error(f"Gagal unduh layer {i}: {e}")

        zip_buffer.seek(0)
        st.success("🎉 Semua layer berhasil diekstrak!")

        st.download_button(
            label="📦 Unduh Semua Layer (ZIP)",
            data=zip_buffer,
            file_name=f"arcgis_{appid}_layers.zip",
            mime="application/zip"
        )

    except Exception as e:
        st.error(f"⚠️ Terjadi kesalahan: {e}")
