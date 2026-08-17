import duckdb
import sys

print("=== STARTING RAW COLUMN STANDARDIZATION ===")

# =====================================================================
# 1. TANGKAP ARGUMEN DINAMIS DARI PIPELINE
# sys.argv[1] menerima path nama file CSV yang dilempar oleh pipeline.py
# =====================================================================
if len(sys.argv) < 2:
    print("[FATAL ERROR] Target CSV file path was not provided to standardizer!")
    sys.exit(1)

target_file = sys.argv[1]

# Menghubungkan ke database staging sementara (sesuai penamaan pipeline.py)
db_conn = duckdb.connect('temp_staging.db')

try:
    # =====================================================================
    # 2. BACA CSV DAN INSPEKSI SKEMA KOLOM
    # Membaca struktur kolom asli dari vendor/supplier
    # =====================================================================
    load_query = f"CREATE OR REPLACE TEMPORARY VIEW temp_column_check AS SELECT * FROM read_csv_auto('{target_file}', encoding='latin-1')"
    db_conn.execute(load_query)
    
    table_info = db_conn.execute("PRAGMA table_info('temp_column_check')").fetchall()
    original_columns = [row[1] for row in table_info]
    
    # Hapus tabel staging lama jika ada
    db_conn.execute("DROP TABLE IF EXISTS raw_sales")

    # =====================================================================
    # 3. STANDARISASI IDENTITAS PELANGGAN
    # Mengubah nama kolom lokal (ID_Pelanggan) menjadi standar (CustomerID)
    # =====================================================================
    if 'ID_Pelanggan' in original_columns:
        db_conn.execute("""
            CREATE TABLE raw_sales AS 
            SELECT InvoiceNo, StockCode, Quantity, UnitPrice, Country,
                   ID_Pelanggan AS CustomerID
            FROM temp_column_check
        """)
        print(f"[SUCCESS] Detected 'ID_Pelanggan' column in {target_file}. Successfully standardized to CustomerID.")
        
    elif 'CustomerID' in original_columns:
        db_conn.execute("CREATE TABLE raw_sales AS SELECT * FROM temp_column_check")
        print(f"[SUCCESS] Columns in {target_file} already match internal schema standard.")
        
    else:
        print(f"\n[FATAL ERROR] Identity column (CustomerID / ID_Pelanggan) not found in {target_file}!")
        sys.exit(1)

except Exception as e:
    print(f"\n[FATAL ERROR] Standardization process failed: {e}")
    sys.exit(1)