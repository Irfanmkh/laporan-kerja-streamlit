import xmlrpc.client
import json
import base64
import os
import subprocess
from datetime import datetime, timezone, timedelta  # <-- Tambahan modul datetime

# 1. Konfigurasi Odoo Lokal
ODOO_URL = 'http://localhost:8069'
ODOO_DB = 'laporan-kerja'          # Sesuaikan dengan nama database Odoo kamu
ODOO_USER = 'irfankhakiki17@gmail.com'    # Email login Odoo kamu
ODOO_PASS = 'Imaka1011'           # Password login Odoo kamu

# 2. Path Penyimpanan
DATA_DIR = 'data'
UPLOADS_DIR = os.path.join(DATA_DIR, 'uploads')
JSON_FILE = os.path.join(DATA_DIR, 'laporan.json')

os.makedirs(UPLOADS_DIR, exist_ok=True)

# Definisikan Zona Waktu WIB (GMT+7)
WIB = timezone(timedelta(hours=7))

def fetch_data_from_odoo():
    print("Connecting to Odoo...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})

    if not uid:
        print("❌ Login Odoo Gagal!")
        return

    print("✅ Authenticated successfully!")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

    # Format timestamp WIB saat proses sync dijalankan
    now_wib_str = datetime.now(WIB).strftime('%Y-%m-%d %H:%M:%S')

    reports = models.execute_kw(
        ODOO_DB, uid, ODOO_PASS,
        'laporan.pekerjaan', 'search_read',
        [[]],
        {'fields': ['id', 'name', 'tanggal', 'status', 'deskripsi', 'catatan_khusus', 'file_excel', 'excel_filename', 'bukti_ss_ids', 'write_date']}
    )

    clean_reports = []

    for r in reports:
        excel_rel_path = None
        ss_paths = []

        # Unduh Excel
        if r.get('file_excel') and r.get('excel_filename'):
            excel_bytes = base64.b64decode(r['file_excel'])
            filename = f"excel_{r['id']}_{r['excel_filename']}"
            filepath = os.path.join(UPLOADS_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(excel_bytes)
            excel_rel_path = f"data/uploads/{filename}"

        # Unduh Banyak Screenshot dari Model laporan.pekerjaan.ss
        ss_ids = r.get('bukti_ss_ids', [])
        if ss_ids:
            ss_records = models.execute_kw(
                ODOO_DB, uid, ODOO_PASS,
                'laporan.pekerjaan.ss', 'search_read',
                [[['id', 'in', ss_ids]]],
                {'fields': ['id', 'image', 'description']}
            )
            for index, ss in enumerate(ss_records):
                if ss.get('image'):
                    ss_bytes = base64.b64decode(ss['image'])
                    filename = f"ss_{r['id']}_{ss['id']}.png"
                    filepath = os.path.join(UPLOADS_DIR, filename)
                    with open(filepath, 'wb') as f:
                        f.write(ss_bytes)
                    ss_paths.append({
                        'path': f"data/uploads/{filename}",
                        'desc': ss.get('description') or f"Screenshot {index + 1}"
                    })

        # Gunakan write_date dari Odoo atau waktu WIB saat sync jika kosong
        updated_at_val = r.get('write_date') or now_wib_str

        clean_reports.append({
            'id': r['id'],
            'judul': r['name'],
            'tanggal': r['tanggal'],
            'updated_at': updated_at_val,  # <-- Timestamp jam & menit untuk Streamlit
            'status': r['status'],
            'deskripsi': r.get('deskripsi') or '',
            'catatan_khusus': r.get('catatan_khusus') or '',
            'excel_path': excel_rel_path,
            'excel_filename': r.get('excel_filename') or 'Download Excel',
            'ss_list': ss_paths
        })

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(clean_reports, f, indent=4, ensure_ascii=False)

    print(f"✅ Extracted {len(clean_reports)} reports to {JSON_FILE}")

def auto_git_push():
    try:
        print("Pushing updates to GitHub...")
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        
        if not status.stdout.strip():
            print("ℹ️ Tidak ada perubahan data baru dari Odoo. Push dilewati.")
            return

        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Auto-sync update data laporan dari Odoo"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("🚀 Successfully synced with GitHub!")
    except Exception as e:
        print("⚠️ Git push error:", e)

if __name__ == '__main__':
    fetch_data_from_odoo()
    auto_git_push()