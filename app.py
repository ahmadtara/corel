import streamlit as st

# Konfigurasi halaman
st.set_page_config(page_title="Edobi Clone", layout="centered")

# ==== STYLE CUSTOM ====
st.markdown("""
<style>
body {
    background-color: #fff;
    font-family: 'Poppins', sans-serif;
}
.header {
    text-align: center;
    margin-bottom: 1rem;
}
.info-box {
    border: 1px solid #eee;
    border-radius: 12px;
    padding: 10px;
    text-align: center;
    background-color: #fafafa;
}
.info-title {
    color: #777;
    font-size: 14px;
}
.info-value {
    font-weight: 600;
    font-size: 16px;
}
.upgrade-btn button {
    background-color: #E53935 !important;
    color: white !important;
    border-radius: 8px !important;
    width: 100%;
    font-weight: bold;
}
.menu-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 0;
    border-bottom: 1px solid #eee;
}
.menu-item img {
    width: 28px;
    height: 28px;
}
.navbar {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background: #fff;
    border-top: 1px solid #eee;
    display: flex;
    justify-content: space-around;
    padding: 10px 0;
}
.nav-item {
    text-align: center;
    font-size: 12px;
    color: #999;
}
.nav-item.active {
    color: #E53935;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ==== HEADER ====
st.markdown("<div class='header'><img src='https://edobi.id/static/media/logo.70f0b2fa.svg' width='100'></div>", unsafe_allow_html=True)

# ==== INFO PANEL ====
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("<div class='info-box'><div class='info-title'>Tipe Akun</div><div class='info-value'>BASIC</div></div>", unsafe_allow_html=True)
with col2:
    st.markdown("<div class='info-box'><div class='info-title'>Masa Aktif</div><div class='info-value'>15/10/2021</div></div>", unsafe_allow_html=True)
with col3:
    st.markdown("<div class='info-box'><div class='info-title'>Jumlah Outlet</div><div class='info-value'>2</div></div>", unsafe_allow_html=True)

st.markdown("<div class='upgrade-btn'>", unsafe_allow_html=True)
st.button("UPGRADE AKUN")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("### ⚙️ Setting")

# ==== MENU LIST ====
menu_items = [
    ("👤", "Profil", "Konfigurasi Profil Pemilik"),
    ("🏠", "Outlet", "Konfigurasi Profil Outlet dan Jam Operasional"),
    ("🧺", "Layanan", "Konfigurasi Layanan"),
    ("👨‍💼", "Pegawai", "Kelola data dan role pegawai"),
    ("🛍️", "Pelanggan", "Kelola data pelanggan"),
    ("💰", "Keuangan", "Kelola Keuangan")
]

for icon, title, desc in menu_items:
    st.markdown(f"""
    <div class='menu-item'>
        <div style='font-size:22px'>{icon}</div>
        <div>
            <div style='font-weight:600'>{title}</div>
            <div style='color:#666;font-size:13px'>{desc}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==== NAVBAR ====
st.markdown("""
<div class='navbar'>
  <div class='nav-item'>🏠<br>Home</div>
  <div class='nav-item'>🧾<br>Order</div>
  <div class='nav-item'>📊<br>Report</div>
  <div class='nav-item active'>⚙️<br>Setting</div>
</div>
""", unsafe_allow_html=True)
