import streamlit as st

st.set_page_config(page_title="Capslock Komputer Service", layout="centered")

st.sidebar.title("🧰 Capslock Komputer")
menu = st.sidebar.radio(
    "Menu",
    ["🏠 Home", "🧾 Order Servis", "📊 Laporan", "⚙️ Pengaturan"]
)

if menu == "🏠 Home":
    import Home
    Home.show()

elif menu == "🧾 Order Servis":
    import Order
    Order.show()

elif menu == "📊 Laporan":
    import Report
    Report.show()

elif menu == "⚙️ Pengaturan":
    import Setting
    Setting.show()
