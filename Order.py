import streamlit as st
import pandas as pd
import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import requests
import urllib.parse

# ================= CONFIG ==================
SPREADSHEET_ID = "1OsnO1xQFniBtEFCvGksR2KKrPt-9idE-w6-poM-wXKU"
SHEET_SERVIS = "Servis"
SHEET_TRANSAKSI = "Transaksi"
SHEET_STOK = "Stok"
CONFIG_FILE = "config.json"
DATA_FILE = "service_data.csv"  # cache lokal

# =============== TELEGRAM NOTIF ===============
TELEGRAM_TOKEN = "7656007924:AAGi1it2M7jE0Sen28myiPhEmYPd1-jsI_Q"
TELEGRAM_CHAT_ID = "6122753506"

def send_telegram_notification(service_data):
    try:
        msg = f"""🔔 *Servis Baru Masuk!*

📦 *Barang:* {service_data.get('Barang')}
⚙️ *Kerusakan:* {service_data.get('Kerusakan')}
📋 *Kelengkapan:* {service_data.get('Kelengkapan')}"""
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("Gagal kirim Telegram:", e)

# =============== AUTH GOOGLE ===============
def authenticate_google():
    creds_dict = st.secrets["gcp_service_account"]
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(credentials)
    return client

def get_worksheet(sheet_name):
    client = authenticate_google()
    sh = client.open_by_key(SPREADSHEET_ID)
    return sh.worksheet(sheet_name)

def ensure_headers(sheet_name, required_headers):
    """
    Pastikan baris header (row 1) di worksheet mengandung required_headers.
    Jika belum ada, tambahkan di akhir baris header yang ada.
    """
    try:
        ws = get_worksheet(sheet_name)
        current = ws.row_values(1)
        if not current:
            # set row1 to required_headers
            ws.insert_row(required_headers, index=1)
            return
        changed = False
        for h in required_headers:
            if h not in current:
                current.append(h)
                changed = True
        if changed:
            # update row 1
            ws.update("1:1", [current])
    except Exception as e:
        print("ensure_headers gagal:", e)

# =============== CONFIG FILE ===============
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Buluh Cina, Panam",
        "telepon": "085172174759"
    }

# =============== REALTIME WIB ===============
@st.cache_data(ttl=300)
def get_cached_internet_date():
    """Ambil tanggal real dari internet (Asia/Jakarta), cache 5 menit."""
    try:
        res = requests.get("https://worldtimeapi.org/api/timezone/Asia/Jakarta", timeout=5)
        if res.status_code == 200:
            data = res.json()
            dt = datetime.datetime.fromisoformat(data["datetime"].replace("Z", "+00:00"))
            return dt.date()
    except Exception as e:
        print("⚠️ Gagal ambil waktu internet:", e)
    return datetime.date.today()

# =============== CACHE CSV ===============
def load_local_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    # default columns include Status Antrian
    return pd.DataFrame(columns=[
        "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan", "No HP",
        "Barang", "Kerusakan", "Kelengkapan", "Status", "Status Antrian",
        "Harga Jasa", "Harga Modal",
        "Jenis Transaksi", "uploaded"
    ])

def save_local_data(df):
    df.to_csv(DATA_FILE, index=False)

# =============== NOMOR NOTA ===============
def get_next_nota_from_sheet(sheet_name, prefix):
    """Ambil nomor nota terakhir dari sheet_name, lalu naikkan +1 (prefix SRV/TRX)."""
    try:
        ws = get_worksheet(sheet_name)
        data = ws.col_values(1)
        if len(data) <= 1:
            return f"{prefix}0000001"
        last_nota = None
        for val in reversed(data):
            if val.strip():
                last_nota = val.strip()
                break
        if last_nota and last_nota.startswith(prefix):
            num = int(last_nota.replace(prefix, ""))
        else:
            num = 0
        return f"{prefix}{num+1:07d}"
    except Exception as e:
        print("Error generate nota:", e)
        return f"{prefix}0000001"

# =============== SPREADSHEET OPS ===============
def append_to_sheet(sheet_name, data: dict):
    """
    Append row to sheet but ensure header contains keys of data first.
    """
    try:
        # ensure headers exist
        required = list(data.keys())
        ensure_headers(sheet_name, required)
        ws = get_worksheet(sheet_name)
        headers = ws.row_values(1)
        # Build row in header order
        row = [data.get(h, "") for h in headers]
        ws.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        # bubble up
        raise

