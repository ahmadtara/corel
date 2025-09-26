import streamlit as st
import xml.etree.ElementTree as ET
import math
from io import BytesIO

# ----------------------
# Fungsi bantu
# ----------------------
def haversine(lon1, lat1, lon2, lat2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def interpolate_point(lon1, lat1, lon2, lat2, ratio):
    lon = lon1 + (lon2 - lon1) * ratio
    lat = lat1 + (lat2 - lat1) * ratio
    return lon, lat

def nearest_pole(lon, lat, poles):
    """Cari pole terdekat dari titik (lon,lat)"""
    best = None
    best_d = float("inf")
    for plon, plat in poles:
        d = haversine(lon, lat, plon, plat)
        if d < best_d:
            best_d = d
            best = (plon, plat)
    return best

# ----------------------
# App Streamlit
# ----------------------
st.title("📍 Tambahkan Placemark Tiap 400m di Jalur Kabel (Snap ke Pole Terdekat)")

uploaded_file = st.file_uploader("Upload file KML", type=["kml"])

if uploaded_file is not None:
    tree = ET.parse(uploaded_file)
    root = tree.getroot()
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    # --- Ambil LineString path ---
    coords_text = root.find(".//kml:LineString/kml:coordinates", ns).text.strip()
    coords = [(float(c.split(",")[0]), float(c.split(",")[1])) for c in coords_text.split()]

    # --- Ambil semua pole (Point) ---
    poles = []
    for pt in root.findall(".//kml:Placemark/kml:Point/kml:coordinates", ns):
        x, y = map(float, pt.text.strip().split(",")[:2])
        poles.append((x, y))

    # --- Hitung jarak kumulatif ---
    distances = [0]
    for i in range(1, len(coords)):
        distances.append(distances[-1] + haversine(*coords[i-1], *coords[i]))
    total_length = distances[-1]

    # --- Cari titik tiap 400m ---
    interval = 2980
    markers, target = [], interval
    while target <= total_length:
        for i in range(1, len(distances)):
            if distances[i] >= target:
                d_seg = distances[i] - distances[i-1]
                ratio = (target - distances[i-1]) / d_seg
                lon, lat = interpolate_point(*coords[i-1], *coords[i], ratio)
                # snap ke pole terdekat
                nlon, nlat = nearest_pole(lon, lat, poles)
                markers.append((target, nlon, nlat))
                break
        target += interval

    # --- Tambahkan Placemark baru ---
    doc = root.find(".//kml:Document", ns)
    for idx, (dist, lon, lat) in enumerate(markers, start=1):
        pm = ET.Element("Placemark")
        ET.SubElement(pm, "name").text = f"SLACK-{idx:02d}"
        pt = ET.SubElement(pm, "Point")
        ET.SubElement(pt, "coordinates").text = f"{lon},{lat},0"
        doc.append(pm)

    # --- Simpan ke memori ---
    output = BytesIO()
    tree.write(output, encoding="utf-8", xml_declaration=True)
    output.seek(0)

    st.success(f"✅ Panjang kabel ≈ {total_length:.2f} m, Marker ditambahkan: {len(markers)} (snap ke pole)")
    st.download_button("⬇️ Download KML Hasil", output, "POLE_SLACK.kml", "application/vnd.google-earth.kml+xml")
