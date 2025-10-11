import streamlit as st
from streamlit_option_menu import option_menu
import Order, Report, Setting, Admin, Expense  # ✅ tambahkan Expense

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
            "💸 Pengeluaran",  # ✅ Tambah menu baru
            "📈 Report",
            "📦 Admin",
            "⚙️ Setting"
        ],
        icons=[
            "file-earmark-plus",
            "box-seam",
            "cash-coin",       # 💸 ikon pengeluaran
            "bar-chart-line",
            "gear"
        ],
        menu_icon="pc-display",
        default_index=0
    )

# ---------------------- ROUTING HALAMAN ----------------------
if selected == "🧾 Order":
    Order.show()
elif selected == "💸 Pengeluaran":   # ✅ routing baru
    Expense.show()
elif selected == "📈 Report":
    Report.show()
elif selected == "📦 Admin":
    Admin.show()
elif selected == "⚙️ Setting":
    Setting.show()