@st.cache_data(ttl=120)
def read_sheet_cached(sheet_name):
    """Cache pembacaan sheet selama 2 menit untuk mempercepat load."""
    ws = get_worksheet(sheet_name)
    return pd.DataFrame(ws.get_all_records())

# =============== SYNC CACHE ===============
def sync_local_cache():
    df = load_local_data()
    if df.empty:
        return
    if "uploaded" not in df.columns:
        df["uploaded"] = False
    not_uploaded = df[df["uploaded"] == False]
    if not not_uploaded.empty:
        st.info(f"🔁 Mengupload ulang {len(not_uploaded)} data tersimpan lokal...")
        for _, row in not_uploaded.iterrows():
            try:
                append_to_sheet(SHEET_SERVIS, row.to_dict())
                df.loc[df["No Nota"] == row["No Nota"], "uploaded"] = True
            except Exception as e:
                st.warning(f"Gagal upload {row['No Nota']}: {e}")
        save_local_data(df)
        st.success("✅ Sinkronisasi cache selesai!")

# =============== ESC/POS PRINT HELPERS ===============
# NOTE: server harus meng-install `python-escpos` (pip install python-escpos)
# and printer must be accessible by server (USB or network).
try:
    from escpos.printer import Usb, Network
    ESC_POS_AVAILABLE = True
except Exception:
    ESC_POS_AVAILABLE = False

def print_escpos_text_lines(lines, cut=True, printer_cfg=None):
    """
    lines: list of strings
    printer_cfg: dict from st.secrets['escpos'] or None
      expected keys:
        - type: 'network' or 'usb'
        - host, port (for network)
        - idVendor, idProduct, in_ep, out_ep (for usb) - id values ints (hex OK)
    """
    if not ESC_POS_AVAILABLE:
        raise RuntimeError("python-escpos not installed on server (pip install python-escpos)")

    p = None
    try:
        if printer_cfg and printer_cfg.get("type") == "network":
            host = printer_cfg.get("host")
            port = int(printer_cfg.get("port", 9100))
            p = Network(host, port=port, timeout=10)
        elif printer_cfg and printer_cfg.get("type") == "usb":
            # vendor/product expected as hex strings like '0x04b8' or ints
            vid = printer_cfg.get("idVendor")
            pid = printer_cfg.get("idProduct")
            in_ep = printer_cfg.get("in_ep", 0x82)
            out_ep = printer_cfg.get("out_ep", 0x01)
            # try convert
            try:
                vid_i = int(str(vid), 0)
                pid_i = int(str(pid), 0)
            except Exception:
                vid_i = int(vid)
                pid_i = int(pid)
            p = Usb(vid_i, pid_i, 0, in_ep=in_ep, out_ep=out_ep, timeout=0)
        else:
            # no config: try network localhost:9100 (common)
            p = Network("127.0.0.1", port=9100, timeout=10)

        # print lines
        for ln in lines:
            p.text(str(ln) + "\n")
        if cut:
            try:
                p.cut()
            except Exception:
                # some network printers don't support cut
                pass
    finally:
        try:
            if p:
                if hasattr(p, 'close'):
                    p.close()
        except Exception:
            pass

def build_servis_print_lines(cfg, service_data, now_dt):
    # Format untuk kertas 57mm x 30mm: keep lines short (about 32-40 chars)
    lines = []
    lines.append(cfg.get("nama_toko", "").center(32))
    lines.append(cfg.get("alamat", ""))
    lines.append("HP: " + cfg.get("telepon", ""))
    lines.append("-" * 32)
    lines.append(f"No Nota : {service_data.get('No Nota')}")
    lines.append(f"Pelanggan: {service_data.get('Nama Pelanggan')}")
    lines.append(f"Tanggal  : {service_data.get('Tanggal Masuk')}")
    lines.append(f"Estimasi : {service_data.get('Estimasi Selesai')}")
    lines.append("-" * 32)
    lines.append(f"Barang   : {service_data.get('Barang')}")
    kerusakan = service_data.get('Kerusakan') or ""
    # wrap long kerusakan into multiple lines (naive)
    for i in range(0, len(kerusakan), 32):
        lines.append(kerusakan[i:i+32])
    kel = service_data.get('Kelengkapan') or ""
    if kel:
        lines.append("Kelengkapan:")
        for i in range(0, len(kel), 32):
            lines.append(kel[i:i+32])
    lines.append("-" * 32)
    harga = service_data.get("Harga Jasa", "")
    lines.append(f"Harga Jasa: {harga}")
    lines.append(f"Status     : {service_data.get('Status')}")
    lines.append("-" * 32)
    lines.append("Terima kasih!")
    lines.append(now_dt.strftime("%d/%m/%Y %H:%M"))
    return lines

