import subprocess
import sys
import os
import glob
import shutil
import logging
from datetime import datetime
import duckdb # TAMBAH IMPORT DUCKDB DI SINI

# SETTING LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('pipeline_audit.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logging.info("=== MEMULAI DATA PIPELINE ORCHESTRATOR (IDEMPOTENT MODE) ===")

# =================================================================
# [BARU] INISIALISASI BUKU TAMU (WATERMARK TABLE)
# =================================================================
db_utama = 'data_mart/database_utama.duckdb'
# Pastikan folder data_mart ada
os.makedirs('data_mart', exist_ok=True)

# BLOK 1: UBAH KE WITH CONTEXT MANAGER
with duckdb.connect(db_utama) as con_utama:
    con_utama.execute("""
        CREATE TABLE IF NOT EXISTS file_diproses_log (
            nama_file VARCHAR UNIQUE,
            waktu_selesai TIMESTAMP
        )
    """)

    # Ambil daftar file yang sudah pernah diproses ke dalam sebuah List Python
    daftar_file_sukses = [row[0] for row in con_utama.execute("SELECT nama_file FROM file_diproses_log").fetchall()]
# (con_utama.close() otomatis terjadi di sini saat keluar dari blok indentasi)
# =================================================================

file_masuk = glob.glob("input/*.csv")

if not file_masuk:
    logging.info("[INFO] Tidak ada file baru di folder 'input/'. Pipeline standby.")
    sys.exit(0)

antrian_skrip = ["standardizer.py", "audit.py", "transform.py", "qa_test.py"]

for file_csv in file_masuk:
    nama_file_dasar = os.path.basename(file_csv)
    
    # =================================================================
    # [BARU] PENGECEKAN IDEMPOTENCY (CEGAH PROSES ULANG)
    # =================================================================
    if nama_file_dasar in daftar_file_sukses:
        logging.warning(f"[IDEMPOTENCY SKIP] File {nama_file_dasar} SUDAH PERNAH DIPROSES sebelumnya. Mengabaikan file ini.")
        # Opsi: Pindahkan file yang terlanjur masuk ini ke folder 'duplicate' atau langsung hapus.
        # Untuk sekarang, kita biarkan saja atau bisa pindahkan ke rejected.
        continue # Lompat ke file_csv berikutnya dalam loop
    # =================================================================

    pesan_mulai = f">>> MEMPROSES FILE: {file_csv} <<<"
    logging.info(pesan_mulai)
    
    file_sukses = True  
    
    for skrip in antrian_skrip:
        logging.info(f"---> Menjalankan: {skrip}")
        
        hasil = subprocess.run([sys.executable, skrip, file_csv], capture_output=True, text=True)
        
        if hasil.stderr.strip():
            for line in hasil.stderr.strip().split('\n'):
                if line.strip():
                    logging.warning(f"[{skrip}] {line}")
                    
        if hasil.returncode != 0:
            semua_output = (hasil.stdout + "\n" + hasil.stderr).strip().split('\n')
            pesan_inti = semua_output[-1] if semua_output else "Terjadi kesalahan"
            
            logging.error(f"[ERROR] Pipeline GAGAL di {skrip} saat memproses {file_csv}. Alasan: {pesan_inti}")
            file_sukses = False  
            break
            
    waktu_sekarang = datetime.now().strftime("%Y%m%d_%H%M%S")

    if file_sukses:
        # =================================================================
        # [BARU] CATAT KE BUKU TAMU JIKA SUKSES SAMPAI AKHIR
        # =================================================================
        # BLOK 2: UBAH KE WITH CONTEXT MANAGER
        with duckdb.connect(db_utama) as con_utama:
            con_utama.execute(f"INSERT INTO file_diproses_log VALUES ('{nama_file_dasar}', CURRENT_TIMESTAMP)")
        # =================================================================

        file_baru = f"archive/processed_{waktu_sekarang}_{nama_file_dasar}"
        shutil.move(file_csv, file_baru)
        logging.info(f"[ARCHIVING] Sukses. File dipindahkan ke: {file_baru}")
    else:
        file_baru = f"rejected/failed_{waktu_sekarang}_{nama_file_dasar}"
        shutil.move(file_csv, file_baru)
        logging.warning(f"[QUARANTINE] File diisolasi ke: {file_baru}")

if os.path.exists('latihan_QA.db'):
    os.remove('latihan_QA.db')
    
# FINAL LOAD: DATABASE PERMANEN UNTUK ANALYST
if os.path.exists('data_mart/data_siap_analisis.parquet'):
    # BLOK 3: UBAH KE WITH CONTEXT MANAGER
    with duckdb.connect(db_utama) as con_utama:
        con_utama.execute("""
            CREATE OR REPLACE TABLE sales_dashboard AS 
            SELECT * FROM read_parquet('data_mart/data_siap_analisis.parquet')
        """)
        logging.info("[DATA MART] Database utama berhasil di-update dengan data terbaru!")
    
    logging.info("---> Menjalankan Reporting Layer: reporter.py")
    subprocess.run([sys.executable, "reporter.py"])

logging.info("=== PIPELINE SELESAI ===")