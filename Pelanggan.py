# pelanggan.py (v3.2) - Modern Tab Menu (stable) + Statistik + Kirim WA Otomatis
import streamlit as st
import pandas as pd
import datetime
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse

# ------------------- PAGE CONFIG -------------------
st.set_page_config(page_title="Pelanggan — Status Antrian", page_icon="📱", layout="wide")

# ------------------- CONFIG -------------------
CONFIG_FILE = "config.json"
SPREADSHEET_ID = "1OsnO1xQFniBtEFCvGksR2KKrPt-9idE-w6-poM-wXKU"
SHEET_SERVIS = "Servis"

# ------------------- AUTH GOOGLE -------------------
def authenticate_google():
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(credentials)
    return client

def get_worksheet(sheet_name):
    client = authenticate_google()
    sh = client.open_by_key(SPREADSHEET_ID)
    return sh.worksheet(sheet_name)

# ------------------- CACHE READ SHEET -------------------
@st.cache_data(ttl=120)
def read_sheet(sheet_name):
    try:
        ws = get_worksheet(sheet_name)
        df = pd.DataFrame(ws.get_all_records())
        return df
    except Exception as e:
        st.warning(f"Gagal membaca sheet {sheet_name}: {e}")
        return pd.DataFrame()

def update_sheet_row_by_nota(sheet_name, nota, updates: dict):
    try:
        ws = get_worksheet(sheet_name)
        cell = None
        try:
            cell = ws.find(str(nota))
        except Exception:
            cell = None

        if not cell:
            headers = ws.row_values(1)
            if "No Nota" in headers:
                no_nota_col = headers.index("No Nota") + 1
                column_vals = ws.col_values(no_nota_col)
                for i, v in enumerate(column_vals, start=1):
                    if str(v).strip() == str(nota).strip():
                        cell = gspread.Cell(i, no_nota_col, v)
                        break

        if not cell:
            raise ValueError(f"Tidak ditemukan nota {nota}")

        row = cell.row
        headers = ws.row_values(1)
        for k, v in updates.items():
            if k in headers:
                col = headers.index(k) + 1
                ws.update_cell(row, col, v)
        return True
    except Exception as e:
        st.error(f"Gagal update sheet {sheet_name} untuk nota {nota}: {e}")
        return False

# ------------------- UTIL -------------------
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"nama_toko":"Capslock Komputer","alamat":"Jl. Buluh Cina, Panam","telepon":"0851-7217-4759"}

def format_rp(n):
    try:
        nnum = int(n)
        return f"Rp {nnum:,.0f}".replace(",", ".")
    except:
        return str(n)

def get_waktu_jakarta():
    tz = datetime.timezone(datetime.timedelta(hours=7))
    return datetime.datetime.now(tz)

