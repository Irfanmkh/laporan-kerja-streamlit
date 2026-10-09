import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="Laporan Data Kerja", layout="wide")

st.title("Laporan Data Kerja")

JSON_FILE = "data/laporan.json"

# Zona waktu GMT+7 (WIB)
WIB = timezone(timedelta(hours=7))

# Helper untuk memformat tanggal/timestamp ke GMT+7 (WIB)
def format_to_wib(dt_input):
    if not dt_input:
        return "-"
    try:
        dt = pd.to_datetime(dt_input)
        if dt.tzinfo is None:
            # Jika naive datetime, tambahkan offset GMT+7
            dt = dt.tz_localize(WIB)
        else:
            dt = dt.tz_convert(WIB)
        return dt.strftime('%d-%m-%Y %H:%M WIB')
    except:
        return str(dt_input)

# Timestamp global (file JSON) dalam GMT+7
if os.path.exists(JSON_FILE):
    mtime = os.path.getmtime(JSON_FILE)
    last_updated_wib = datetime.fromtimestamp(mtime, tz=WIB).strftime('%d-%m-%Y %H:%M WIB')
    st.caption(f"**Terakhir disinkronisasi server:** {last_updated_wib} (GMT+7)")
else:
    st.caption("Belum ada data yang disinkronisasi.")

# Helper Slug URL
def create_slug(title):
    if not title:
        return "laporan"
    slug = str(title).lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')

# Dialog Modal untuk Detail Laporan
@st.dialog("Detail Laporan", width="large")
def show_detail_modal(report):
    col_info, col_img = st.columns([3, 2])
    
    with col_info:
        st.subheader(report['judul'])
        st.write(f"**Tanggal Laporan:** {report['tanggal']}")
        # Menampilkan timestamp per data di modal
        updated_at_str = format_to_wib(report.get('updated_at') or report.get('write_date') or report['tanggal'])
        st.write(f"**Terakhir Diupdate:** {updated_at_str}")
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

        st.markdown("**Unduh File Excel:**")
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
                    st.warning("Gambar tidak ditemukan di server/repo.")
        else:
            st.write("_Tidak ada lampiran screenshot._")

if not os.path.exists(JSON_FILE):
    st.info("Belum ada data laporan yang di-sync.")
