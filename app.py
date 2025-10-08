import streamlit as st

st.set_page_config(page_title="KasirApp", layout="centered")

# Cek halaman aktif (default: Home)
if "page" not in st.session_state:
    st.session_state.page = "Home"

# Fungsi untuk berpindah halaman
def go(page):
    st.session_state.page = page
    st.experimental_rerun()

# Header logo
st.markdown("<h2 style='text-align:center; color:#E53935;'>🧾 KasirApp</h2>", unsafe_allow_html=True)

# Routing ke halaman sesuai pilihan
if st.session_state.page == "Home":
    import Home
    Home.show()
elif st.session_state.page == "Order":
    import Order
    Order.show()
elif st.session_state.page == "Report":
    import Report
    Report.show()
elif st.session_state.page == "Setting":
    import Setting
    Setting.show()

# ==== NAVBAR BAWAH ====
st.markdown("""
<style>
.navbar {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background: #fff;
    border-top: 1px solid #ddd;
    display: flex;
    justify-content: space-around;
    padding: 8px 0;
}
.nav-item {
    text-align: center;
    font-size: 13px;
    color: #999;
}
.nav-item.active {
    color: #E53935;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# Tombol navigasi
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🏠\nHome"):
        go("Home")
with col2:
    if st.button("🧾\nOrder"):
        go("Order")
with col3:
    if st.button("📊\nReport"):
        go("Report")
with col4:
    if st.button("⚙️\nSetting"):
        go("Setting")
