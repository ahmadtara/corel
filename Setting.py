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
        "footer_nota": "Terima kasih sudah servis di Capslock Komputer 🙏",
        "template_wa": "Halo {nama}, servis {barang} Anda sudah selesai ✅. Silakan diambil di toko."
    }

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)

def show():
    st.title("⚙️ Pengaturan Toko")
    cfg = load_config()

    nama_toko = st.text_input("Nama Toko", cfg["nama_toko"])
    alamat = st.text_area("Alamat", cfg["alamat"])
    footer = st.text_area("Teks Footer Nota", cfg["footer_nota"])
    template_wa = st.text_area("Template Pesan WhatsApp", cfg["template_wa"])

    if st.button("💾 Simpan Pengaturan"):
        new_cfg = {
            "nama_toko": nama_toko,
            "alamat": alamat,
            "footer_nota": footer,
            "template_wa": template_wa
        }
        save_config(new_cfg)
        st.success("✅ Pengaturan berhasil disimpan.")
