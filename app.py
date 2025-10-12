# ========================== app.py (v3.1 - Bottom Navigation Android Style) ==========================
import streamlit as st
from streamlit_option_menu import option_menu
import Order, Report, Setting, Admin, Expense, Pelanggan

# ---------------------- KONFIGURASI HALAMAN ----------------------
st.set_page_config(
    page_title="Servis Center",
    page_icon="🧾",
    layout="wide"
)

# ---------------------- LOGIN CONFIG ----------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------------- LOGIN FORM ----------------------
def login_form():
    st.subheader("🔐 Login Admin")
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login", use_container_width=True):
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            st.session_state.logged_in = True
            st.success("✅ Login berhasil!")
            st.rerun()
        else:
            st.error("❌ Username atau password salah!")

# ---------------------- LOGOUT BUTTON ----------------------
def logout_button():
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.success("Berhasil logout.")
        st.rerun()

# ---------------------- CSS UNTUK MENU BAWAH ----------------------
st.markdown("""
    <style>
    /* Hilangkan sidebar */
    section[data-testid="stSidebar"] {display: none;}

    /* Posisi menu bawah */
    div[data-testid="stHorizontalBlock"] {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        background-color: #fff;
        border-top: 1px solid #ddd;
        z-index: 999;
        text-align: center;
        padding: 0.2rem 0;
    }

    /* Gaya ikon menu */
    ul.nav {
        display: flex !important;
        justify-content: space-around;
        margin: 0;
        padding: 0;
        width: 100%;
    }
    .nav-item {
        flex: 1;
    }
    .nav-item > a {
        color: #9b9b9b !important;
        font-weight: 500;
        font-size: 13px;
    }
    .nav-item > a:hover {
        color: #FF4B4B !important;
    }
    .nav-item.active > a {
        color: #FF4B4B !important;
        font-weight: 600;
    }

    /* Tambah jarak konten agar tidak ketutupan menu bawah */
    .block-container {
        padding-bottom: 5rem;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------- MENU BAWAH ----------------------
if not st.session_state.logged_in:
    selected = option_menu(
        None,
        ["🏠 Home", "🧾 Order", "✅ Pelanggan", "💸 Pengeluaran", "🔐 Login"],
        icons=["house", "file-earmark-plus", "person-check", "cash-coin", "lock"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal"
    )
else:
    selected = option_menu(
        None,
        ["🏠 Home", "🧾 Order", "📈 Report", "⚙️ Setting", "🚪 Logout"],
        icons=["house", "file-earmark-plus", "bar-chart-line", "gear", "door-closed"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal"
    )

# ---------------------- ROUTING HALAMAN ----------------------
if not st.session_state.logged_in:
    if selected == "🏠 Home":
        st.title("📱 Selamat Datang di Servis Center")
        st.info("Gunakan menu bawah untuk navigasi.")
    elif selected == "🧾 Order":
        Order.show()
    elif selected == "✅ Pelanggan":
        Pelanggan.show()
    elif selected == "💸 Pengeluaran":
        Expense.show()
    elif selected == "🔐 Login":
        login_form()

else:
    if selected == "🏠 Home":
        st.title("📊 Dashboard Admin")
        st.success("Halo Admin 👋")
    elif selected == "🧾 Order":
        Order.show()
    elif selected == "📈 Report":
        Report.show()
    elif selected == "⚙️ Setting":
        Setting.show()
    elif selected == "🚪 Logout":
        logout_button()
