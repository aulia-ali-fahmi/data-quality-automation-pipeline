import subprocess
import sys
import os
import glob
import shutil
import logging
from datetime import datetime
import duckdb

# =====================================================================
# 1. KONFIGURASI LOGGING
# Menulis catatan eksekusi ke file 'pipeline_audit.log' dan terminal
# =====================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('pipeline_audit.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logging.info("=== STARTING DATA PIPELINE ORCHESTRATOR ===")

# Path database utama dan pembuatan folder penyimpanan data
main_db_path = 'data_mart/main_warehouse.duckdb'
os.makedirs('data_mart', exist_ok=True)

# =====================================================================
# 2. CEK LOG BUKU TAMU (IDEMPOTENCY CHECK)
# Mencegah file yang sama diproses dua kali jika dimasukkan ulang
# =====================================================================
with duckdb.connect(main_db_path) as main_conn:
    main_conn.execute("""
        CREATE TABLE IF NOT EXISTS processed_files_log (
            file_name VARCHAR UNIQUE,
            processed_at TIMESTAMP
        )
    """)

    # Ambil daftar nama file yang sudah pernah sukses diproses sebelumnya
    processed_files_list = [row[0] for row in main_conn.execute("SELECT file_name FROM processed_files_log").fetchall()]

# Cek apakah ada file CSV baru di folder 'input/'
incoming_files = glob.glob("input/*.csv")

if not incoming_files:
    logging.info("[INFO] No new CSV files found in 'input/' directory. Pipeline standby.")
    sys.exit(0)

# Antrian skrip yang akan dijalankan secara berurutan untuk setiap file
script_queue = ["standardizer.py", "audit.py", "transform.py", "qa_test.py"]

# =====================================================================
# 3. PROSES EKSEKUSI SETIAP FILE CSV
# =====================================================================
for csv_file in incoming_files:
    base_file_name = os.path.basename(csv_file)
    
    # Skrip lompat (SKIP) jika file sudah pernah diproses sebelumnya
    if base_file_name in processed_files_list:
        logging.warning(f"[IDEMPOTENCY SKIP] File '{base_file_name}' was already processed. Skipping.")
        continue

    logging.info(f">>> PROCESSING FILE: {csv_file} <<<")
    file_process_success = True  
    
    # Jalankan tahapan skrip satu per satu (Standardize -> Audit -> Transform -> QA)
    for script_name in script_queue:
        logging.info(f"---> Executing script: {script_name}")
        
        execution_result = subprocess.run([sys.executable, script_name, csv_file], capture_output=True, text=True)
        
        # Tangkap pesan peringatan (warning) jika ada
        if execution_result.stderr.strip():
            for line in execution_result.stderr.strip().split('\n'):
                if line.strip():
                    logging.warning(f"[{script_name}] {line}")
                    
        # Jika skrip gagal (return code != 0), hentikan eksekusi file ini
        if execution_result.returncode != 0:
            output_lines = (execution_result.stdout + "\n" + execution_result.stderr).strip().split('\n')
            failure_reason = output_lines[-1] if output_lines else "Unknown execution error"
            
            logging.error(f"[ERROR] Pipeline FAILED at {script_name} for file {csv_file}. Reason: {failure_reason}")
            file_process_success = False  
            break
            
    current_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # =====================================================================
    # 4. PENANGANAN HASIL (ARCHIVE vs QUARANTINE)
    # =====================================================================
    if file_process_success:
        # Catat ke database bahwa file ini sukses diproses
        with duckdb.connect(main_db_path) as main_conn:
            main_conn.execute(f"INSERT INTO processed_files_log VALUES ('{base_file_name}', CURRENT_TIMESTAMP)")

        # Pindahkan file CSV asli ke folder 'archive'
        archived_target = f"archive/processed_{current_timestamp}_{base_file_name}"
        shutil.move(csv_file, archived_target)
        logging.info(f"[ARCHIVING] Success. File moved to: {archived_target}")
    else:
        # Pindahkan file CSV bermasalah ke folder 'rejected' (karantina)
        quarantine_target = f"rejected/failed_{current_timestamp}_{base_file_name}"
        shutil.move(csv_file, quarantine_target)
        logging.warning(f"[QUARANTINE] File isolated to: {quarantine_target}")

# Bersihkan database sementara jika masih tersisa
if os.path.exists('temp_staging.db'):
    os.remove('temp_staging.db')
    
# =====================================================================
# 5. FINAL LOAD TO DATA MART & REPORTING
# Pembaharuan tabel utama untuk dasbor analisis bisnis
# =====================================================================
if os.path.exists('data_mart/analytics_ready_data.parquet'):
    with duckdb.connect(main_db_path) as main_conn:
        main_conn.execute("""
            CREATE OR REPLACE TABLE sales_dashboard AS 
            SELECT * FROM read_parquet('data_mart/analytics_ready_data.parquet')
        """)
        logging.info("[DATA MART] Main database table updated with clean dataset!")
    
    logging.info("---> Generating Executive Report via reporter.py")
    subprocess.run([sys.executable, "reporter.py"])

logging.info("=== PIPELINE EXECUTION COMPLETED ===")