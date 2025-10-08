import streamlit as st

def show():
    # === Konfigurasi Halaman ===
    st.set_page_config(page_title="Setting", layout="centered")

    # === Header / Title ===
    st.markdown("""
        <style>
        .title {
            text-align: center;
            color: #E53935;
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #888;
            font-size: 14px;
            margin-bottom: 30px;
        }
        .card {
            background-color: #fff;
            border-radius: 16px;
            padding: 18px 22px;
            margin-bottom: 16px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        }
        .card h4 {
            color: #333;
            margin-bottom: 8px;
            font-size: 16px;
        }
        .card small {
            color: #777;
            font-size: 13px;
        }
        .switch {
            float: right;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='title'>⚙️ Pengaturan</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Atur tampilan, mode, dan fitur aplikasi</div>", unsafe_allow_html=True)

    # === Pengaturan Tampilan ===
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 🎨 Tampilan")
    dark_mode = st.toggle("Mode Gelap", key="dark_mode")
    compact_mode = st.toggle("Mode Kompak", key="compact_mode")
    st.markdown("</div>", unsafe_allow_html=True)

    # === Pengaturan Aplikasi ===
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### ⚡ Kinerja")
    auto_refresh = st.toggle("Auto-refresh Data", key="auto_refresh")
    optimize_speed = st.toggle("Optimasi Kecepatan", key="optimize_speed")
    st.markdown("</div>", unsafe_allow_html=True)

    # === Pengaturan Printer / Nota ===
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 🧾 Printer & Nota")
    printer_name = st.text_input("Nama Printer", value="EPSON TM-T82")
    nota_footer = st.text_area("Catatan di bawah nota", "Terima kasih telah berbelanja 🙏")
    st.markdown("</div>", unsafe_allow_html=True)

    # === Pengaturan Akun ===
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("### 👤 Akun Kasir")
    username = st.text_input("Nama Kasir", value="Kasir 1")
    password = st.text_input("PIN Keamanan", type="password", value="1234")
    st.markdown("</div>", unsafe_allow_html=True)

    # === Simpan Perubahan ===
    if st.button("💾 Simpan Pengaturan", use_container_width=True):
        st.success("✅ Pengaturan berhasil disimpan!")
        st.balloons()

    # === Footer versi info ===
    st.markdown("""
        <hr style="margin-top:25px;margin-bottom:10px;">
        <div style='text-align:center;color:#aaa;font-size:12px;'>
            Versi Aplikasi <b>v1.0.0</b> | Edobi Style UI 🎨<br>
            © 2025 KasirApp by ChatGPT
        </div>
    """, unsafe_allow_html=True)
