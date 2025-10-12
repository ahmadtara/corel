# ========================== app.py (v3.3 - Bottom Nav with Full Admin Menu) ==========================
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
    section[data-testid="stSidebar"] {display: none;}

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

    .block-container {
        padding-bottom: 5rem;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------- MENU BAWAH ----------------------
if not st.session_state.logged_in:
    selected = option_menu(
        None,
        ["🧾 Order", "✅ Pelanggan", "💸 Pengeluaran", "🔐 Login"],
        icons=["file-earmark-plus", "person-check", "cash-coin", "lock"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal"
    )
else:
    selected = option_menu(
        None,
        ["🧾 Order", "✅ Pelanggan", "💸 Pengeluaran", "📈 Report", "📦 Admin", "⚙️ Setting", "🚪 Logout"],
        icons=["file-earmark-plus", "person-check", "cash-coin", "bar-chart-line", "box-seam", "gear", "door-closed"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal"
    )

# ---------------------- ROUTING HALAMAN ----------------------
if not st.session_state.logged_in:
    if selected == "🧾 Order":
        Order.show()
    elif selected == "✅ Pelanggan":
        Pelanggan.show()
    elif selected == "💸 Pengeluaran":
        Expense.show()
    elif selected == "🔐 Login":
        login_form()
else:
    if selected == "🧾 Order":
        Order.show()
    elif selected == "✅ Pelanggan":
        Pelanggan.show()
    elif selected == "💸 Pengeluaran":
        Expense.show()
    elif selected == "📈 Report":
        Report.show()
    elif selected == "📦 Admin":
        Admin.show()
    elif selected == "⚙️ Setting":
        Setting.show()
    elif selected == "🚪 Logout":
        logout_button()
