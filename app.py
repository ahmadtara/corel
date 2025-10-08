# app.py
import streamlit as st
from streamlit_option_menu import option_menu
import Order, Report, Setting
from drive_auth import login_google_drive

st.set_page_config(page_title="Servis Center", page_icon="🧾", layout="centered")

# ✅ login Google sekali saja di sini
creds = login_google_drive()

with st.sidebar:
    selected = option_menu(
        "📱 Capslock Komputer",
        ["🧾 Order", "📈 Report", "⚙️ Setting"],
        icons=["file-earmark-plus", "bar-chart-line", "gear"],
        menu_icon="pc-display",
        default_index=0
    )

if selected == "🧾 Order":
    Order.show()
elif selected == "📈 Report":
    Report.show()
elif selected == "⚙️ Setting":
    Setting.show()
