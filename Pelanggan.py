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

        # gunakan session_state agar aksi tidak hilang saat rerun
        action_key = f"action_{no_nota}"
        if action_key not in st.session_state:
            st.session_state[action_key] = None

        if (status_antrian == "" or status_antrian.lower() == "antrian") and active_status == "Antrian":
            if st.button("✅ Siap Diambil (Kirim WA)", key=f"ambil_{no_nota}"):
                st.session_state[action_key] = "ambil"
                st.session_state[f"data_{no_nota}"] = (nama, no_nota, no_hp, hj_str, jenis_transaksi)
                st.rerun()

        elif status_antrian.lower() == "siap diambil" and active_status == "Siap Diambil":
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✔️ Selesai", key=f"selesai_{no_nota}"):
                    st.session_state[action_key] = "selesai"
                    st.rerun()
            with c2:
                if st.button("❌ Batal", key=f"batal_{no_nota}"):
                    st.session_state[action_key] = "batal"
                    st.rerun()

        else:
            st.info(f"📌 Status Antrian: {status_antrian or 'Antrian'}")

        # eksekusi aksi setelah rerun
        if st.session_state[action_key] == "ambil":
            nama, no_nota, no_hp, hj_str, jenis_transaksi = st.session_state.get(f"data_{no_nota}", ("", "", "", "", ""))
            updates = {
                "Harga Jasa": hj_str,
                "Harga Modal": hm_str,
                "Jenis Transaksi": jenis_transaksi,
                "Status Antrian": "Siap Diambil"
            }
            ok = update_sheet_row_by_nota(SHEET_SERVIS, no_nota, updates)
            if ok:
                reload_df()
                kirim_wa_pelanggan(nama, no_nota, no_hp, hj_str, jenis_transaksi, cfg['nama_toko'])
                st.success(f"Nota {no_nota} → Siap Diambil dan WA terbuka.")
            st.session_state[action_key] = None

        elif st.session_state[action_key] == "selesai":
            ok = update_sheet_row_by_nota(SHEET_SERVIS, no_nota, {"Status Antrian": "Selesai"})
            if ok:
                reload_df()
                st.success(f"Nota {no_nota} → Selesai")
            st.session_state[action_key] = None

        elif st.session_state[action_key] == "batal":
            ok = update_sheet_row_by_nota(SHEET_SERVIS, no_nota, {"Status Antrian": "Batal"})
            if ok:
                reload_df()
                st.warning(f"Nota {no_nota} → Batal")
            st.session_state[action_key] = None
