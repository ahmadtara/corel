# pelanggan.py (v3.3) - Lightweight, Responsive Tabs + Statistik + Kirim WA Otomatis
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

# ------------------- READ SHEET (cached) -------------------
@st.cache_data(ttl=120)
def read_sheet_once(sheet_name):
    """Membaca Google Sheet. Decorated dengan st.cache_data untuk mengurangi panggilan."""
    ws = get_worksheet(sheet_name)
    df = pd.DataFrame(ws.get_all_records())
    return df

def load_df():
    """Load dari session cache atau ambil baru jika belum ada."""
    if "df_cache" not in st.session_state:
        try:
            st.session_state.df_cache = read_sheet_once(SHEET_SERVIS)
        except Exception as e:
            st.warning(f"Gagal membaca sheet: {e}")
            st.session_state.df_cache = pd.DataFrame()
    return st.session_state.df_cache.copy()

def reload_df():
    """Force reload dari Google Sheet dan simpan ke session_state."""
    try:
        st.session_state.df_cache = read_sheet_once(SHEET_SERVIS)
    except Exception as e:
        st.warning(f"Gagal reload sheet: {e}")
        st.session_state.df_cache = pd.DataFrame()

# ------------------- UPDATE SHEET -------------------
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
.stat-card { padding:14px; border-radius:10px; color:#fff; text-align:center; font-weight:700; }
.card-orange{ background:#FFA500 } .card-blue{ background:#0A84FF } .card-green{ background:#34C759 } .card-red{ background:#FF3B30 }
.small-muted { color:#666; font-size:13px; }
.limit-note { font-size:13px; color:#666; margin-bottom:6px; }
</style>
"""
st.markdown(STYLE, unsafe_allow_html=True)

# ------------------- RENDER UTIL FUNCTIONS -------------------
def prepare_df_for_view(df):
    # Ensure important columns exist
    for col in ["Tanggal Masuk","No Nota","Nama Pelanggan","No HP","Barang","Harga Jasa","Harga Modal","Jenis Transaksi","Status Antrian"]:
        if col not in df.columns:
            df[col] = ""
    df["Status Antrian"] = df["Status Antrian"].fillna("").astype(str).str.strip()
    df["Tanggal_parsed"] = pd.to_datetime(df["Tanggal Masuk"], errors="coerce", dayfirst=True)
    return df

def render_card_entry(row, cfg, active_status):
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

        # actions
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
                    # update local cache quickly and then rerun to refresh UI
                    reload_df()
                    kirim_wa_pelanggan(nama, no_nota, no_hp, hj_str, jenis_transaksi, cfg['nama_toko'])
                    st.success(f"Nota {no_nota} dipindah ke 'Siap Diambil' dan WA terbuka.")
                    st.rerun()

        elif status_antrian.lower() == "siap diambil" and active_status == "Siap Diambil":
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✔️ Selesai", key=f"selesai_{no_nota}"):
                    ok = update_sheet_row_by_nota(SHEET_SERVIS, no_nota, {"Status Antrian": "Selesai"})
                    if ok:
                        reload_df()
                        st.success(f"Nota {no_nota} → Selesai")
                        st.rerun()
            with c2:
                if st.button("❌ Batal", key=f"batal_{no_nota}"):
                    ok = update_sheet_row_by_nota(SHEET_SERVIS, no_nota, {"Status Antrian": "Batal"})
                    if ok:
                        reload_df()
                        st.warning(f"Nota {no_nota} → Batal")
                        st.rerun()
        else:
            st.info(f"📌 Status Antrian: {status_antrian or 'Antrian'}")

# ------------------- APP -------------------
def show():
    cfg = load_config()
    st.title("📱 Pelanggan — Status Antrian & Kirim WA")

    # reload control
    colr, colr2 = st.columns([1,4])
    with colr:
        if st.button("🔄 Reload Data Sheet"):
            # clear cache and reload
            try:
                read_sheet_once.clear()
            except Exception:
                pass
            reload_df()
            st.rerun()
    with colr2:
        st.write("")  # spacing

    # load df cached in session
    df = load_df()

    # prepare dataframe
    df = prepare_df_for_view(df)

    # statistics (use counts from prepared df)
    total_antrian = len(df[(df["Status Antrian"] == "") | (df["Status Antrian"].str.lower() == "antrian")])
    total_siap = len(df[df["Status Antrian"].str.lower() == "siap diambil"])
    total_selesai = len(df[df["Status Antrian"].str.lower() == "selesai"])
    total_batal = len(df[df["Status Antrian"].str.lower() == "batal"])

    s1, s2, s3, s4 = st.columns([1.1,1.1,1.1,1.1], gap="large")
    with s1:
        st.markdown(f'<div class="stat-card card-orange">🕒<br><div style="font-size:14px">Antrian</div><div style="font-size:18px;margin-top:6px">{total_antrian}</div></div>', unsafe_allow_html=True)
    with s2:
        st.markdown(f'<div class="stat-card card-blue">📢<br><div style="font-size:14px">Siap Diambil</div><div style="font-size:18px;margin-top:6px">{total_siap}</div></div>', unsafe_allow_html=True)
    with s3:
        st.markdown(f'<div class="stat-card card-green">✅<br><div style="font-size:14px">Selesai</div><div style="font-size:18px;margin-top:6px">{total_selesai}</div></div>', unsafe_allow_html=True)
    with s4:
        st.markdown(f'<div class="stat-card card-red">❌<br><div style="font-size:14px">Batal</div><div style="font-size:18px;margin-top:6px">{total_batal}</div></div>', unsafe_allow_html=True)

    st.markdown("")  # spacer

    # TABS (Streamlit native -> instant)
    tab_antrian, tab_siap, tab_selesai, tab_batal = st.tabs([
        "🕒 Antrian",
        "📢 Siap Diambil",
        "✅ Selesai",
        "❌ Batal"
    ])

    # common filter + search (apply to each tab's df_view)
    with st.expander("🔧 Filter & Pencarian", expanded=False):
        today = get_waktu_jakarta().date()
        filter_tipe = st.selectbox("Filter Waktu", ["Semua", "Per Hari", "Per Bulan"], index=0)
        if filter_tipe == "Per Hari":
            tanggal_pilih = st.date_input("Pilih Tanggal:", today)
        elif filter_tipe == "Per Bulan":
            tahun = st.number_input("Tahun", value=today.year, step=1)
            bulan = st.number_input("Bulan (1–12)", value=today.month, min_value=1, max_value=12, step=1)
        q = st.text_input("Cari Nama atau No Nota")

    # build filters function
    def apply_filters(df_in):
        df_out = df_in.copy()
        if filter_tipe == "Per Hari":
            df_out = df_out[df_out["Tanggal_parsed"].dt.date == tanggal_pilih]
        elif filter_tipe == "Per Bulan":
            df_out = df_out[(df_out["Tanggal_parsed"].dt.year == tahun) & (df_out["Tanggal_parsed"].dt.month == bulan)]
        if q and str(q).strip():
            q_lower = str(q).strip().lower()
            df_out = df_out[df_out["Nama Pelanggan"].astype(str).str.lower().str.contains(q_lower) | df_out["No Nota"].astype(str).str.lower().str.contains(q_lower)]
        return df_out

    # helper to show tab content with limit / pagination
    def show_tab(df_tab, active_status_label):
        df_tab = apply_filters(df_tab)
        st.markdown(f"Menampilkan **{len(df_tab)} data** untuk status **{active_status_label}**.")
        if len(df_tab) == 0:
            st.info(f"📭 Belum ada data untuk status **{active_status_label}**.")
            return

        # pagination: tampilkan 25 per halaman
        per_page = 25
        total = len(df_tab)
        pages = (total - 1) // per_page + 1
        page = st.number_input(
            f"Halaman ({active_status_label})",
            min_value=1,
            max_value=pages,
            value=1,
            step=1,
            format="%d",
            key=f"page_{active_status_label}"
        )

        start = (page - 1) * per_page
        end = start + per_page
        df_slice = df_tab.iloc[start:end].reset_index(drop=True)

        st.markdown(f"<div class='limit-note'>Menampilkan baris {start+1}–{min(end, total)} dari {total}</div>", unsafe_allow_html=True)

        for idx, row in df_slice.iterrows():
            render_card_entry(row, cfg, active_status_label)

    # tab: Antrian
    with tab_antrian:
        df_tab = df[(df["Status Antrian"] == "") | (df["Status Antrian"].str.lower() == "antrian")]
        show_tab(df_tab, "Antrian")

    with tab_siap:
        df_tab = df[df["Status Antrian"].str.lower() == "siap diambil"]
        show_tab(df_tab, "Siap Diambil")

    with tab_selesai:
        df_tab = df[df["Status Antrian"].str.lower() == "selesai"]
        show_tab(df_tab, "Selesai")

    with tab_batal:
        df_tab = df[df["Status Antrian"].str.lower() == "batal"]
        show_tab(df_tab, "Batal")

# run app
if __name__ == "__main__":
    show()
