# app.py (FINAL) - Dengan menu Konfirmasi Pelanggan
import streamlit as st
from streamlit_option_menu import option_menu
import Order, Report, Setting, Admin, Expense, Pelanggan  # ✅ tambahkan Pelanggan

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
            "💸 Pengeluaran",
            "📈 Report",
            "📦 Admin",
            "✅ Konfirmasi Pelanggan",  # ✅ menu baru
            "⚙️ Setting"
        ],
        icons=[
            "file-earmark-plus",  # Order
            "cash-coin",          # Pengeluaran
            "bar-chart-line",     # Report
            "box-seam",           # Admin
            "person-check",       # Konfirmasi Pelanggan
            "gear"                # Setting
        ],
        menu_icon="pc-display",
        default_index=0
    )

# ---------------------- ROUTING HALAMAN ----------------------
if selected == "🧾 Order":
    Order.show()
elif selected == "💸 Pengeluaran":
    Expense.show()
elif selected == "📈 Report":
    Report.show()
elif selected == "📦 Admin":
    Admin.show()
elif selected == "✅ Konfirmasi Pelanggan":  # ✅ panggil Pelanggan.py
    Pelanggan.show()
elif selected == "⚙️ Setting":
    Setting.show()
