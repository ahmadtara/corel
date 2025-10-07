import streamlit as st
import geopandas as gpd
import requests
import io
import simplekml
import tempfile
import zipfile
import os
import pandas as pd

st.set_page_config(page_title="🗺️ Batas Kelurahan Pekanbaru (BIG + Backup)", layout="wide")
st.title("🗺️ Batas Kelurahan Pekanbaru — BIG + Backup Mirror")

st.write("""
Aplikasi ini mengambil batas administratif **kelurahan di Kota Pekanbaru**
dari layanan resmi **Badan Informasi Geospasial (BIG)**.
Jika server BIG tidak dapat diakses, aplikasi otomatis memakai **backup mirror dari GitHub (Alf-Anas / Indonesia GeoJSON)**.
""")

# URL utama WFS BIG
BIG_WFS_URL = "https://geoservices.big.go.id/geoserver/wfs"

# URL backup dari GitHub
BACKUP_URL = "https://github.com/alf-anas/indonesia-geojson/raw/main/geojson/admin/kelurahan/pekanbaru_kelurahan.geojson"


@st.cache_data
def load_from_big():
    """Coba ambil data dari WFS BIG."""
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typename": "BATASWILAYAH:BATAS_DESA_AR_50K",  # layer kelurahan
        "outputFormat": "application/json",
    }
    r = requests.get(BIG_WFS_URL, params=params, timeout=60)
    r.raise_for_status()
    gdf = gpd.read_file(io.BytesIO(r.content))
    # Filter hanya Pekanbaru
    gdf = gdf[gdf["WADMKK"].str.contains("PEKANBARU", case=False, na=False)]
    return gdf.to_crs(epsg=4326)


@st.cache_data
def load_from_backup():
    """Ambil data dari GitHub mirror jika BIG gagal."""
    r = requests.get(BACKUP_URL, timeout=60)
    r.raise_for_status()
    gdf = gpd.read_file(io.BytesIO(r.content))
    return gdf.to_crs(epsg=4326)


st.subheader("📦 Memuat Data Batas Kelurahan...")

try:
    gdf = load_from_big()
    st.success(f"Data berhasil dimuat dari sumber BIG ({len(gdf)} kelurahan).")
    source = "BIG"
except Exception as e:
    st.warning(f"⚠️ Gagal memuat data dari BIG: {e}")
    st.info("Mengambil data dari backup GitHub (mirror)...")
    try:
        gdf = load_from_backup()
        st.success(f"Data berhasil dimuat dari backup GitHub ({len(gdf)} kelurahan).")
        source = "GitHub Backup"
    except Exception as e2:
        st.error(f"Gagal memuat data dari backup juga: {e2}")
        st.stop()

# Tampilkan tabel dan peta sederhana
st.write(f"### ✅ Sumber data aktif: {source}")
st.dataframe(gdf[["WADMPR", "WADMKK", "NAMOBJ"]].rename(columns={
    "WADMPR": "Provinsi",
    "WADMKK": "Kota/Kabupaten",
    "NAMOBJ": "Kelurahan"
}))

# Preview peta
st.map(gdf, zoom=11)

# Export ke KML
if st.button("⬇️ Export ke KML"):
    kml = simplekml.Kml()
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom.geom_type == "Polygon":
            coords = [(x, y) for x, y in geom.exterior.coords]
            p = kml.newpolygon(name=row["NAMOBJ"], outerboundaryis=coords)
            p.style.polystyle.color = "7dff0000"
            p.style.linestyle.width = 2
        elif geom.geom_type == "MultiPolygon":
            for poly in geom.geoms:
                coords = [(x, y) for x, y in poly.exterior.coords]
                p = kml.newpolygon(name=row["NAMOBJ"], outerboundaryis=coords)
                p.style.polystyle.color = "7dff0000"
                p.style.linestyle.width = 2

    temp_dir = tempfile.mkdtemp()
    kml_path = os.path.join(temp_dir, "batas_kelurahan_pekanbaru.kml")
    kml.save(kml_path)

    with open(kml_path, "rb") as f:
        st.download_button("📥 Download KML", f, file_name="batas_kelurahan_pekanbaru.kml")
