import streamlit as st
import xml.etree.ElementTree as ET
from io import BytesIO

# ----------------------
# Streamlit App
# ----------------------
st.title("🔄 Balik Urutan Placemark KML")

uploaded_file = st.file_uploader("Upload file KML", type=["kml"])

if uploaded_file is not None:
    try:
        # Baca isi file ke memory
        file_content = uploaded_file.read()

        # Register namespace umum KML
        ET.register_namespace("", "http://www.opengis.net/kml/2.2")
        ET.register_namespace("gx", "http://www.google.com/kml/ext/2.2")

        # Parsing XML
        tree = ET.ElementTree(ET.fromstring(file_content))
        root = tree.getroot()

        ns = {
            "kml": "http://www.opengis.net/kml/2.2",
            "gx": "http://www.google.com/kml/ext/2.2",
        }

        # Cari Document atau Folder
        doc = root.find(".//kml:Document", ns)
        if doc is None:
            doc = root.find(".//kml:Folder", ns)

        if doc is not None:
            placemarks = doc.findall("kml:Placemark", ns)

            # Hapus semua dulu
            for pm in placemarks:
                doc.remove(pm)

            # Tambahkan kembali dengan urutan terbalik
            for pm in reversed(placemarks):
                doc.append(pm)

            # Simpan hasil ke memory buffer
            output_buffer = BytesIO()
            tree.write(output_buffer, encoding="UTF-8", xml_declaration=True)
            output_buffer.seek(0)

            st.success("✅ Urutan berhasil dibalik!")
            st.download_button(
                label="💾 Download KML Hasil",
                data=output_buffer,
                file_name="KML_REVERSED.kml",
                mime="application/vnd.google-earth.kml+xml"
            )
        else:
            st.error("❌ Tidak ditemukan Document atau Folder di dalam file KML.")

    except Exception as e:
        st.error(f"⚠️ Gagal parsing KML: {e}")
