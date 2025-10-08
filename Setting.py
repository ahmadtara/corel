import streamlit as st
import json
import os

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Sudirman No. 123, Pekanbaru",
        "no_toko": "6285172174759",
        "footer_nota": "Terima kasih sudah servis di Capslock Komputer 🙏",
        "template_wa": (
            "🧾 *NOTA ELEKTRONIK*\n\n"
            "💻 *{nama_toko}*\n"
            "{alamat}\n"
            "HP : {no_toko}\n\n"
            "=======================\n"
            "No Nota : {no_nota}\n"
            "Pelanggan : {nama}\n"
            "Tanggal Masuk : {tanggal_masuk}\n"
            "Estimasi Selesai : {estimasi}\n"
            "=======================\n"
            "{barang}\n"
            "{kerusakan}\n"
            "{kelengkapan}\n"
            "=======================\n"
            "Harga : {harga}\n"
            "Status : {status}\n"
            "Dapatkan Promo Mahasiswa 🎓\n"
            "=======================\n\n"
            "Best Regard Admin {nama_toko}\n"
            "{footer_nota}"
        )
    }

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

def show():
    st.title("⚙️ Pengaturan Toko")

    cfg = load_config()

    st.subheader("🛠️ Informasi Toko")
    nama_toko = st.text_input("Nama Toko", cfg["nama_toko"])
    alamat = st.text_area("Alamat Toko", cfg["alamat"])
    no_toko = st.text_input("Nomor WhatsApp Toko", cfg.get("no_toko", ""))
    footer = st.text_area("Teks Footer Nota", cfg["footer_nota"])

    st.subheader("💬 Template Pesan WhatsApp")
    st.caption("Gunakan placeholder: {nama}, {barang}, {tanggal_masuk}, {estimasi}, {status}, {harga}, {no_nota}")
    template_wa = st.text_area("Template Pesan WhatsApp", cfg["template_wa"], height=250)

    # Preview pesan
    st.markdown("### 📱 Preview Pesan WA")
    contoh = template_wa.format(
        nama_toko=nama_toko,
        alamat=alamat,
        no_toko=no_toko,
        footer_nota=footer,
        nama="Ahmad",
        barang="Laptop ASUS A409",
        kerusakan="Tidak bisa nyala",
        kelengkapan="Charger",
        harga="150000",
        status="Cek Dulu",
        tanggal_masuk="21/08/2025 - 10:07",
        estimasi="24/08/2025 - 10:07",
        no_nota="TRX/0000001"
    )
    st.code(contoh, language="")

    if st.button("💾 Simpan Pengaturan"):
        new_cfg = {
            "nama_toko": nama_toko,
            "alamat": alamat,
            "no_toko": no_toko,
            "footer_nota": footer,
            "template_wa": template_wa
        }
        save_config(new_cfg)
        st.success("✅ Pengaturan berhasil disimpan.")
