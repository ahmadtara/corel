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
        json.dump(cfg, f, indent=2)

def show():
    st.title("⚙️ Pengaturan Toko")

    cfg = load_config()
    nama = st.text_input("Nama Toko", value=cfg["nama_toko"])
    alamat = st.text_area("Alamat Toko", value=cfg["alamat"])
    footer = st.text_area("Footer Nota", value=cfg["footer_nota"])
    template = st.text_area("Template Pesan WhatsApp", value=cfg["template_wa"])

    if st.button("💾 Simpan"):
        cfg["nama_toko"] = nama
        cfg["alamat"] = alamat
        cfg["footer_nota"] = footer
        cfg["template_wa"] = template
        save_config(cfg)
        st.success("✅ Pengaturan disimpan.")
