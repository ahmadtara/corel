import streamlit as st
import pandas as pd
import requests
import datetime
import base64
import json

# ================== KONFIGURASI GITHUB ==================
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]        # "username/nama-repo"
GITHUB_FILE = st.secrets["GITHUB_FILE"]        # "service_data.csv"
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")

# ================== FUNGSI GITHUB ==================
def github_get_file():
    """Ambil isi file CSV dari GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        content = r.json()
        data = base64.b64decode(content["content"]).decode("utf-8")
        sha = content["sha"]
        return data, sha
    else:
        st.error(f"Gagal mengambil file GitHub: {r.text}")
        return None, None

def github_update_file(new_content, sha):
    """Update file CSV ke GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    message = f"Update laporan servis - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
    data = {
        "message": message,
        "content": content,
        "branch": GITHUB_BRANCH,
        "sha": sha
    }
    r = requests.put(url, headers=headers, data=json.dumps(data))
    return r.status_code in [200, 201]

# ================== DATA ==================
def load_data():
    data, sha = github_get_file()
    if data:
        df = pd.read_csv(pd.compat.StringIO(data))
        if "Harga Modal" not in df.columns:
            df["Harga Modal"] = ""
        return df, sha
    else:
        return pd.DataFrame(columns=[
            "No Nota", "Tanggal Masuk", "Estimasi Selesai", "Nama Pelanggan", "No HP",
            "Barang", "Kerusakan", "Kelengkapan", "Status", "Harga Jasa", "Harga Modal"
        ]), None

def save_data(df, sha):
    csv_content = df.to_csv(index=False)
    return github_update_file(csv_content, sha)

# ================== KONFIG TOKO ==================
def load_config():
    return {
        "nama_toko": "Capslock Komputer",
        "alamat": "Jl. Buluh Cina, Panam",
        "telepon": "0851-7217-4759"
    }

# ================== PAGE ==================
def show():
    cfg = load_config()
    st.title("📊 Laporan Servis")

    df, sha = load_data()
    if df.empty:
        st.info("Belum ada data servis.")
        return

    # Konversi tanggal
    df["Tanggal Masuk"] = pd.to_datetime(df["Tanggal Masuk"], errors="coerce")

    # ================== FILTER BULAN ==================
    st.sidebar.header("📅 Filter Laporan per Bulan")
    bulan_unik = sorted(df["Tanggal Masuk"].dropna().dt.to_period("M").unique())
    if len(bulan_unik) > 0:
        pilih_bulan = st.sidebar.selectbox(
            "Pilih Bulan:",
            options=["Semua Bulan"] + [str(b) for b in bulan_unik],
            index=0
        )
        if pilih_bulan != "Semua Bulan":
            df = df[df["Tanggal Masuk"].dt.to_period("M") == pd.Period(pilih_bulan)]

    # ================== HITUNG REKAP ==================
    def parse_rupiah(s):
        try:
            return int(str(s).replace("Rp", "").replace(".", "").strip())
        except:
            return 0

    total_jasa = df["Harga Jasa"].apply(parse_rupiah).sum()
    total_modal = df["Harga Modal"].apply(parse_rupiah).sum()
    total_untung = total_jasa - total_modal

    st.metric("💰 Total Modal", f"Rp {total_modal:,}".replace(",", "."))
    st.metric("💵 Total Jasa", f"Rp {total_jasa:,}".replace(",", "."))
    st.metric("📈 Total Untung", f"Rp {total_untung:,}".replace(",", "."))

    # ================== TABEL ==================
    st.dataframe(df, use_container_width=True)
    st.divider()
    st.subheader("📱 Klik Pelanggan Untuk Kirim WA Otomatis")

    for i, row in df.iterrows():
        with st.expander(f"{row['Nama Pelanggan']} - {row['Barang']} ({row['Status']})"):
            # ---------------- HARGA MODAL ----------------
            modal_input = st.text_input(
                "Harga Modal (tidak dikirim ke WA)",
                value=str(row["Harga Modal"]).replace("Rp ", "").replace(".", "") if pd.notna(row["Harga Modal"]) else "",
                key=f"modal_{i}"
            )

            # ---------------- HARGA JASA ----------------
            harga_input = st.text_input(
                "Harga Jasa (akan dikirim ke WA)",
                value=str(row["Harga Jasa"]).replace("Rp ", "").replace(".", "") if pd.notna(row["Harga Jasa"]) else "",
                key=f"harga_{i}"
            )

            if harga_input.strip():
                # Format harga jasa
                try:
                    harga_num = int(harga_input.replace("Rp", "").replace(".", "").replace(",", "").strip())
                    harga_baru = f"Rp {harga_num:,}".replace(",", ".")
                except:
                    harga_baru = harga_input

                # Format harga modal
                try:
                    modal_num = int(modal_input.replace("Rp", "").replace(".", "").replace(",", "").strip()) if modal_input.strip() else 0
                    modal_baru = f"Rp {modal_num:,}".replace(",", ".") if modal_input.strip() else ""
                except:
                    modal_baru = modal_input

                # Update CSV
                df.at[i, "Status"] = "Lunas"
                df.at[i, "Harga Jasa"] = harga_baru
                df.at[i, "Harga Modal"] = modal_baru
                save_data(df, sha)

                # Buat pesan WA
                msg = f"""Assalamualaikum {row['Nama Pelanggan']},

Unit anda dengan nomor nota *{row['No Nota']}* sudah selesai dan siap untuk diambil.

Total Biaya Servis: *{harga_baru}*

Terima Kasih 🙏
{cfg['nama_toko']}"""

                # Format nomor HP
                no_hp = str(row["No HP"]).replace("+", "").replace(" ", "").strip()
                if no_hp.startswith("0"):
                    no_hp = "62" + no_hp[1:]

                link = f"https://wa.me/{no_hp}?text={requests.utils.quote(msg)}"

                st.success(f"✅ Servis {row['Barang']} ditandai lunas & membuka WhatsApp...")
                st.markdown(f"[📲 Buka WhatsApp]({link})", unsafe_allow_html=True)

                # 🔥 Buka otomatis WA di tab baru
                js = f"""
                <script>
                    setTimeout(function(){{
                        window.open("{link}", "_blank");
                    }}, 800);
                </script>
                """
                st.markdown(js, unsafe_allow_html=True)
                st.stop()

            st.info("Isi harga untuk kirim WA otomatis & update status. Harga modal hanya untuk laporan, tidak dikirim ke WA.")

    # ================== HAPUS MASSAL ==================
    st.divider()
    st.subheader("🗑️ Hapus Beberapa Data Sekaligus")

    pilih = st.multiselect(
        "Pilih servis untuk dihapus:",
        df.index,
        format_func=lambda x: f"{df.loc[x, 'Nama Pelanggan']} - {df.loc[x, 'Barang']}"
    )

    if st.button("🚮 Hapus Terpilih"):
        if pilih:
            df = df.drop(pilih).reset_index(drop=True)
            save_data(df, sha)
            st.success("Data terpilih berhasil dihapus.")
            st.rerun()
        else:
            st.warning("Belum ada data yang dipilih.")
