import streamlit as st
import pandas as pd
import datetime
import os
import requests
import tempfile
import base64
from reportlab.lib.pagesizes import A7
from reportlab.pdfgen import canvas
import json

DATA_FILE = "service_data.csv"
CONFIG_FILE = "config.json"

# ---------------------- CONFIG ----------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Sudirman No. 123, Pekanbaru",
        "footer_nota": "Terima kasih sudah servis di Capslock Komputer 🙏",
        "template_wa": "Halo {nama}, servis {barang} Anda sudah selesai ✅. Silakan diambil di toko."
    }

# ---------------------- DATA ----------------------
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=[
            "Tanggal", "Nama Pelanggan", "No HP", "Barang",
            "Kerusakan", "Kelengkapan", "Status"
        ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ---------------------- PDF STRUK ----------------------
def buat_struk_pdf(cfg, nama, no_hp, barang, kerusakan, kelengkapan):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    c = canvas.Canvas(temp_file.name, pagesize=A7)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(105, 380, cfg["nama_toko"])
    c.setFont("Helvetica", 7)
    c.drawCentredString(105, 365, cfg["alamat"])
    c.line(10, 360, 190, 360)

    c.setFont("Helvetica", 8)
    c.drawString(10, 345, f"Tanggal : {datetime.date.today()}")
    c.drawString(10, 330, f"Nama    : {nama}")
    c.drawString(10, 315, f"No HP   : {no_hp}")
    c.drawString(10, 300, f"Barang  : {barang}")
    c.drawString(10, 285, f"Kerusakan : {kerusakan}")
    c.drawString(10, 270, f"Kelengkapan : {kelengkapan}")

    c.line(10, 260, 190, 260)
    c.drawString(10, 245, "Barang diterima untuk diperiksa/servis.")
    c.drawCentredString(105, 230, cfg["footer_nota"])
    c.showPage()
    c.save()
    return temp_file.name

# ---------------------- UI ----------------------
def show():
    cfg = load_config()
    st.title("🧾 Input Servis Baru")

    with st.form("form_service"):
        nama = st.text_input("Nama Pelanggan")
        no_hp = st.text_input("Nomor WhatsApp", placeholder="6281234567890 (tanpa +)")
        barang = st.text_input("Nama Barang", placeholder="Laptop ASUS A409")
        kerusakan = st.text_area("Detail Kerusakan", placeholder="Tidak bisa booting")
        kelengkapan = st.text_area("Kelengkapan", placeholder="Charger, Tas")
        submitted = st.form_submit_button("💾 Simpan Servis")

    if submitted:
        if not all([nama, no_hp, barang]):
            st.error("Nama, Nomor HP, dan Barang wajib diisi!")
            return

        df = load_data()
        new = pd.DataFrame([{
            "Tanggal": datetime.date.today(),
            "Nama Pelanggan": nama,
            "No HP": no_hp,
            "Barang": barang,
            "Kerusakan": kerusakan,
            "Kelengkapan": kelengkapan,
            "Status": "Diterima"
        }])
        df = pd.concat([df, new], ignore_index=True)
        save_data(df)
        st.success(f"✅ Servis {barang} oleh {nama} berhasil disimpan!")

        pdf_path = buat_struk_pdf(cfg, nama, no_hp, barang, kerusakan, kelengkapan)
        with open(pdf_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            href = f'<a href="data:application/pdf;base64,{b64}" download="Nota_Servis_{nama}.pdf">🖨️ Download Nota PDF (Thermal)</a>'
            st.markdown(href, unsafe_allow_html=True)

    st.divider()
    st.subheader("📋 Daftar Servis Masuk")

    df = load_data()
    if df.empty:
        st.info("Belum ada servis masuk.")
        return

    for i, row in df.iterrows():
        with st.expander(f"{row['Nama Pelanggan']} - {row['Barang']} ({row['Status']})"):
            st.write(f"📅 **Tanggal:** {row['Tanggal']}")
            st.write(f"📞 **No HP:** {row['No HP']}")
            st.write(f"💻 **Barang:** {row['Barang']}")
            st.write(f"🧩 **Kerusakan:** {row['Kerusakan']}")
            st.write(f"🎒 **Kelengkapan:** {row['Kelengkapan']}")
            st.write(f"📦 **Status:** {row['Status']}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"✅ Tandai Selesai #{i}", key=f"done_{i}"):
                    df.at[i, "Status"] = "Selesai"
                    save_data(df)
                    st.success("Servis ditandai selesai.")

            with col2:
                if st.button(f"💬 Kirim WA #{i}", key=f"wa_{i}"):
                    msg = cfg["template_wa"].format(
                        nama=row["Nama Pelanggan"],
                        barang=row["Barang"]
                    )

                    # --- PERBAIKAN LINK WA RESMI ---
                    no_hp = str(row["No HP"]).replace("+", "").replace(" ", "").strip()
                    if no_hp:
                        link = f"https://wa.me/{no_hp}?text={requests.utils.quote(msg)}"
                        st.markdown(f"[📲 Kirim WhatsApp ke {no_hp}]({link})")
                        st.info(f"Link WhatsApp: {link}")
                    else:
                        st.warning("⚠️ Nomor HP kosong, tidak bisa kirim WhatsApp.")