else:
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        reports = json.load(f)

    # ---------------------------------------------------------
    # PERSIAPAN DATA & FILTER BULAN
    # ---------------------------------------------------------
    bulan_map = {
        '01': 'Januari', '02': 'Februari', '03': 'Maret', '04': 'April',
        '05': 'Mei', '06': 'Juni', '07': 'Juli', '08': 'Agustus',
        '09': 'September', '10': 'Oktober', '11': 'November', '12': 'Desember'
    }

    unique_months_dict = {}

    for r in reports:
        r['slug'] = create_slug(r['judul'])
        
        try:
            dt = pd.to_datetime(r['tanggal'])
            r['bulan_filter'] = f"{bulan_map[dt.strftime('%m')]} {dt.strftime('%Y')}"
            r['bulan_sort'] = dt.strftime('%Y-%m')
        except:
            r['bulan_filter'] = "Tidak Diketahui"
            r['bulan_sort'] = "0000-00"
            
        if r['bulan_filter'] != "Tidak Diketahui":
            unique_months_dict[r['bulan_filter']] = r['bulan_sort']

    sorted_months = sorted(unique_months_dict.keys(), key=lambda x: unique_months_dict[x], reverse=True)
    list_filter_bulan = ["Semua Bulan"] + sorted_months

    # ---------------------------------------------------------
    # FITUR SHARE LINK
    # ---------------------------------------------------------
    if "modal_opened_from_url" not in st.session_state:
        st.session_state.modal_opened_from_url = False

    if "laporan" in st.query_params and not st.session_state.modal_opened_from_url:
        target_slug = st.query_params["laporan"]
        status_map = {'done': 'Selesai', 'in_progress': 'In Progress', 'pending': 'Pending'}
        
        target_report = next((r for r in reports if r['slug'] == target_slug), None)
        if target_report:
            target_report['status_label'] = status_map.get(target_report['status'], target_report['status'])
            st.session_state.modal_opened_from_url = True
            show_detail_modal(target_report)

    # ---------------------------------------------------------
    # FILTER & PENCARIAN
    # ---------------------------------------------------------
    col_search, col_month, col_status = st.columns([2, 1, 1])
    with col_search:
        search_query = st.text_input("Cari laporan...", "")
    with col_month:
        month_filter = st.selectbox("Filter Bulan", list_filter_bulan)
    with col_status:
        status_filter = st.selectbox("Filter Status", ["Semua", "Selesai", "In Progress", "Pending"])

    status_map = {'done': 'Selesai', 'in_progress': 'In Progress', 'pending': 'Pending'}

    filtered_reports = []
    for r in reports:
        st_label = status_map.get(r['status'], r['status'])
        
        match_search = search_query.lower() in r['judul'].lower() or search_query.lower() in r.get('deskripsi', '').lower()
        match_status = (status_filter == "Semua") or (status_filter == st_label)
        match_month = (month_filter == "Semua Bulan") or (r.get('bulan_filter') == month_filter)

        if match_search and match_status and match_month:
            r['status_label'] = st_label
            filtered_reports.append(r)

    # ---------------------------------------------------------
    # TABEL DATA
    # ---------------------------------------------------------
    if not filtered_reports:
        st.warning("Tidak ada data laporan yang sesuai dengan filter pencarian.")
    else:
        st.markdown("""
            <style>
            .table-header {
                font-weight: 600;
                color: #64748b;
                font-size: 13px;
                border-bottom: 1px solid #e2e8f0;
                padding-bottom: 12px;
                margin-bottom: 4px;
            }
            .status-badge {
                display: inline-block;
                padding: 4px 9px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                white-space: nowrap;
            }
            .stButton > button {
                width: 100%;
                min-height: 34px;
                padding: 4px 10px;
                font-size: 13px;
                font-weight: 500;
                border-radius: 6px;
            }
            .timestamp-sub {
                font-size: 11px;
                color: #64748b;
                margin-top: 2px;
            }
            @media (max-width: 768px) {
                div[data-testid="stHorizontalBlock"] {
                    flex-wrap: nowrap !important;
                    overflow-x: auto !important;
                    -webkit-overflow-scrolling: touch;
                    padding-bottom: 10px;
                }
                div[data-testid="column"] { min-width: 130px !important; }
                div[data-testid="column"]:nth-child(1) { min-width: 40px !important; }
                div[data-testid="column"]:nth-child(7) { min-width: 80px !important; }
            }
            </style>
        """, unsafe_allow_html=True)

        header_cols = st.columns([0.5, 1.4, 2.7, 1.3, 1.8, 2.0, 0.9])

        header_cols[0].markdown('<div class="table-header">No</div>', unsafe_allow_html=True)
        header_cols[1].markdown('<div class="table-header">Tanggal & Update</div>', unsafe_allow_html=True)
        header_cols[2].markdown('<div class="table-header">Judul Laporan</div>', unsafe_allow_html=True)
        header_cols[3].markdown('<div class="table-header">Status</div>', unsafe_allow_html=True)
        header_cols[4].markdown('<div class="table-header">Lampiran Excel</div>', unsafe_allow_html=True)
        header_cols[5].markdown('<div class="table-header">Catatan Khusus</div>', unsafe_allow_html=True)
        header_cols[6].markdown('<div class="table-header">Aksi</div>', unsafe_allow_html=True)

        for idx, r in enumerate(filtered_reports):
            cols = st.columns([0.5, 1.4, 2.7, 1.3, 1.8, 2.0, 0.9], vertical_alignment="center")

            if r['status'] == 'done':
                status_html = '<span class="status-badge" style="color:#0f766e;background:#ccfbf1;">Selesai</span>'
            elif r['status'] == 'in_progress':
                status_html = '<span class="status-badge" style="color:#b45309;background:#fef3c7;">In Progress</span>'
            else:
                status_html = '<span class="status-badge" style="color:#b91c1c;background:#fee2e2;">Pending</span>'

            # Ambil timestamp per item (jika Odoo/JSON punya updated_at / write_date)
            item_ts = format_to_wib(r.get('updated_at') or r.get('write_date') or r['tanggal'])

            cols[0].write(idx + 1)
            # Menampilkan Tanggal Laporan & Timestamp GMT+7 di bawahnya
            cols[1].markdown(f"**{r['tanggal']}**<div class='timestamp-sub'>last updated: {item_ts}</div>", unsafe_allow_html=True)
            cols[2].write(r['judul'])
            cols[3].markdown(status_html, unsafe_allow_html=True)
            
            if r.get('excel_path') and os.path.exists(r['excel_path']):
                with open(r['excel_path'], "rb") as ef:
                    cols[4].download_button(
                        label=f"{r.get('excel_filename', 'Download')}",
                        data=ef.read(),
                        file_name=r.get('excel_filename', 'laporan.xlsx'),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_table_{r['id']}"
                    )
            else:
                cols[4].write("-")
            
            cols[5].write(r.get('catatan_khusus') if r.get('catatan_khusus') else "-")

            if cols[6].button("Detail", key=f"btn_row_{r['id']}"):
                st.query_params["laporan"] = r['slug']
                show_detail_modal(r)