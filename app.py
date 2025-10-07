import streamlit as st
import osmnx as ox
import geopandas as gpd
from shapely.geometry import Polygon
from fastkml import kml
import tempfile
import zipfile
import os

st.set_page_config(page_title="Batas Kelurahan Pekanbaru (OSM)", layout="wide")

# ====== Daftar Kelurahan ======
kelurahan_list = [
    "Simpang Tiga", "Tangkerang Labuai", "Pesisir", "Wonorejo", "Maharatu",
    "Perhentian Marpoyan", "Labuh Baru Timur", "Sukamaju", "Sukamulya",
    "Kota Baru", "Simpang Empat", "Sukaramai", "Sumahilang", "Tanah Datar",
    "Harjosari", "Jadirejo", "Kedung Sari", "Pulau Karomah", "Sialang Rampai",
    "Kampung Dalam", "Padang Bulan", "Sago", "Meranti Pandak", "Binawidya",
    "Simpang Baru", "Tobek Godang", "Mentangor"
]

st.title("🗺️ Batas Kelurahan Pekanbaru (Data OSM)")
st.write("Aplikasi ini mengambil batas administratif kelurahan langsung dari OpenStreetMap.")

# ====== Proses Download Data ======
def get_kelurahan_boundary(kel_name):
    try:
        gdf = ox.geocode_to_gdf(f"{kel_name}, Pekanbaru, Riau, Indonesia")
        return gdf
    except Exception as e:
        st.warning(f"Gagal ambil data: {kel_name} ({e})")
        return None

if st.button("🔍 Ambil Batas Kelurahan dari OSM"):
    all_gdf = []
    for kel in kelurahan_list:
        gdf = get_kelurahan_boundary(kel)
        if gdf is not None:
            gdf["nama"] = kel
            all_gdf.append(gdf)

    if len(all_gdf) > 0:
        merged = gpd.GeoDataFrame(pd.concat(all_gdf, ignore_index=True), crs=all_gdf[0].crs)

        # Simpan KML
        temp_dir = tempfile.mkdtemp()
        kml_path = os.path.join(temp_dir, "kelurahan_pekanbaru.kml")
        merged.to_file(kml_path, driver="KML")

        # Zip ke KMZ
        kmz_path = os.path.join(temp_dir, "kelurahan_pekanbaru.kmz")
        with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(kml_path, arcname="kelurahan_pekanbaru.kml")

        st.success("✅ Berhasil! File siap diunduh.")
        with open(kml_path, "rb") as f:
            st.download_button("⬇️ Download KML", f, file_name="kelurahan_pekanbaru.kml")
        with open(kmz_path, "rb") as f:
            st.download_button("⬇️ Download KMZ", f, file_name="kelurahan_pekanbaru.kmz")
    else:
        st.error("❌ Tidak ada data ditemukan dari OSM.")