def kirim_wa_pelanggan(nama, no_nota, no_hp, hj_str, jenis_transaksi, nama_toko):
    msg = f"""Assalamualaikum {nama},

Unit anda dengan nomor nota *{no_nota}* sudah selesai dan siap untuk diambil.

Total Biaya Servis: *{hj_str if hj_str else '(Cek Dulu)'}*
Pembayaran: *{jenis_transaksi}*

Terima Kasih 🙏
{nama_toko}"""
    no_hp_clean = str(no_hp).replace("+","").replace(" ","").replace("-","").strip()
    if no_hp_clean.startswith("0"):
        no_hp_clean = "62" + no_hp_clean[1:]
    elif not no_hp_clean.startswith("62"):
        no_hp_clean = "62" + no_hp_clean
    if no_hp_clean.isdigit() and len(no_hp_clean) >= 10:
        wa_link = f"https://wa.me/{no_hp_clean}?text={urllib.parse.quote(msg)}"
        js = f"""<script>
            setTimeout(function(){{ window.open("{wa_link}", "_blank"); }}, 150);
        </script>"""
        st.markdown(js, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Nomor HP pelanggan kosong atau tidak valid.")

# ------------------- STYLES -------------------
STYLE = """
<style>
.tab-menu { display:flex; gap:28px; border-bottom: 1.5px solid #eee; padding-bottom: 6px; margin-bottom: 18px; }
.tab-btn {
  background: transparent;
  border: none;
  font-size: 15px;
  color: #555;
  font-weight: 600;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: 6px;
}
.tab-btn:hover { color: #111; background:#f7f7f7; }
.tab-active { color:#e53935; border-bottom:3px solid #e53935; }
.stat-card { padding:16px; border-radius:10px; color:#fff; text-align:center; font-weight:700; }
.card-orange{ background:#FFA500; } .card-blue{ background:#0A84FF; } .card-green{ background:#34C759; } .card-red{ background:#FF3B30; }
</style>
"""
st.markdown(STYLE, unsafe_allow_html=True)

# ------------------- APP -------------------
def show():
    cfg = load_config()
    st.title("📱 Pelanggan — Status Antrian & Kirim WA")

    # reload
    if st.button("🔄 Reload Data Sheet"):
        st.cache_data.clear()
        st.experimental_rerun()

    # read
    df = read_sheet(SHEET_SERVIS)
    if df.empty:
        st.info("Belum ada data di sheet Servis.")
        return

    # ensure columns
    for col in ["Tanggal Masuk","No Nota","Nama Pelanggan","No HP","Barang","Harga Jasa","Harga Modal","Jenis Transaksi","Status Antrian"]:
        if col not in df.columns:
            df[col] = ""

    df["Status Antrian"] = df["Status Antrian"].fillna("").astype(str).str.strip()

    # statistics cards
    total_antrian = len(df[(df["Status Antrian"] == "") | (df["Status Antrian"].str.lower() == "antrian")])
    total_siap = len(df[df["Status Antrian"].str.lower() == "siap diambil"])
    total_selesai = len(df[df["Status Antrian"].str.lower() == "selesai"])
    total_batal = len(df[df["Status Antrian"].str.lower() == "batal"])

    sc1, sc2, sc3, sc4 = st.columns([1.1,1.1,1.1,1.1], gap="large")
    with sc1:
        st.markdown(f'<div class="stat-card card-orange">🕒<br>Antrian<br><div style="font-size:18px;margin-top:6px">{total_antrian}</div></div>', unsafe_allow_html=True)
    with sc2:
        st.markdown(f'<div class="stat-card card-blue">📢<br>Siap Diambil<br><div style="font-size:18px;margin-top:6px">{total_siap}</div></div>', unsafe_allow_html=True)
    with sc3:
        st.markdown(f'<div class="stat-card card-green">✅<br>Selesai<br><div style="font-size:18px;margin-top:6px">{total_selesai}</div></div>', unsafe_allow_html=True)
    with sc4:
        st.markdown(f'<div class="stat-card card-red">❌<br>Batal<br><div style="font-size:18px;margin-top:6px">{total_batal}</div></div>', unsafe_allow_html=True)

    st.markdown("")  # spacing

    # TAB BAR using buttons (stable)
    tabs = [("Antrian","🕒"), ("Siap Diambil","📢"), ("Selesai","✅"), ("Batal","❌")]
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Antrian"

    # Render tab buttons with spacing and active style
    tab_cols = st.columns(len(tabs))
    for i, (label, icon) in enumerate(tabs):
        is_active = (st.session_state.active_tab == label)
        btn_label = f"{icon}  {label}"
        if is_active:
            if tab_cols[i].button(btn_label, key=f"tab_{label}"):
                # keep active if re-click
                st.session_state.active_tab = label
            # add a visual underline via markdown (since button can't have class easily)
            tab_cols[i].markdown(f"<div style='height:4px;background:#e53935;border-radius:2px;margin-top:6px'></div>", unsafe_allow_html=True)
        else:
            if tab_cols[i].button(btn_label, key=f"tab_{label}"):
                st.session_state.active_tab = label

    active_status = st.session_state.active_tab

    # -------- FILTER AREA --------
    st.markdown("### 📅 Filter Data")
    today = get_waktu_jakarta().date()
    filter_tipe = st.radio("Filter:", ["Semua", "Per Hari", "Per Bulan"], horizontal=True)

    df["Tanggal_parsed"] = pd.to_datetime(df["Tanggal Masuk"], errors="coerce", dayfirst=True)

    if filter_tipe == "Per Hari":
        tanggal_pilih = st.date_input("Pilih Tanggal:", today)
        df = df[df["Tanggal_parsed"].dt.date == tanggal_pilih]
    elif filter_tipe == "Per Bulan":
        tahun = st.number_input("Tahun", value=today.year, step=1)
        bulan = st.number_input("Bulan (1–12)", value=today.month, min_value=1, max_value=12, step=1)
        df = df[(df["Tanggal_parsed"].dt.year == tahun) & (df["Tanggal_parsed"].dt.month == bulan)]

    # search
    st.markdown("### 🔎 Cari Pelanggan")
    q = st.text_input("Cari berdasarkan Nama atau No Nota (ketik lalu Enter)")
    if q.strip():
        q_lower = q.strip().lower()
        df = df[df["Nama Pelanggan"].astype(str).str.lower().str.contains(q_lower) | df["No Nota"].astype(str).str.lower().str.contains(q_lower)]

    # filter by active_status
    if active_status == "Antrian":
        df_view = df[(df["Status Antrian"] == "") | (df["Status Antrian"].str.lower() == "antrian")]
    else:
        df_view = df[df["Status Antrian"].str.lower() == active_status.lower()]

    st.markdown(f"Menampilkan **{len(df_view)} data** untuk status **{active_status}**.")

    # if empty, show friendly message
    if len(df_view) == 0:
        st.info(f"📭 Belum ada data untuk status **{active_status}**.")
        return

    # show entries
    df_view = df_view.reset_index(drop=True)
    for idx, row in df_view.iterrows():
        no_nota = row.get("No Nota", "")
        nama = row.get("Nama Pelanggan", "")
        barang = row.get("Barang", "")
        no_hp = row.get("No HP", "")
        status_antrian = (row.get("Status Antrian") or "").strip()
        harga_jasa_existing = row.get("Harga Jasa", "")
        harga_modal_existing = row.get("Harga Modal", "")
        jenis_existing = row.get("Jenis Transaksi") if pd.notna(row.get("Jenis Transaksi")) else "Cash"

        header_label = f"🧾 {no_nota} — {nama} — {barang} ({status_antrian or 'Antrian'})"
        with st.expander(header_label, expanded=False):
            left, right = st.columns([2,1])
            with left:
                st.write(f"📅 **Tanggal Masuk:** {row.get('Tanggal Masuk','')}")
                st.write(f"👤 **Nama:** {nama}")
                st.write(f"📞 **No HP:** {no_hp}")
                st.write(f"🧰 **Barang:** {barang}")
                st.write(f"📝 **Keterangan Status:** {status_antrian or 'Antrian'}")
            with right:
                harga_jasa_input = st.text_input("Harga Jasa (Rp)", value=str(harga_jasa_existing).replace("Rp","").replace(".",""), key=f"hj_{no_nota}")
                harga_modal_input = st.text_input("Harga Modal (Rp)", value=str(harga_modal_existing).replace("Rp","").replace(".",""), key=f"hm_{no_nota}")
                jenis_transaksi = st.radio("Jenis Transaksi:", ["Cash","Transfer"], index=0 if str(jenis_existing).lower()!="transfer" else 1, key=f"jenis_{no_nota}", horizontal=True)

            # parse safely
            try:
                hj_num = int(str(harga_jasa_input).replace(".","").replace(",","").strip()) if str(harga_jasa_input).strip() else 0
            except:
                hj_num = 0
            try:
                hm_num = int(str(harga_modal_input).replace(".","").replace(",","").strip()) if str(harga_modal_input).strip() else 0
            except:
                hm_num = 0
            hj_str = format_rp(hj_num) if hj_num else ""
            hm_str = format_rp(hm_num) if hm_num else ""

            # actions based on status and active tab
            if (status_antrian == "" or status_antrian.lower() == "antrian") and active_status == "Antrian":
                if st.button("✅ Siap Diambil (Kirim WA)", key=f"ambil_{no_nota}"):
                    updates = {
                        "Harga Jasa": hj_str,
                        "Harga Modal": hm_str,
                        "Jenis Transaksi": jenis_transaksi,
                        "Status Antrian": "Siap Diambil"
                    }
                    ok = update_sheet_row_by_nota(SHEET_SERVIS, no_nota, updates)
                    if ok:
                        kirim_wa_pelanggan(nama, no_nota, no_hp, hj_str, jenis_transaksi, cfg['nama_toko'])
                        st.success(f"Nota {no_nota} dipindah ke 'Siap Diambil' dan WA terbuka.")
                        st.experimental_rerun()

            elif status_antrian.lower() == "siap diambil" and active_status == "Siap Diambil":
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✔️ Selesai", key=f"selesai_{no_nota}"):
                        ok = update_sheet_row_by_nota(SHEET_SERVIS, no_nota, {"Status Antrian": "Selesai"})
                        if ok:
                            st.success(f"Nota {no_nota} → Selesai")
                            st.experimental_rerun()
                with c2:
                    if st.button("❌ Batal", key=f"batal_{no_nota}"):
                        ok = update_sheet_row_by_nota(SHEET_SERVIS, no_nota, {"Status Antrian": "Batal"})
                        if ok:
                            st.warning(f"Nota {no_nota} → Batal")
                            st.experimental_rerun()
            else:
                st.info(f"📌 Status Antrian: {status_antrian or 'Antrian'}")

# run
if __name__ == "__main__":
    show()
