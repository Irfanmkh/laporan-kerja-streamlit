import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Laporan Data Kerja", layout="wide")

st.title("Laporan Data Kerja")
st.caption("Daftar laporan pekerjaan harian")

JSON_FILE = "data/laporan.json"

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
                    st.image(item['path'], caption=item['desc'], use_container_width=True)
        else:
            st.write("_Tidak ada lampiran screenshot._")

if not os.path.exists(JSON_FILE):
    st.info("Belum ada data laporan yang di-sync.")
else:
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        reports = json.load(f)

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
        header_cols = st.columns([0.5, 1.5, 3.5, 1.5, 2, 2, 1.5])
        header_cols[0].markdown("**No**")
        header_cols[1].markdown("**Tanggal**")
        header_cols[2].markdown("**Judul Laporan**")
        header_cols[3].markdown("**Status**")
        header_cols[4].markdown("**Lampiran Excel**")
        header_cols[5].markdown("**Catatan Khusus**")
        header_cols[6].markdown("**Aksi**")
        
        st.divider()

        for idx, r in enumerate(filtered_reports):
            cols = st.columns([0.5, 1.5, 3.5, 1.5, 2, 2, 1.5])
            
            if r['status'] == 'done':
                status_html = '<span style="color: #0d9488; background-color: #ccfbf1; padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 13px;">Selesai</span>'
            elif r['status'] == 'in_progress':
                status_html = '<span style="color: #d97706; background-color: #fef3c7; padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 13px;">In Progress</span>'
            else:
                status_html = '<span style="color: #dc2626; background-color: #fee2e2; padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 13px;">Pending</span>'

            cols[0].write(idx + 1)
            cols[1].write(r['tanggal'])
            cols[2].write(r['judul'])
            cols[3].markdown(status_html, unsafe_allow_html=True)
            cols[4].write(r.get('excel_filename') if r.get('excel_path') else "-")
            cols[5].write(r.get('catatan_khusus') if r.get('catatan_khusus') else "-")
            
            if cols[6].button("Detail", key=f"btn_{r['id']}"):
                show_detail_modal(r)