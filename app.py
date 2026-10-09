import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Laporan Data Kerja", layout="wide")

st.title("Laporan Data Kerja")
st.caption("Daftar laporan pekerjaan harian")

JSON_FILE = "data/laporan.json"

# Dialog Modal untuk Detail Laporan
@st.dialog("Detail Laporan Pekerjaan", width="large")
def show_detail_modal(report):
    col_info, col_img = st.columns([3, 2])
    
    with col_info:
        st.subheader(report['judul'])
        st.write(f"**Tanggal:** {report['tanggal']}")
        st.write(f"**Status:** {report['status_label']}")
        
        st.markdown("**Deskripsi Pekerjaan:**")
        if report.get('deskripsi'):
            st.write(report['deskripsi'])
        else:
            st.write("_Tidak ada deskripsi._")
            
        st.markdown("**Catatan Khusus:**")
        if report.get('catatan_khusus'):
            st.info(report['catatan_khusus'])
        else:
            st.write("_Tidak ada catatan khusus._")

        if report.get('excel_path') and os.path.exists(report['excel_path']):
            with open(report['excel_path'], "rb") as ef:
                st.download_button(
                    label=f"Unduh {report['excel_filename']}",
                    data=ef.read(),
                    file_name=report['excel_filename'],
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_modal_{report['id']}"
                )

    with col_img:
        st.markdown("**Bukti Screenshot:**")
        ss_list = report.get('ss_list', [])
        if ss_list:
            for item in ss_list:
                if os.path.exists(item['path']):
                    st.image(item['path'], caption=item.get('desc', 'Screenshot'), use_container_width=True)
                else:
                    st.warning(f"File gambar `{item['path']}` tidak ditemukan di server/repo.")
        else:
            st.write("_Tidak ada lampiran screenshot._")

if not os.path.exists(JSON_FILE):
    st.info("Belum ada data laporan yang di-sync.")
else:
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        reports = json.load(f)

    # Filter & Search
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        search_query = st.text_input("Cari laporan...", "")
    with col_filter:
        status_filter = st.selectbox("Filter Status", ["Semua", "Selesai", "In Progress", "Pending"])

    status_map = {'done': 'Selesai', 'in_progress': 'In Progress', 'pending': 'Pending'}

    filtered_reports = []
    for r in reports:
        st_label = status_map.get(r['status'], r['status'])
        
        match_search = search_query.lower() in r['judul'].lower() or search_query.lower() in r.get('deskripsi', '').lower()
        match_status = (status_filter == "Semua") or (status_filter == st_label)

        if match_search and match_status:
            r['status_label'] = st_label
            filtered_reports.append(r)

    if not filtered_reports:
        st.warning("Tidak ada data laporan yang sesuai.")
    else:
        # Pilihan Laporan / Aksi Detail (Sangat Friendly untuk Mobile)
        selected_title = st.selectbox(
            "Pilih laporan untuk melihat detail & bukti screenshot:",
            options=["-- Pilih Laporan --"] + [r['judul'] for r in filtered_reports]
        )

        if selected_title != "-- Pilih Laporan --":
            selected_report = next((r for r in filtered_reports if r['judul'] == selected_title), None)
            if selected_report:
                if st.button("Buka Pop-up Detail", type="primary"):
                    show_detail_modal(selected_report)

        st.write("") # Spacer

        # Olah data untuk Tabel Responsive
        table_data = []
        for idx, r in enumerate(filtered_reports):
            table_data.append({
                "No": idx + 1,
                "Tanggal": r['tanggal'],
                "Judul Laporan": r['judul'],
                "Status": r['status_label'],
                "Lampiran Excel": r.get('excel_filename') if r.get('excel_path') else "-",
                "Catatan Khusus": r.get('catatan_khusus') if r.get('catatan_khusus') else "-"
            })

        df = pd.DataFrame(table_data)

        # Function Styling Warna Status
        def highlight_status(val):
            if val == 'Selesai':
                return 'background-color: #ccfbf1; color: #0d9488; font-weight: bold;'
            elif val == 'In Progress':
                return 'background-color: #fef3c7; color: #d97706; font-weight: bold;'
            elif val == 'Pending':
                return 'background-color: #fee2e2; color: #dc2626; font-weight: bold;'
            return ''

        styled_df = df.style.map(highlight_status, subset=['Status'])

        # Render Tabel Bawaan Streamlit (Otomatis Scroll Horizontal & Responsive di HP)
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "No": st.column_config.NumberColumn("No", width="small"),
                "Tanggal": st.column_config.TextColumn("Tanggal", width="medium"),
                "Judul Laporan": st.column_config.TextColumn("Judul Laporan", width="large"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Lampiran Excel": st.column_config.TextColumn("Lampiran Excel", width="medium"),
                "Catatan Khusus": st.column_config.TextColumn("Catatan Khusus", width="medium"),
            }
        )