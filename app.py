import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm

# ==========================
# Fungsi untuk generate PDF
# ==========================
def generate_pdf(project_code, fat_a, fat_b, fat_c, fat_d, width_mm, height_mm):
    file_name = "output.pdf"

    # Konversi ke mm sesuai ukuran Corel
    width, height = width_mm * mm, height_mm * mm
    c = canvas.Canvas(file_name, pagesize=(width, height))

    # Judul project (posisi atas tengah)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 15*mm, project_code)

    # Mulai posisi FAT
    y = height - 30*mm
    x_start = 20*mm

    def draw_fat(prefix, count, y_start):
        x = x_start
        y = y_start
        for i in range(1, count + 1):
            text = f"FAT {prefix}{i:02d}"
            c.setFont("Helvetica-Bold", 12)
            c.drawString(x, y, text)
            x += 30*mm  # jarak antar FAT
            if x > (width - 30*mm):  # kalau mentok kanan, turun baris
                x = x_start
                y -= 8*mm
        return y - 10*mm

    # Generate FAT A-D
    y = draw_fat("A", fat_a, y)
    y = draw_fat("B", fat_b, y)
    y = draw_fat("C", fat_c, y)
    y = draw_fat("D", fat_d, y)

    c.save()
    return file_name

# ==========================
# Streamlit UI
# ==========================
st.title("📑 Generator Label FAT (Export ke PDF untuk Corel)")

# Input ukuran halaman (sesuaikan dengan ukuran Corel kamu)
width_mm = st.number_input("Lebar Halaman (mm)", 50, 1000, 300)
height_mm = st.number_input("Tinggi Halaman (mm)", 50, 1000, 200)

# Input teks utama dan jumlah FAT
project_code = st.text_input("Masukkan Kode Project", "OAKN1.036")
fat_a = st.number_input("Jumlah FAT A", 0, 200, 8)
fat_b = st.number_input("Jumlah FAT B", 0, 200, 8)
fat_c = st.number_input("Jumlah FAT C", 0, 200, 8)
fat_d = st.number_input("Jumlah FAT D", 0, 200, 8)

# Tombol generate
if st.button("🚀 Generate PDF"):
    file_path = generate_pdf(project_code, fat_a, fat_b, fat_c, fat_d, width_mm, height_mm)
    with open(file_path, "rb") as f:
        st.download_button("⬇️ Download PDF", f, file_name="output.pdf")
