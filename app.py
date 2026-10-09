import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime, timezone, timedelta

st.set_page_config(page_title="Laporan Data Kerja", layout="wide")

st.title("Laporan Data Kerja")

JSON_FILE = "data/laporan.json"
WIB = timezone(timedelta(hours=7))

# --- HELPER FORMATTING ---
def format_to_wib(dt_input):
    if not dt_input:
        return "-"
    try:
        dt = pd.to_datetime(dt_input)
        if dt.tzinfo is None:
            dt = dt.tz_localize('UTC').tz_convert(WIB)
        else:
            dt = dt.tz_convert(WIB)
        return dt.strftime('%d-%m-%Y %H:%M WIB')
    except:
        return str(dt_input)

# Timestamp Global
if os.path.exists(JSON_FILE):
    mtime = os.path.getmtime(JSON_FILE)
    last_updated_wib = datetime.fromtimestamp(mtime, tz=WIB).strftime('%d-%m-%Y %H:%M WIB')
    st.caption(f"🕒 **Terakhir disinkronisasi server:** {last_updated_wib}")
else:
    st.caption("🕒 Belum ada data yang disinkronisasi.")

def create_slug(title):
    if not title:
        return "laporan"
    slug = str(title).lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    return slug.strip('-')

# --- DEKLARASI MODAL DIALOG ---
@st.dialog("Detail Laporan Pekerjaan", width="large")
def show_detail_modal(report):
    col_info, col_img = st.columns([3, 2])
    
    with col_info:
        st.subheader(report['judul'])
        st.write(f"**Tanggal Laporan:** {report['tanggal']}")
        
        raw_ts = report.get('updated_at') or report.get('write_date')
        item_ts = format_to_wib(raw_ts) if raw_ts else last_updated_wib
        st.write(f"**Terakhir Diupdate:** {item_ts}")
        
        status_map = {'done': 'Selesai', 'in_progress': 'In Progress', 'pending': 'Pending'}
        st.write(f"**Status:** {status_map.get(report['status'], report['status'])}")
        
        st.markdown("**Deskripsi Pekerjaan:**")
        st.write(report.get('deskripsi') or "_Tidak ada deskripsi._")
            
        st.markdown("**Catatan Khusus:**")
        if report.get('catatan_khusus'):
            st.info(report['catatan_khusus'])
        else:
            st.write("_Tidak ada catatan khusus._")

        st.markdown("**Unduh File Excel:**")
        if report.get('excel_path') and os.path.exists(report['excel_path']):
            with open(report['excel_path'], "rb") as ef:
                st.download_button(
                    label=f"Unduh {report.get('excel_filename', 'Excel')}",
                    data=ef.read(),
                    file_name=report.get('excel_filename', 'laporan.xlsx'),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_modal_{report.get('id', 'default')}"
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


# --- MANAGEMENT DATA & SESSION STATE ---
if not os.path.exists(JSON_FILE):
    st.info("Belum ada data laporan yang di-sync.")
    st.stop()

with open(JSON_FILE, "r", encoding="utf-8") as f:
    reports = json.load(f)

# Inisialisasi state laporan aktif
if "active_report" not in st.session_state:
    st.session_state.active_report = None

# Persiapan Slug & Filter Bulan
bulan_map = {'01':'Januari','02':'Februari','03':'Maret','04':'April','05':'Mei','06':'Juni','07':'Juli','08':'Agustus','09':'September','10':'Oktober','11':'November','12':'Desember'}
unique_months_dict = {}

for r in reports:
    r['slug'] = create_slug(r['judul'])
    try:
        dt = pd.to_datetime(r['tanggal'])
        r['bulan_filter'] = f"{bulan_map[dt.strftime('%m')]} {dt.strftime('%Y')}"
        r['bulan_sort'] = dt.strftime('%Y-%m')
        unique_months_dict[r['bulan_filter']] = r['bulan_sort']
    except:
        r['bulan_filter'] = "Tidak Diketahui"

sorted_months = sorted(unique_months_dict.keys(), key=lambda x: unique_months_dict[x], reverse=True)
list_filter_bulan = ["Semua Bulan"] + sorted_months

# Cek URL Parameter jika halaman di-load langsung via Link Share
if "laporan" in st.query_params and st.session_state.active_report is None:
    target_slug = st.query_params["laporan"]
    target = next((r for r in reports if r['slug'] == target_slug), None)
    if target:
        st.session_state.active_report = target


# --- FILTER UI ---
col_search, col_month, col_status = st.columns([2, 1, 1])
search_query = col_search.text_input("Cari laporan...", "")
month_filter = col_month.selectbox("Filter Bulan", list_filter_bulan)
status_filter = col_status.selectbox("Filter Status", ["Semua", "Selesai", "In Progress", "Pending"])

status_map = {'done': 'Selesai', 'in_progress': 'In Progress', 'pending': 'Pending'}

filtered_reports = []
for r in reports:
    st_label = status_map.get(r['status'], r['status'])
    match_search = search_query.lower() in r['judul'].lower() or search_query.lower() in r.get('deskripsi', '').lower()
    match_status = (status_filter == "Semua") or (status_filter == st_label)
    match_month = (month_filter == "Semua Bulan") or (r.get('bulan_filter') == month_filter)

    if match_search and match_status and match_month:
        filtered_reports.append(r)


# --- TABEL DATA ---
if not filtered_reports:
    st.warning("Tidak ada data laporan yang sesuai dengan filter pencarian.")
else:
    st.markdown("""
        <style>
        .table-header { font-weight: 600; color: #64748b; font-size: 13px; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 4px; }
        .status-badge { display: inline-block; padding: 4px 9px; border-radius: 6px; font-size: 12px; font-weight: 600; white-space: nowrap; }
        .stButton > button { width: 100%; min-height: 34px; padding: 4px 10px; font-size: 13px; font-weight: 500; border-radius: 6px; }
        @media (max-width: 768px) {
            div[data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; overflow-x: auto !important; -webkit-overflow-scrolling: touch; padding-bottom: 10px; }
            div[data-testid="column"] { min-width: 130px !important; }
            div[data-testid="column"]:nth-child(1) { min-width: 40px !important; }
            div[data-testid="column"]:nth-child(7) { min-width: 80px !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    header_cols = st.columns([0.5, 1.4, 2.7, 1.3, 1.8, 2.0, 0.9])
    headers = ["No", "Tanggal & Update", "Judul Laporan", "Status", "Lampiran Excel", "Catatan Khusus", "Aksi"]
    for i, h in enumerate(headers):
        header_cols[i].markdown(f'<div class="table-header">{h}</div>', unsafe_allow_html=True)

    for idx, r in enumerate(filtered_reports):
        cols = st.columns([0.5, 1.4, 2.7, 1.3, 1.8, 2.0, 0.9], vertical_alignment="center")

        if r['status'] == 'done':
            status_html = '<span class="status-badge" style="color:#0f766e;background:#ccfbf1;">Selesai</span>'
        elif r['status'] == 'in_progress':
            status_html = '<span class="status-badge" style="color:#b45309;background:#fef3c7;">In Progress</span>'
        else:
            status_html = '<span class="status-badge" style="color:#b91c1c;background:#fee2e2;">Pending</span>'

        raw_ts = r.get('updated_at') or r.get('write_date')
        item_ts = format_to_wib(raw_ts) if raw_ts else last_updated_wib
        row_id = r.get('id', idx)

        cols[0].write(idx + 1)
        cols[1].markdown(f"<b>{r['tanggal']}</b><br><span style='font-size: 11px; color: #64748b;'>last updated: {item_ts}</span>", unsafe_allow_html=True)
        cols[2].write(r['judul'])
        cols[3].markdown(status_html, unsafe_allow_html=True)
        
        # Download Excel
        if r.get('excel_path') and os.path.exists(r['excel_path']):
            with open(r['excel_path'], "rb") as ef:
                cols[4].download_button(
                    label=f"{r.get('excel_filename', 'Download')}",
                    data=ef.read(),
                    file_name=r.get('excel_filename', 'laporan.xlsx'),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_tbl_{row_id}_{idx}"
                )
        else:
            cols[4].write("-")
        
        cols[5].write(r.get('catatan_khusus') if r.get('catatan_khusus') else "-")

        # Tombol Detail: Set state & parameter URL tanpa memanggil modal langsung di sini
        if cols[6].button("Detail", key=f"btn_row_{row_id}_{idx}"):
            st.query_params["laporan"] = r['slug']
            st.session_state.active_report = r
            st.rerun()

# --- EKSEKUSI MODAL HANYA 1 KALI DI PALING BAWAH ---
if st.session_state.active_report:
    show_detail_modal(st.session_state.active_report)