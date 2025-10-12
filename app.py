# ========================== app.py (v2.0) - Dengan Login Admin ==========================
import streamlit as st
from streamlit_option_menu import option_menu
import Order, Report, Setting, Admin, Expense, Pelanggan

# ---------------------- KONFIGURASI HALAMAN ----------------------
st.set_page_config(
    page_title="Servis Center",
    page_icon="🧾",
    layout="centered"
)

# ---------------------- KONFIGURASI LOGIN ----------------------
# Username dan password bisa kamu ubah di sini
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

# Inisialisasi status login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------------- FUNGSI LOGIN ----------------------
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

# ---------------------- FUNGSI LOGOUT ----------------------
def logout_button():
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.success("Berhasil logout.")
        st.rerun()

# ---------------------- SIDEBAR MENU ----------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1048/1048953.png", width=80)
    st.markdown("## 📱 Capslock Komputer")

    # Jika belum login → tampilkan menu user biasa saja
    if not st.session_state.logged_in:
        selected = option_menu(
            "Menu Utama",
            [
                "🧾 Order",
                "✅ Pelanggan",
                "💸 Pengeluaran",
                "🔐 Login Admin"  # tombol login
            ],
            icons=[
                "file-earmark-plus",
                "person-check",
                "cash-coin",
                "lock"
            ],
            menu_icon="pc-display",
            default_index=0
        )
    else:
        selected = option_menu(
            "Menu Admin",
            [
                "🧾 Order",
                "✅ Pelanggan",
                "💸 Pengeluaran",
                "📈 Report",
                "📦 Admin",
                "⚙️ Setting",
                "🚪 Logout"
            ],
            icons=[
                "file-earmark-plus",
                "person-check",
                "cash-coin",
                "bar-chart-line",
                "box-seam",
                "gear",
                "door-closed"
            ],
            menu_icon="pc-display",
            default_index=0
        )

# ---------------------- ROUTING HALAMAN ----------------------
if not st.session_state.logged_in:
    if selected == "🧾 Order":
        Order.show()
    elif selected == "✅ Pelanggan":
        Pelanggan.show()
    elif selected == "💸 Pengeluaran":
        Expense.show()
    elif selected == "🔐 Login Admin":
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
