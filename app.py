import streamlit as st
import xml.etree.ElementTree as ET
from io import BytesIO
import re

st.title("🔄 Balik Urutan Placemark KML")

uploaded_file = st.file_uploader("Upload file KML", type=["kml"])

if uploaded_file is not None:
    try:
        # Baca isi file asli (decode ke string)
        file_content = uploaded_file.read().decode("utf-8")

        # Hapus semua deklarasi xmlns
        file_content = re.sub(r"\sxmlns(:\w+)?=\"[^\"]+\"", "", file_content)
        # Hapus prefix di tag, contoh <gx:Track> jadi <Track>
        file_content = re.sub(r"<(/?)(\w+):", r"<\1", file_content)

        # Parsing XML yang sudah dibersihkan
        tree = ET.ElementTree(ET.fromstring(file_content))
        root = tree.getroot()

        # Cari Document atau Folder
        doc = root.find(".//Document")
        if doc is None:
            doc = root.find(".//Folder")

        if doc is not None:
            # Ambil semua Placemark ke dalam list (urut asli)
            placemarks = list(doc.findall("Placemark"))

            if len(placemarks) > 0:
                # Hapus semua Placemark dari doc
                for pm in placemarks:
                    doc.remove(pm)

                # Append ulang dengan urutan terbalik
                for pm in placemarks[::-1]:
                    doc.append(pm)

                # Simpan hasil ke buffer
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
                st.warning("⚠️ Tidak ada Placemark ditemukan di dalam file KML.")
        else:
            st.error("❌ Tidak ditemukan Document atau Folder di dalam file KML.")

    except Exception as e:
        st.error(f"⚠️ Gagal parsing KML: {e}")
