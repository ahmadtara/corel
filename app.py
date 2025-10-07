# app.py
import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
from owslib.wfs import WebFeatureService
from shapely.geometry import shape
import tempfile
import zipfile
import io

st.set_page_config(page_title="Batas Kelurahan Pekanbaru", layout="wide")

st.title("🗺️ Batas Kelurahan Kota Pekanbaru — Sumber Data BIG")

st.info("Aplikasi ini mengambil batas administratif kelurahan di Kota Pekanbaru langsung dari layanan geospasial resmi BIG (Badan Informasi Geospasial).")

# URL layanan WFS dari BIG
WFS_URL = "https://geoservices.big.go.id/geoserver/wfs"

try:
    wfs = WebFeatureService(url=WFS_URL, version="1.1.0")

    layer_name = "wilayah:Admin_Desa_Indonesia"
    response = wfs.getfeature(
        typename=layer_name,
        outputFormat="application/json",
        filter="<Filter><PropertyIsLike wildCard='%' name='kabupaten'>%Pekanbaru%</PropertyIsLike></Filter>",
    )

    gdf = gpd.read_file(io.BytesIO(response.read()))
    gdf = gdf.to_crs(epsg=4326)

    # Tampilkan daftar kelurahan
    kelurahan_list = sorted(gdf['nama'].unique().tolist())
    st.write(f"✅ Ditemukan **{len(kelurahan_list)} kelurahan** di Kota Pekanbaru.")

    # Map interaktif
    m = folium.Map(location=[0.5, 101.45], zoom_start=12)
    for _, row in gdf.iterrows():
        folium.GeoJson(row['geometry'], name=row['nama'],
                       tooltip=row['nama']).add_to(m)
    folium.LayerControl().add_to(m)
    st_data = st_folium(m, width=800, height=600)

    # Tombol download KML
    if st.button("💾 Download sebagai KML"):
        with tempfile.TemporaryDirectory() as tmpdir:
            kml_path = f"{tmpdir}/batas_kelurahan_pekanbaru.kml"
            gdf.to_file(kml_path, driver="KML")
            with open(kml_path, "rb") as f:
                st.download_button(
                    label="⬇️ Klik untuk mengunduh KML",
                    data=f,
                    file_name="batas_kelurahan_pekanbaru.kml",
                    mime="application/vnd.google-earth.kml+xml"
                )

except Exception as e:
    st.error(f"Gagal memuat data dari BIG: {e}")
    st.warning("Silakan periksa koneksi internet atau coba lagi nanti.")
