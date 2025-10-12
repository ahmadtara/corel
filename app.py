# ========================== app.py (v3.0 - Bottom Nav Style Android) ==========================
import streamlit as st
import streamlit.components.v1 as components
import Order, Report, Setting, Admin, Expense, Pelanggan

# ---------------------- CONFIG ----------------------
st.set_page_config(page_title="Servis Center", page_icon="🧾", layout="centered")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "menu" not in st.session_state:
    st.session_state.menu = "home"

# ---------------------- LOGIN ----------------------
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

# ---------------------- LOGOUT ----------------------
def logout_button():
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.success("Berhasil logout.")
        st.rerun()

# ---------------------- RENDER PAGE ----------------------
menu = st.session_state.menu

if menu == "home":
    st.markdown("## 🧺 Max Wash Laundry\nJl Kemang Utara No 40 Jakarta Selatan")
    st.metric("Omset Hari Ini", "Rp 0")
    st.columns(3)
    st.button("Transaksi Baru", use_container_width=True, type="primary")
    st.button("Pengeluaran", use_container_width=True)
elif menu == "order":
    Order.show()
elif menu == "report":
    Report.show()
elif menu == "setting":
    if not st.session_state.logged_in:
        login_form()
    else:
        Setting.show()
        logout_button()

# ---------------------- BOTTOM NAVIGATION ----------------------
st.markdown(
    """
    <style>
    .bottom-nav {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        height: 70px;
        background-color: white;
        border-top: 1px solid #ddd;
        display: flex;
        justify-content: space-around;
        align-items: center;
        box-shadow: 0 -2px 8px rgba(0,0,0,0.1);
        z-index: 9999;
    }
    .nav-item {
        text-align: center;
        flex: 1;
        color: #888;
        font-size: 12px;
    }
    .nav-item.active {
        color: #e74c3c;
    }
    .nav-item i {
        font-size: 22px;
        display: block;
        margin-bottom: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

components.html(
    f"""
    <div class="bottom-nav">
        <div class="nav-item {'active' if menu=='home' else ''}" onclick="parent.postMessage({{menu: 'home'}}, '*')">
            <i class="bi bi-house-fill"></i>Home
        </div>
        <div class="nav-item {'active' if menu=='order' else ''}" onclick="parent.postMessage({{menu: 'order'}}, '*')">
            <i class="bi bi-bag-fill"></i>Order
        </div>
        <div class="nav-item {'active' if menu=='report' else ''}" onclick="parent.postMessage({{menu: 'report'}}, '*')">
            <i class="bi bi-graph-up"></i>Report
        </div>
        <div class="nav-item {'active' if menu=='setting' else ''}" onclick="parent.postMessage({{menu: 'setting'}}, '*')">
            <i class="bi bi-gear-fill"></i>Setting
        </div>
    </div>

    <script>
    window.addEventListener("message", (event) => {{
        const menu = event.data.menu;
        if (menu) {{
            window.parent.streamlitSend({{ type: "set_menu", menu: menu }});
        }}
    }});
    </script>
    """,
    height=80,
)

# ---------------------- HANDLE NAVIGATION ----------------------
def handle_js_event(event):
    if event["type"] == "set_menu":
        st.session_state.menu = event["menu"]
        st.experimental_rerun()
