import streamlit as st
import xml.etree.ElementTree as ET

st.title("🖊️ Ganti Teks di Template SVG (Corel)")

# Upload SVG template
uploaded_file = st.file_uploader("Upload file SVG dari Corel", type=["svg"])

if uploaded_file:
    tree = ET.parse(uploaded_file)
    root = tree.getroot()

    # Input teks pengganti
    old_text = st.text_input("Teks lama (misalnya: OAKN1.036)")
    new_text = st.text_input("Teks baru (misalnya: BKSN2.045)")

    fat_a = st.number_input("Jumlah FAT A", min_value=0, max_value=100, value=8)
    fat_b = st.number_input("Jumlah FAT B", min_value=0, max_value=100, value=8)
    fat_c = st.number_input("Jumlah FAT C", min_value=0, max_value=100, value=8)
    fat_d = st.number_input("Jumlah FAT D", min_value=0, max_value=100, value=8)

    if st.button("🔄 Proses Replace"):
        count_replace = 0
        for elem in root.iter():
            if elem.text and old_text in elem.text:
                elem.text = elem.text.replace(old_text, new_text)
                count_replace += 1

        # Update FAT otomatis
        fat_sections = {
            "FAT A": fat_a,
            "FAT B": fat_b,
            "FAT C": fat_c,
            "FAT D": fat_d,
        }

        for elem in root.iter():
            if elem.text:
                for prefix, limit in fat_sections.items():
                    if elem.text.startswith(prefix):
                        # Ambil nomor FAT sekarang
                        try:
                            num = int(elem.text.split(" ")[-1][1:])  # contoh FAT A01 → 1
                        except:
                            continue
                        if num > limit:
                            elem.text = ""  # hapus kalau lebih dari limit

        # Simpan hasil
        output_file = "output.svg"
        tree.write(output_file, encoding="utf-8", xml_declaration=True)

        with open(output_file, "rb") as f:
            st.download_button(
                "⬇️ Download hasil SVG",
                f,
                file_name="output.svg",
                mime="image/svg+xml"
            )

        st.success(f"Teks '{old_text}' berhasil diganti jadi '{new_text}'. {count_replace} kali diganti.")
