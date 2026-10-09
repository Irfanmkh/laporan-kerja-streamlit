import xmlrpc.client
import json
import base64
import os
import subprocess

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

def fetch_data_from_odoo():
    print("Connecting to Odoo...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})

    if not uid:
        print("❌ Login Odoo Gagal! Periksa DB, Email, atau Password.")
        return

    print("✅ Authenticated successfully!")
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

    # Fetch semua record dari model 'laporan.pekerjaan'
    reports = models.execute_kw(
        ODOO_DB, uid, ODOO_PASS,
        'laporan.pekerjaan', 'search_read',
        [[]],
        {'fields': ['id', 'name', 'tanggal', 'status', 'deskripsi', 'file_excel', 'excel_filename', 'bukti_ss']}
    )

    clean_reports = []

    for r in reports:
        excel_rel_path = None
        ss_rel_path = None

        # Simpan file Excel jika ada
        if r.get('file_excel') and r.get('excel_filename'):
            excel_bytes = base64.b64decode(r['file_excel'])
            filename = f"excel_{r['id']}_{r['excel_filename']}"
            filepath = os.path.join(UPLOADS_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(excel_bytes)
            excel_rel_path = f"data/uploads/{filename}"

        # Simpan Gambar Screenshot jika ada
        if r.get('bukti_ss'):
            ss_bytes = base64.b64decode(r['bukti_ss'])
            filename = f"ss_{r['id']}.png"
            filepath = os.path.join(UPLOADS_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(ss_bytes)
            ss_rel_path = f"data/uploads/{filename}"

        clean_reports.append({
            'id': r['id'],
            'judul': r['name'],
            'tanggal': r['tanggal'],
            'status': r['status'],
            'deskripsi': r['deskripsi'] or '',
            'excel_path': excel_rel_path,
            'excel_filename': r.get('excel_filename') or 'Download Excel',
            'ss_path': ss_rel_path
        })

    # Simpan ke laporan.json
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(clean_reports, f, indent=4, ensure_ascii=False)

    print(f"✅ Extracted {len(clean_reports)} reports to {JSON_FILE}")

def auto_git_push():
    try:
        print("Pushing updates to GitHub...")
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Auto-sync update data laporan dari Odoo"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("🚀 Successfully synced with GitHub!")
    except Exception as e:
        print("⚠️ Git push skipped or failed:", e)

if __name__ == '__main__':
    fetch_data_from_odoo()
    auto_git_push()