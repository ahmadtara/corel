import streamlit as st
import requests
import simplekml
import time
import zipfile
import io
from shapely.geometry import shape, Polygon, MultiPolygon

st.set_page_config(page_title="Batas Kelurahan → KML", page_icon="🗺️")

st.title("🗺️ Buat KML Polygon Batas Kelurahan (Data BIG)")

st.markdown("""
Aplikasi ini mengambil batas wilayah **kelurahan** dari layanan **Badan Informasi Geospasial (BIG)**  
dan mengekspor hasilnya ke file **KML/KMZ** yang bisa dibuka di Google Earth.
""")

default_kelurahan = """Simpang Tiga
Tangkerang Labuai
Pesisir
Wonorejo
Maharatu
Perhentianmarpoyan
Labuh Baru Timur
Sukamaju
Sukamulya
Kota Baru
Simpang Empat
Sukaramai
Sumahilang
Tanah Datar
Harjosari
Jadirejo
Kedung Sari
Pulau Karomah
Sialangrampai
Kampung Dalam
Padang Bulan
Sago
Meranti Pandak
Binawidya
Simpangbaru
Tobekgodang
Mentangor"""

kelurahan_input = st.text_area("📍 Daftar nama kelurahan (satu per baris):", default_kelurahan, height=300)

run_button = st.button("🚀 Generate KML & KMZ")

BASE_URL = "https://geoservices.big.go.id/rbi/rest/services/BATASWILAYAH/BATAS_WILAYAH/MapServer/11/query"

def query_kelurahan(nama_kel):
    where = f"wakbk1 LIKE '%PEKANBARU%' AND wakld1 = '{nama_kel.replace("'", "''")}'"
    params = {
        "where": where,
        "outFields": "*",
        "f": "geojson",
        "outSR": "4326",
        "returnGeometry": "true"
    }
    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

if run_button:
    kelurahan_list = [k.strip() for k in kelurahan_input.split("\n") if k.strip()]
    st.info(f"Mengambil data untuk {len(kelurahan_list)} kelurahan...")
    kml = simplekml.Kml()
    not_found = []
    progress = st.progress(0)
    log = st.empty()

    for idx, name in enumerate(kelurahan_list):
        log.write(f"⏳ Memproses: **{name}** ...")
        try:
            geojson = query_kelurahan(name)
            features = geojson.get("features", [])
            if not features:
                not_found.append(name)
                log.write(f"⚠️ Tidak ditemukan: {name}")
                continue

            for feat in features:
                geom = feat.get("geometry")
                if geom:
                    geom_shape = shape(geom)
                    polys = []
                    if isinstance(geom_shape, Polygon):
                        polys = [geom_shape]
                    elif isinstance(geom_shape, MultiPolygon):
                        polys = list(geom_shape.geoms)

                    for poly in polys:
                        coords = [(x, y) for x, y in poly.exterior.coords]
                        p = kml.newpolygon(name=name, outerboundaryis=coords)
                        p.altitudemode = simplekml.AltitudeMode.clampToGround
                        p.style.polystyle.color = simplekml.Color.changealphaint(80, simplekml.Color.blue)
                        p.style.linestyle.color = simplekml.Color.red
                        p.style.linestyle.width = 1
            log.write(f"✅ Berhasil: {name}")
        except Exception as e:
            not_found.append(name)
            log.write(f"❌ Gagal ambil {name}: {e}")
        progress.progress((idx + 1) / len(kelurahan_list))
        time.sleep(0.2)

    # Simpan ke KML & KMZ
    kml_buffer = io.BytesIO()
    kml.save(kml_buffer)
    kml_bytes = kml_buffer.getvalue()

    kmz_buffer = io.BytesIO()
    with zipfile.ZipFile(kmz_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("kelurahan_pekanbaru.kml", kml_bytes)
    kmz_bytes = kmz_buffer.getvalue()

    st.success("✅ Selesai membuat file KML dan KMZ!")

    st.download_button("⬇️ Download KML", kml_bytes, "kelurahan_pekanbaru.kml")
    st.download_button("⬇️ Download KMZ (Zip)", kmz_bytes, "kelurahan_pekanbaru.kmz")

    if not_found:
        st.warning("⚠️ Beberapa kelurahan tidak ditemukan:")
        st.write(", ".join(not_found))
