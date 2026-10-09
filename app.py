import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Laporan Data Kerja", layout="wide")

st.title("Laporan Data Kerja")
st.caption("Daftar laporan pekerjaan harian")

JSON_FILE = "data/laporan.json"

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
        
        match_search = search_query.lower() in r['judul'].lower() or search_query.lower() in r['deskripsi'].lower()
        match_status = (status_filter == "Semua") or (status_filter == st_label)

        if match_search and match_status:
            r['status_label'] = st_label
            filtered_reports.append(r)

    if not filtered_reports:
        st.warning("Tidak ada data laporan yang sesuai.")
    else:
        # Konversi data ke DataFrame untuk tampilan tabel yang rapi
        table_data = []
        for index, r in enumerate(filtered_reports):
            table_data.append({
                "No": index + 1,
                "Tanggal": r['tanggal'],
                "Judul Laporan": r['judul'],
                "Status": r['status_label'],
                "Lampiran Excel": r['excel_filename'] if r.get('excel_path') else "-"
            })

        df = pd.DataFrame(table_data)

        # Tampilkan Tabel Utama
        st.dataframe(
            df,
            column_config={
                "No": st.column_config.NumberColumn("No", width="small"),
                "Tanggal": st.column_config.TextColumn("Tanggal", width="medium"),
                "Judul Laporan": st.column_config.TextColumn("Judul Laporan", width="large"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Lampiran Excel": st.column_config.TextColumn("Lampiran Excel", width="medium"),
            },
            hide_index=True,
            use_container_width=True
        )

        st.divider()

        # Pilihan Laporan untuk Melihat Detail & Gambar Screenshot
        st.subheader("Detail Laporan")
        selected_title = st.selectbox(
            "Pilih laporan untuk melihat detail dan bukti gambar:",
            options=[r['judul'] for r in filtered_reports]
        )

        # Cari data laporan yang dipilih
        selected_report = next((r for r in filtered_reports if r['judul'] == selected_title), None)

        if selected_report:
            col_detail, col_media = st.columns([3, 2])

            with col_detail:
                st.markdown(f"### {selected_report['judul']}")
                st.write(f"**Tanggal:** {selected_report['tanggal']} | **Status:** {selected_report['status_label']}")
                
                st.markdown("**Deskripsi Pekerjaan:**")
                if selected_report['deskripsi']:
                    st.write(selected_report['deskripsi'])
                else:
                    st.write("_Tidak ada deskripsi._")

                # Tombol Download File Excel
                if selected_report.get('excel_path') and os.path.exists(selected_report['excel_path']):
                    with open(selected_report['excel_path'], "rb") as ef:
                        st.download_button(
                            label=f"Unduh {selected_report['excel_filename']}",
                            data=ef.read(),
                            file_name=selected_report['excel_filename'],
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_selected_{selected_report['id']}"
                        )

            with col_media:
                # Gambar hanya tampil di sini ketika laporan dipilih/diklik
                if selected_report.get('ss_path') and os.path.exists(selected_report['ss_path']):
                    st.image(selected_report['ss_path'], caption="Bukti Screenshot", use_container_width=True)
                else:
                    st.info("Tidak ada lampiran screenshot pada laporan ini.")