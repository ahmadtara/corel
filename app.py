import streamlit as st
from streamlit_option_menu import option_menu
import Order, Report, Setting, Admin  # ✅ tambahkan Admin di sini

# ---------------------- KONFIGURASI HALAMAN ----------------------
st.set_page_config(
    page_title="Servis Center",
    page_icon="🧾",
    layout="centered"
)

# ---------------------- SIDEBAR MENU ----------------------
with st.sidebar:
    selected = option_menu(
        "📱 Capslock Komputer",
        [
            "🧾 Order",
            "📦 Admin Barang",  # ✅ Tambah menu baru untuk Admin.py
            "📈 Report",
            "⚙️ Setting"
        ],
        icons=[
            "file-earmark-plus",
            "box-seam",          # ikon untuk Admin Barang
            "bar-chart-line",
            "gear"
        ],
        menu_icon="pc-display",
        default_index=0
    )

# ---------------------- ROUTING HALAMAN ----------------------
if selected == "🧾 Order":
    Order.show()
elif selected == "📦 Admin Barang":  # ✅ Tambah logika baru
    Admin.show()
elif selected == "📈 Report":
    Report.show()
elif selected == "⚙️ Setting":
    Setting.show()
