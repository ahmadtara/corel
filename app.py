# app.py
import streamlit as st
import requests
import io
import zipfile
import tempfile
import os
import time
import json
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape
import simplekml

st.set_page_config(page_title="Batas Kelurahan Pekanbaru (BIG + OSM)", layout="wide")
st.title("🗺️ Batas Kelurahan Pekanbaru — (BIG → fallback OSM)")
st.write("Aplikasi akan mencoba ambil polygon tiap kelurahan dari BIG (utama) lalu OSM (fallback).")

# === Daftar kelurahan final ===
kelurahan_list = [
    "Simpang Tiga","Tangkerang Labuai","Pesisir","Wonorejo","Maharatu",
    "Perhentian Marpoyan","Labuh Baru Timur","Sukamaju","Sukamulya","Kota Baru",
    "Simpang Empat","Sukaramai","Sumahilang","Tanah Datar","Harjosari",
    "Jadirejo","Kedungsari","Pulau Karomah","Sialangrampai","Kampung Dalam",
    "Padang Bulan","Sago","Meranti Pandak","Binawidya","Simpang Baru",
    "Tobek Godang","Mentangor"
]

BASE_BIG = "https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/BATAS_WILAYAH/MapServer/11/query"

# === Fungsi Query BIG ===
def query_big_kelurahan(name):
    escaped_name = name.replace("'", "''")
    queries = [
        f"wakbk1 LIKE '%PEKANBARU%' AND wakld1 = '{escaped_name}'",
        f"wakbk1 LIKE '%PEKANBARU%' AND upper(wakld1) LIKE upper('%{escaped_name}%')",
        f"upper(nama) LIKE upper('%{escaped_name}%')",
    ]
    for where in queries:
        params = {
            "where": where,
            "outFields": "*",
            "f": "geojson",
            "outSR": "4326",
            "returnGeometry": "true"
        }
        try:
            r = requests.get(BASE_BIG, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            if "features" in data and data["features"]:
                return data
        except Exception:
            pass
        time.sleep(0.1)
    return None

# === Fungsi Query OSM ===
def query_osm_kelurahan(name):
    try:
        q_area = '[out:json][timeout:25];relation["name"="Pekanbaru"]["admin_level"~"6|7|8"];out ids;'
        r = requests.get("https://overpass-api.de/api/interpreter", params={"data": q_area}, timeout=30)
        r.raise_for_status()
        res = r.json()
        if not res.get("elements"):
            return None
        rel_id = res["elements"][0]["id"]
        area_id = 3600000000 + rel_id

        q = f"""
        [out:json][timeout:60];
        area({area_id})->.a;
        (
          relation["admin_level"~"8|9"]["name"~"^{name}$",i](area.a);
          way["admin_level"~"8|9"]["name"~"^{name}$",i](area.a);
        );
        out geom;
        """
        r2 = requests.get("https://overpass-api.de/api/interpreter", params={"data": q}, timeout=60)
        r2.raise_for_status()
        data = r2.json()

        if not data.get("elements"):
            return None

        geoms, props = [], []
        for el in data["elements"]:
            if "geometry" in el:
                coords = [(pt["lon"], pt["lat"]) for pt in el["geometry"]]
                if len(coords) > 3:
                    poly = shape({"type": "Polygon", "coordinates": [coords]})
                    geoms.append(poly)
                    props.append(el.get("tags", {}))
        if geoms:
            gdf = gpd.GeoDataFrame(props, geometry=geoms, crs="EPSG:4326")
            return json.loads(gdf.to_json())
    except Exception:
        return None
    return None

# === Main Action ===
if st.button("🔍 Generate semua kelurahan (BIG → OSM)"):
    gdfs = []
    status = []
    progress = st.progress(0)

    for i, kel in enumerate(kelurahan_list):
        st.write(f"Memproses: **{kel}**")

        # Coba BIG dulu
        data = query_big_kelurahan(kel)
        if data:
            try:
                gdf = gpd.GeoDataFrame.from_features(data["features"], crs="EPSG:4326")
                gdf["nama_src"] = "BIG"
                gdf["nama_kel"] = kel
                gdfs.append(gdf)
                status.append((kel, "BIG"))
                st.success(f" - Ditemukan di BIG ({len(gdf)} feature).")
                progress.progress((i+1)/len(kelurahan_list))
                continue
            except Exception as e:
                st.warning(f" - Gagal parsing BIG: {e}")

        # Fallback ke OSM
        st.info(f" - Mencoba OSM fallback untuk {kel} ...")
        osm_json = query_osm_kelurahan(kel)
        if osm_json:
            try:
                gdf = gpd.GeoDataFrame.from_features(osm_json["features"], crs="EPSG:4326")
                gdf["nama_src"] = "OSM"
                gdf["nama_kel"] = kel
                gdfs.append(gdf)
                status.append((kel, "OSM"))
                st.success(f" - Ditemukan di OSM ({len(gdf)} feature).")
                progress.progress((i+1)/len(kelurahan_list))
                continue
            except Exception as e:
                st.warning(f" - Gagal parsing OSM: {e}")

        st.error(f" - Tidak ditemukan polygon untuk {kel}")
        status.append((kel, "NOT_FOUND"))
        progress.progress((i+1)/len(kelurahan_list))

    # Gabungkan hasil
    if gdfs:
        merged = pd.concat(gdfs, ignore_index=True)
        merged = gpd.GeoDataFrame(merged, crs="EPSG:4326")
        merged = merged.dissolve(by="nama_kel", as_index=False)

        st.success(f"Ditemukan polygon untuk {merged.shape[0]} dari {len(kelurahan_list)} kelurahan.")

        kml_obj = simplekml.Kml()
        colors = ["7dff0000","7d00ff00","7d0000ff","7d00ffff","7dff00ff","7dffff00"]
        for idx, row in merged.iterrows():
            name = row["nama_kel"]
            geom = row.geometry
            if geom is None:
                continue
            polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
            for p in polys:
                coords = [(x,y) for x,y in p.exterior.coords]
                pol = kml_obj.newpolygon(name=name, outerboundaryis=coords)
                pol.style.polystyle.color = colors[idx % len(colors)]
                pol.style.linestyle.width = 2

        temp_dir = tempfile.mkdtemp()
        kml_path = os.path.join(temp_dir, "batas_kelurahan_pekanbaru.kml")
        kml_obj.save(kml_path)
        kmz_path = os.path.join(temp_dir, "batas_kelurahan_pekanbaru.kmz")
        with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(kml_path, arcname=os.path.basename(kml_path))

        with open(kml_path, "rb") as f:
            st.download_button("⬇️ Download KML", f, file_name="batas_kelurahan_pekanbaru.kml")
        with open(kmz_path, "rb") as f:
            st.download_button("⬇️ Download KMZ", f, file_name="batas_kelurahan_pekanbaru.kmz")

        df_stat = pd.DataFrame(status, columns=["Kelurahan", "Sumber"])
        st.dataframe(df_stat)
    else:
        st.error("Tidak ada polygon ditemukan. Coba ulangi atau periksa koneksi.")

st.markdown("---")
st.info("Sumber data: BIG Geoservices (MapServer) + OpenStreetMap Overpass API.")
