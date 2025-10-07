import streamlit as st
import simplekml

st.set_page_config(page_title="Batas Kelurahan Pekanbaru", page_icon="🗺️")

st.title("🗺️ Batas Kelurahan Pekanbaru (KML/KMZ Generator)")
st.write("Aplikasi sederhana untuk membuat file KML dan KMZ batas kelurahan di Pekanbaru (data BIG + OSM).")

# Daftar kelurahan resmi
kelurahan_list = [
    "Simpang Tiga",
    "Tangkerang Labuai",
    "Pesisir",
    "Wonorejo",
    "Maharatu",
    "Perhentian Marpoyan",
    "Labuh Baru Timur",
    "Sukamaju",
    "Sukamulya",
    "Kota Baru",
    "Simpang Empat",
    "Sukaramai",
    "Sumahilang",
    "Tanah Datar",
    "Harjosari",
    "Jadirejo",
    "Kedungsari",
    "Pulau Karomah",
    "Sialangrampai",
    "Kampung Dalam",
    "Padang Bulan",
    "Sago",
    "Meranti Pandak",
    "Binawidya",
    "Simpang Baru",
    "Tobek Godang",
    "Mentangor"
]

st.subheader("Daftar Kelurahan:")
st.write(", ".join(kelurahan_list))

st.divider()

st.info("Klik tombol di bawah untuk membuat file KML dan KMZ batas kelurahan (data poligon contoh).")

if st.button("Buat & Unduh File KML/KMZ"):
    kml = simplekml.Kml()
    
    # Contoh titik poligon dummy (nanti bisa diganti dengan data BIG/OSM)
    for name in kelurahan_list:
        pol = kml.newpolygon(name=name)
        pol.outerboundaryis = [
            (101.41, 0.51),
            (101.42, 0.51),
            (101.42, 0.52),
            (101.41, 0.52),
            (101.41, 0.51)
        ]
        pol.style.polystyle.color = "7dff0000"  # semi transparan merah
        pol.style.linestyle.color = "ff0000ff"
        pol.style.linestyle.width = 2

    # Simpan file
    kml.save("batas_kelurahan_pekanbaru.kml")
    kml.savekmz("batas_kelurahan_pekanbaru.kmz")

    with open("batas_kelurahan_pekanbaru.kml", "rb") as f:
        st.download_button("⬇️ Download File KML", f, file_name="batas_kelurahan_pekanbaru.kml")

    with open("batas_kelurahan_pekanbaru.kmz", "rb") as f:
        st.download_button("⬇️ Download File KMZ", f, file_name="batas_kelurahan_pekanbaru.kmz")

    st.success("✅ File KML dan KMZ berhasil dibuat!")
