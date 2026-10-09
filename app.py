import streamlit as st
import json
import os

st.set_page_config(page_title="Dashboard Laporan Pekerjaan", page_icon="📊", layout="wide")

st.title("📊 Dashboard Laporan Pekerjaan")
st.caption("Daftar laporan pekerjaan publik (Read-Only)")

JSON_FILE = "data/laporan.json"

if not os.path.exists(JSON_FILE):
    st.info("Belum ada data laporan yang di-sync.")
else:
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        reports = json.load(f)

    # Filter & Search
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("🔍 Cari laporan...", "")
    with col_filter:
        status_filter = st.selectbox("Filter Status", ["Semua", "Selesai", "In Progress", "Pending"])

    # Map status Odoo ke teks tampilan
    status_map = {'done': 'Selesai', 'in_progress': 'In Progress', 'pending': 'Pending'}

    filtered_reports = []
    for r in reports:
        st_label = status_map.get(r['status'], r['status'])
        
        # Match Filter
        match_search = search_query.lower() in r['judul'].lower() or search_query.lower() in r['deskripsi'].lower()
        match_status = (status_filter == "Semua") or (status_filter == st_label)

        if match_search and match_status:
            r['status_label'] = st_label
            filtered_reports.append(r)

    st.write(f"Menampilkan **{len(filtered_reports)}** laporan")
    st.divider()

    # Loop Laporan Card
    for r in filtered_reports:
        with st.container():
            col1, col2 = st.columns([3, 2])

            with col1:
                st.subheader(r['judul'])
                st.caption(f"📅 Tanggal: **{r['tanggal']}** | Status: **{r['status_label']}**")
                st.write(r['deskripsi'] if r['deskripsi'] else "_Tidak ada deskripsi._")

                # Tombol Download Excel
                if r.get('excel_path') and os.path.exists(r['excel_path']):
                    with open(r['excel_path'], "rb") as ef:
                        st.download_button(
                            label=f"📁 Unduh File ({r['excel_filename']})",
                            data=ef.read(),
                            file_name=r['excel_filename'],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_{r['id']}"
                        )

            with col2:
                # Preview Bukti Screenshot
                if r.get('ss_path') and os.path.exists(r['ss_path']):
                    st.image(r['ss_path'], caption="Bukti Screenshot", use_container_width=True)

            st.divider()