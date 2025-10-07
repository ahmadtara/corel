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
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
import simplekml

st.set_page_config(page_title="Batas Kelurahan Pekanbaru (BIG + OSM)", layout="wide")
st.title("Batas Kelurahan Pekanbaru — (BIG → fallback OSM)")
st.write("Aplikasi akan mencoba ambil polygon tiap kelurahan dari BIG (utama) lalu OSM (fallback).")

# === Daftar kelurahan final (27) ===
kelurahan_list = [
    "Simpang Tiga","Tangkerang Labuai","Pesisir","Wonorejo","Maharatu",
    "Perhentian Marpoyan","Labuh Baru Timur","Sukamaju","Sukamulya","Kota Baru",
    "Simpang Empat","Sukaramai","Sumahilang","Tanah Datar","Harjosari",
    "Jadirejo","Kedungsari","Pulau Karomah","Sialangrampai","Kampung Dalam",
    "Padang Bulan","Sago","Meranti Pandak","Binawidya","Simpang Baru",
    "Tobek Godang","Mentangor"
]

BASE_BIG = "https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/BATAS_WILAYAH/MapServer/11/query"
# note: layer 11 in BIG often berisi desa/kelurahan; kalau berbeda di masa depan, ubah URL.

# Helper: normalize name for matching tolerant
def norm(s):
    return "".join(c for c in s.lower() if c.isalnum())

# Query BIG for single kelurahan by exact field match (wakld1 etc)
def query_big_kelurahan(name):
    # try several where clauses tolerant to ejaan/spasi: wakld1, name, nama
    queries = [
        f"wakbk1 LIKE '%PEKANBARU%' AND wakld1 = '{name.replace(\"'\",\"''")}'",
        f"wakbk1 LIKE '%PEKANBARU%' AND upper(wakld1) LIKE upper('%{name}%')",
        f"upper(nama) LIKE upper('%{name}%')",
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
            features = data.get("features", [])
            if features:
                return data  # raw geojson featurecollection
        except Exception as e:
            # fail silently and try next query
            pass
        time.sleep(0.15)
    return None

# Query OSM Overpass for boundary by name inside Pekanbaru area
def query_osm_kelurahan(name):
    # 1) find area id for Pekanbaru (by relation)
    try:
        # get relation id for Pekanbaru
        q_area = f'[out:json][timeout:25];relation["name"="Pekanbaru"]["admin_level"~"7|8|6"];out ids;'
        r = requests.get("https://overpass-api.de/api/interpreter", params={"data": q_area}, timeout=30)
        r.raise_for_status()
        res = r.json()
        if not res.get("elements"):
            return None
        rel_id = res["elements"][0]["id"]
        area_id = 3600000000 + rel_id
        # Now search for relation/way with admin_level 8 (kelurahan) and name match in that area
        q = (
            f'[out:json][timeout:25];area({area_id})->.a;'
            f'('
            f'relation["admin_level"~"8|9"]["name"~"^{name}$",i](area.a);'
            f'way["admin_level"~"8|9"]["name"~"^{name}$",i](area.a);'
            f');out geom;'
        )
        r2 = requests.get("https://overpass-api.de/api/interpreter", params={"data": q}, timeout=60)
        r2.raise_for_status()
        data = r2.json()
        if data.get("elements"):
            # convert to GeoDataFrame
            geoms = []
            props = []
            for el in data["elements"]:
                if el["type"] == "relation":
                    # assemble multipolygon from members (Overpass returns 'members' with geometry in 'geometry' field)
                    # But Overpass with out geom returns geometry on the relation itself sometimes
                    coords = None
                    if "members" in el:
                        # reconstruct using members is complex; easier: if 'tags' and 'bounds' available, skip complex
                        pass
                    if "geometry" in el:
                        # geometry is list of points (likely outer ring)
                        poly = shape({"type":"Polygon", "coordinates":[[(pt["lon"], pt["lat"]) for pt in el["geometry"]]]})
                        geoms.append(poly)
                        props.append(el.get("tags", {}))
                elif el["type"] == "way":
                    if "geometry" in el:
                        poly = shape({"type":"Polygon", "coordinates":[[(pt["lon"], pt["lat"]) for pt in el["geometry"]]]})
                        geoms.append(poly)
                        props.append(el.get("tags", {}))
            if geoms:
                gdf = gpd.GeoDataFrame(props, geometry=geoms, crs="EPSG:4326")
                return json.loads(gdf.to_json())
    except Exception as e:
        return None
    return None