def build_barang_print_lines(cfg, transaksi_data, now_dt):
    lines = []
    lines.append(cfg.get("nama_toko", "").center(32))
    lines.append(cfg.get("alamat", ""))
    lines.append("HP: " + cfg.get("telepon", ""))
    lines.append("-" * 32)
    lines.append(f"No Nota : {transaksi_data.get('No Nota')}")
    lines.append(f"Tanggal : {transaksi_data.get('Tanggal')}")
    lines.append(f"Barang  : {transaksi_data.get('Nama Barang')}")
    lines.append(f"Qty     : {transaksi_data.get('Qty')}")
    harga = transaksi_data.get("Harga Jual", 0)
    total = transaksi_data.get("Total", 0)
    lines.append(f"Harga   : Rp {float(harga):,.0f}")
    lines.append(f"Total   : Rp {float(total):,.0f}")
    lines.append("-" * 32)
    lines.append("Terima kasih!")
    lines.append(now_dt.strftime("%d/%m/%Y %H:%M"))
    return lines

# =============== PAGE APP ===============
def show():
    cfg = load_config()
    sync_local_cache()
    st.title("🧾 Transaksi Servis & Barang")

    tab1, tab2 = st.tabs(["🛠️ Servis Baru", "🧰 Transaksi Barang"])

    # --------------------------------------
    # TAB 1 : SERVIS BARU
    # --------------------------------------
    with tab1:
        with st.form("form_service"):
            tanggal_masuk = st.date_input("Tanggal Masuk", value=get_cached_internet_date())
            estimasi = st.date_input("Estimasi Selesai", value=get_cached_internet_date() + datetime.timedelta(days=3))
            nama = st.text_input("Nama Pelanggan", placeholder="King Dion")
            no_hp = st.text_input("Nomor WhatsApp", placeholder="081234567890")
            barang = st.text_input("Nama Barang", placeholder="Laptop ASUS A409")
            kerusakan = st.text_area("Detail Kerusakan", placeholder="Tidak bisa booting, Install Ulang")
            kelengkapan = st.text_area("Kelengkapan", placeholder="Charger, Tas")
            jenis_transaksi = st.radio("Jenis Transaksi:", ["Cash", "Transfer"], horizontal=True, key="jenis_servis")
            harga_jasa = st.number_input("Harga Jasa (opsional)", min_value=0.0, format="%.0f")
            harga_modal = st.number_input("Harga Modal (opsional)", min_value=0.0, format="%.0f")
            submitted = st.form_submit_button("💾 Simpan Servis")

        if submitted:
            if not all([nama, no_hp, barang]):
                st.error("Nama, Nomor HP, dan Barang wajib diisi!")
                return

            nota = get_next_nota_from_sheet(SHEET_SERVIS, "SRV/")
            tanggal_masuk_str = tanggal_masuk.strftime("%d/%m/%Y")
            estimasi_selesai = estimasi.strftime("%d/%m/%Y")

            service_data = {
                "No Nota": nota,
                "Tanggal Masuk": tanggal_masuk_str,
                "Estimasi Selesai": estimasi_selesai,
                "Nama Pelanggan": nama,
                "No HP": no_hp,
                "Barang": barang,
                "Kerusakan": kerusakan,
                "Kelengkapan": kelengkapan,
                "Status": "Cek Dulu",
                "Status Antrian": "Antrian",  # <-- otomatis diisi "Antrian"
                "Harga Jasa": harga_jasa,
                "Harga Modal": harga_modal,
                "Jenis Transaksi": jenis_transaksi,
                "uploaded": False
            }

            df = load_local_data()
            df = pd.concat([df, pd.DataFrame([service_data])], ignore_index=True)

            # pastikan header "Status Antrian" ada di sheet sebelum append
            try:
                append_to_sheet(SHEET_SERVIS, service_data)
                df.loc[df["No Nota"] == nota, "uploaded"] = True
                st.success(f"✅ Servis {barang} berhasil disimpan ke Google Sheet!")
            except Exception as e:
                st.warning(f"⚠️ Gagal upload ke Sheet: {e}. Disimpan lokal dulu.")
            save_local_data(df)

            # === Kirim Notif Telegram ===
            try:
                send_telegram_notification(service_data)
                st.info("🔔 Notifikasi Telegram terkirim.")
            except Exception as e:
                st.warning(f"⚠️ Gagal kirim notifikasi Telegram: {e}")

            # === Buat link Print Preview: buka tab baru berisi HTML dan auto-trigger print() ===
            html_nota = f"""
            <html>
            <head>
            <meta charset="utf-8" />
            <title>Nota Servis {nota}</title>
            <style>
            body {{
              font-family: monospace;
              width: 320px;
              margin: 10px auto;
              text-align: left;
              color: #000;
            }}
            h2 {{ text-align: center; margin-bottom: 4px; }}
            hr {{ border: 1px dashed #000; margin: 8px 0; }}
            p, div {{ margin: 2px 0; white-space: pre-wrap; }}
            .center {{ text-align: center; }}
            </style>
            </head>
            <body onload="window.print()">
            <h2>{cfg['nama_toko']}</h2>
            <div>{cfg['alamat']}<br/>HP: {cfg['telepon']}</div>
            <hr/>
            <div><b>No Nota:</b> {nota}</div>
            <div><b>Pelanggan:</b> {nama}</div>
            <div><b>Tanggal Masuk:</b> {tanggal_masuk_str}</div>
            <div><b>Estimasi Selesai:</b> {estimasi_selesai}</div>
            <hr/>
            <div><b>Barang:</b> {barang}</div>
            <div><b>Kerusakan:</b><br/>{kerusakan}</div>
            <div><b>Kelengkapan:</b><br/>{kelengkapan}</div>
            <hr/>
            <div><b>Harga:</b> (Cek Dulu)</div>
            <div><b>Status:</b> Cek Dulu</div>
            <hr/>
            <div class="center">Terima Kasih 🙏</div>
            <div class="center">{datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
            </body>
            </html>
            """
            data_url = "data:text/html;charset=utf-8," + urllib.parse.quote(html_nota)
            st.markdown(f"[🖨️ Buka Print Preview Nota di Tab Baru]({data_url})", unsafe_allow_html=True)

            # === TOMBOL DOWNLOAD HTML (opsional) ===
            st.download_button("📥 Download Nota (HTML)", data=html_nota,
                               file_name=f"Nota_{nota}.html", mime="text/html")

            # WhatsApp link
            msg = f"""*NOTA ELEKTRONIK*

```{cfg['nama_toko']}```
 {cfg['alamat']}
HP :  {cfg['telepon']}

=======================
*No Nota* : {nota}
*Pelanggan* : {nama}
*Tanggal Masuk* : {tanggal_masuk_str}
*Estimasi Selesai* : {estimasi_selesai}
=======================
Barang : {barang}
Kerusakan : {kerusakan}
Kelengkapan : {kelengkapan}
=======================
*Harga* : (Cek Dulu)
*Status* : Cek Dulu
_Dapatkan Promo Mahasiswa_
=======================

Best Regard,
Admin {cfg['nama_toko']}
Terima Kasih 🙏
"""
            hp = str(no_hp).replace("+", "").replace(" ", "").replace("-", "").strip()
            if hp.startswith("0"): hp = "62" + hp[1:]
            elif not hp.startswith("62"): hp = "62" + hp
            wa_link = f"https://wa.me/{hp}?text={requests.utils.quote(msg)}"
            st.markdown(f"[📲 KIRIM NOTA SERVIS VIA WHATSAPP]({wa_link})", unsafe_allow_html=True)

            # === ESC/POS PRINT SERVIS (langsung, jika tersedia) ===
            now_dt = datetime.datetime.now()
            printer_cfg = None
            # read escpos config from st.secrets if available
            try:
                printer_cfg = st.secrets.get("escpos", None)
            except Exception:
                printer_cfg = None

            if ESC_POS_AVAILABLE:
                try:
                    lines = build_servis_print_lines(cfg, service_data, now_dt)
                    print_escpos_text_lines(lines, cut=True, printer_cfg=printer_cfg)
                    st.info("🖨️ Nota SERVIS dikirim ke printer (ESC/POS).")
                except Exception as e:
                    st.warning(f"⚠️ Gagal cetak ke ESC/POS: {e}")
            else:
                st.warning("📌 Module 'python-escpos' belum terpasang di server. Install dengan: pip install python-escpos")

    # --------------------------------------
    # TAB 2 : TRANSAKSI BARANG
    # --------------------------------------
    with tab2:
        st.subheader("🧰 Penjualan Accessories / Sparepart")

        col_refresh, _ = st.columns([1, 3])
        with col_refresh:
            if st.button("🔄 Refresh Data Stok"):
                st.cache_data.clear()
                st.rerun()

        try:
            stok_df = read_sheet_cached(SHEET_STOK)
        except Exception:
            stok_df = pd.DataFrame(columns=["nama_barang", "modal", "harga_jual", "qty"])

        pilihan_input = st.radio("Pilih Cara Input Transaksi:", ["📦 Pilih dari Stok", "✍️ Input Manual"], horizontal=True)

        # === Pilih dari stok ===
        if pilihan_input == "📦 Pilih dari Stok" and not stok_df.empty:
            nama_barang = st.selectbox("Pilih Barang", stok_df["nama_barang"])
            barang_row = stok_df[stok_df["nama_barang"] == nama_barang].iloc[0]
            modal = float(barang_row.get("modal", 0))
            harga_default = float(barang_row.get("harga_jual", 0))
            stok = int(barang_row.get("qty", 0))
            harga_jual = st.number_input("Harga Jual (boleh ubah manual)", value=harga_default)
            qty = st.number_input("Jumlah Beli", min_value=1, max_value=stok if stok > 0 else 1)
            jenis_transaksi = st.radio("Jenis Transaksi:", ["Cash", "Transfer"], horizontal=True, key="jenis_barang_stok")
            nama_pembeli = st.text_input("Nama Pembeli (opsional)")
            no_hp_pembeli = st.text_input("Nomor WhatsApp Pembeli (opsional)")
            tanggal = get_cached_internet_date()

            if st.button("💾 Simpan Transaksi dari Stok"):
                nota = get_next_nota_from_sheet(SHEET_TRANSAKSI, "TRX/")
                total = harga_jual * qty
                untung = (harga_jual - modal) * qty
                transaksi_data = {
                    "No Nota": nota,
                    "Tanggal": tanggal.strftime("%d/%m/%Y"),
                    "Nama Barang": nama_barang,
                    "Modal": modal,
                    "Harga Jual": harga_jual,
                    "Qty": qty,
                    "Total": total,
                    "Untung": untung,
                    "Pembeli": nama_pembeli,
                    "Jenis Transaksi": jenis_transaksi
                }
                append_to_sheet(SHEET_TRANSAKSI, transaksi_data)

                # 🔥 Kurangi stok otomatis
                try:
                    ws_stok = get_worksheet(SHEET_STOK)
                    stok_data = ws_stok.get_all_records()
                    for i, row in enumerate(stok_data, start=2):
                        if str(row.get("nama_barang", "")).strip() == str(nama_barang).strip():
                            stok_baru = int(row.get("qty", 0)) - int(qty)
                            if stok_baru < 0:
                                stok_baru = 0
                            col_index = list(row.keys()).index("qty") + 1
                            ws_stok.update_cell(i, col_index, stok_baru)
                            break
                except Exception as e:
                    st.warning(f"⚠️ Gagal update stok: {e}")

                st.success(f"✅ Transaksi {nama_barang} tersimpan! Untung: Rp {untung:,.0f}".replace(",", "."))
                msg = f"""NOTA PENJUALAN

💻 *{cfg['nama_toko']}* 💻
{cfg['alamat']}
HP : {cfg['telepon']}

No Nota : {nota}
Tanggal : {tanggal.strftime('%d/%m/%Y')}
Barang  : {nama_barang}
Qty     : {qty}
Harga   : Rp {harga_jual:,.0f}
Total   : Rp {total:,.0f}

Terima kasih sudah berbelanja!
"""
                if no_hp_pembeli:
                    hp = str(no_hp_pembeli).replace("+", "").replace(" ", "").replace("-", "")
                    if hp.startswith("0"): hp = "62" + hp[1:]
                    elif not hp.startswith("62"): hp = "62" + hp
                    wa_link = f"https://wa.me/{hp}?text={requests.utils.quote(msg)}"
                    st.markdown(f"[📲 KIRIM NOTA VIA WHATSAPP]({wa_link})", unsafe_allow_html=True)

                # === ESC/POS PRINT BARANG (langsung, tanpa preview) ===
                now_dt = datetime.datetime.now()
                printer_cfg = None
                try:
                    printer_cfg = st.secrets.get("escpos", None)
                except Exception:
                    printer_cfg = None

                if ESC_POS_AVAILABLE:
                    try:
                        lines = build_barang_print_lines(cfg, transaksi_data, now_dt)
                        print_escpos_text_lines(lines, cut=True, printer_cfg=printer_cfg)
                        st.info("🖨️ Nota BARANG dikirim ke printer (ESC/POS).")
                    except Exception as e:
                        st.warning(f"⚠️ Gagal cetak ke ESC/POS: {e}")
                else:
                    st.warning("📌 Module 'python-escpos' belum terpasang di server. Install dengan: pip install python-escpos")

        # === Input manual ===
        if pilihan_input == "✍️ Input Manual":
            nama_barang_manual = st.text_input("Nama Barang")
            modal_manual = st.number_input("Harga Modal", min_value=0.0, format="%.0f")
            harga_manual = st.number_input("Harga Jual", min_value=0.0, format="%.0f")
            qty_manual = st.number_input("Jumlah Beli", min_value=1)
            jenis_transaksi = st.radio("Jenis Transaksi:", ["Cash", "Transfer"], horizontal=True, key="jenis_barang_manual")
            nama_pembeli_manual = st.text_input("Nama Pembeli (opsional)")
            no_hp_pembeli_manual = st.text_input("Nomor WhatsApp Pembeli (opsional)")
            tanggal_manual = get_cached_internet_date()

            if st.button("💾 Simpan Transaksi Manual"):
                if not nama_barang_manual or harga_manual <= 0:
                    st.error("Nama barang dan harga jual wajib diisi!")
                else:
                    nota = get_next_nota_from_sheet(SHEET_TRANSAKSI, "TRX/")
                    total = harga_manual * qty_manual
                    untung = (harga_manual - modal_manual) * qty_manual
                    transaksi_data = {
                        "No Nota": nota,
                        "Tanggal": tanggal_manual.strftime("%d/%m/%Y"),
                        "Nama Barang": nama_barang_manual,
                        "Modal": modal_manual,
                        "Harga Jual": harga_manual,
                        "Qty": qty_manual,
                        "Total": total,
                        "Untung": untung,
                        "Pembeli": nama_pembeli_manual,
                        "Jenis Transaksi": jenis_transaksi
                    }
                    append_to_sheet(SHEET_TRANSAKSI, transaksi_data)
                    st.success(f"✅ Transaksi manual {nama_barang_manual} tersimpan! Untung: Rp {untung:,.0f}".replace(",", "."))
                    msg = f"""NOTA PENJUALAN

💻 *{cfg['nama_toko']}* 💻
{cfg['alamat']}
HP : {cfg['telepon']}

No Nota : {nota}
Tanggal : {tanggal_manual.strftime('%d/%m/%Y')}
Barang  : {nama_barang_manual}
Qty     : {qty_manual}
Harga   : Rp {harga_manual:,.0f}
Total   : Rp {total:,.0f}

Terima kasih sudah berbelanja!
"""
                    if no_hp_pembeli_manual:
                        hp = str(no_hp_pembeli_manual).replace("+", "").replace(" ", "").replace("-", "")
                        if hp.startswith("0"): hp = "62" + hp[1:]
                        elif not hp.startswith("62"): hp = "62" + hp
                        wa_link = f"https://wa.me/{hp}?text={requests.utils.quote(msg)}"
                        st.markdown(f"[📲 KIRIM NOTA VIA WHATSAPP]({wa_link})", unsafe_allow_html=True)

                    # === ESC/POS PRINT BARANG (langsung, tanpa preview) ===
                    now_dt = datetime.datetime.now()
                    printer_cfg = None
                    try:
                        printer_cfg = st.secrets.get("escpos", None)
                    except Exception:
                        printer_cfg = None

                    if ESC_POS_AVAILABLE:
                        try:
                            lines = build_barang_print_lines(cfg, transaksi_data, now_dt)
                            print_escpos_text_lines(lines, cut=True, printer_cfg=printer_cfg)
                            st.info("🖨️ Nota BARANG dikirim ke printer (ESC/POS).")
                        except Exception as e:
                            st.warning(f"⚠️ Gagal cetak ke ESC/POS: {e}")
                    else:
                        st.warning("📌 Module 'python-escpos' belum terpasang di server. Install dengan: pip install python-escpos")

if __name__ == "__main__":
    show()