# Main action
if st.button("🔍 Generate semua kelurahan (BIG → OSM)"):
    status = []
    gdfs = []
    progress = st.progress(0)
    for i, kel in enumerate(kelurahan_list):
        st.write(f"Memproses: **{kel}**")
        # 1) try BIG
        data = query_big_kelurahan(kel)
        if data:
            # convert features to GeoDataFrame
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
                st.warning(f" - Error parsing BIG result for {kel}: {e}")

        # 2) try OSM fallback
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
                st.warning(f" - Error parsing OSM result for {kel}: {e}")

        # 3) not found
        st.error(f" - Tidak ditemukan polygon untuk: {kel}")
        status.append((kel, "NOT_FOUND"))
        progress.progress((i+1)/len(kelurahan_list))

    # combine results
    if gdfs:
        merged = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs="EPSG:4326")
        # optional: dissolve by our kelurahan name to unify multipart pieces
        merged = merged.dissolve(by="nama_kel", as_index=False)
        st.success(f"Ditemukan polygon untuk {merged.shape[0]} / {len(kelurahan_list)} kelurahan.")

        # build KML with different styles per kelurahan
        kml_obj = simplekml.Kml()
        colors = [
            "7dff0000","7d00ff00","7d0000ff","7d00ffff","7dff00ff","7dffff00",
            "7d880000","7d008800","7d000088","7d888800","7d880088","7d008888"
        ]
        for idx, row in merged.iterrows():
            name = row["nama_kel"]
            geom = row.geometry
            # convert to polygons list
            polys = []
            if geom.geom_type == "Polygon":
                polys = [geom]
            elif geom.geom_type == "MultiPolygon":
                polys = list(geom.geoms)
            else:
                continue
            for p in polys:
                coords = [(x,y) for x,y in p.exterior.coords]
                pol = kml_obj.newpolygon(name=name, outerboundaryis=coords)
                color = colors[idx % len(colors)]
                pol.style.polystyle.color = color
                pol.style.linestyle.width = 2

        # save KML to bytes
        temp_dir = tempfile.mkdtemp()
        kml_path = os.path.join(temp_dir, "batas_kelurahan_pekanbaru.kml")
        kml_obj.save(kml_path)
        kmz_path = os.path.join(temp_dir, "batas_kelurahan_pekanbaru.kmz")
        with zipfile.ZipFile(kmz_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(kml_path, arcname=os.path.basename(kml_path))

        with open(kml_path, "rb") as f:
            st.download_button("⬇️ Download KML", data=f, file_name="batas_kelurahan_pekanbaru.kml")
        with open(kmz_path, "rb") as f:
            st.download_button("⬇️ Download KMZ", data=f, file_name="batas_kelurahan_pekanbaru.kmz")

        st.write("Status per kelurahan (sumber):")
        df_stat = pd.DataFrame(status, columns=["kelurahan","source"])
        st.dataframe(df_stat)
    else:
        st.error("Gagal menemukan polygon untuk semua kelurahan. Periksa koneksi atau sumber data.")

st.markdown("---")
st.info("Sumber data: BIG Geoservices (MapServer) + OpenStreetMap Overpass API. Jika ada kelurahan yang tetap tidak ditemukan, kita bisa ambil dari shapefile resmi (BIG / Alf-Anas repo) dan upload manual.")
