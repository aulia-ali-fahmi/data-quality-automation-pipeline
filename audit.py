import duckdb
import sys

# =====================================================================
# 1. TANGKAP ARGUMEN DINAMIS DARI PIPELINE
# Tangkap nama file target dari argument pipeline.py
# =====================================================================
target_file_name = sys.argv[1] if len(sys.argv) > 1 else 'DEBUG'

print("=== STARTING DATA AUDIT & ANOMALY DETECTION ===")

# Hubungkan ke database staging sementara
db_conn = duckdb.connect('temp_staging.db')

# =====================================================================
# 2. SELEKSI DATA KOTOR (ANOMALIES)
# Filter record yang melanggar integritas data (Null Customer / Non-positive Price & Qty)
# Read dari tabel 'raw_sales' hasil keluaran standardizer.py
# =====================================================================
dirty_data_query = f"""
	SELECT 
		InvoiceNo, 
		StockCode, 
		Quantity, 
		UnitPrice, 
		CustomerID, 
		'{target_file_name}' AS source_file_name
	FROM raw_sales
	WHERE CustomerID IS NULL
	OR UnitPrice <= 0
	OR Quantity < 0
"""

print("\n--- CALCULATING TOTAL RECORDS ---")
print(db_conn.execute("SELECT COUNT(*) AS total_records FROM raw_sales").df())

print("\n--- CALCULATING DIRTY/INVALID RECORDS ---")
print(db_conn.execute(f"SELECT COUNT(*) AS dirty_records_count FROM ({dirty_data_query})").df())

# =====================================================================
# 3. PENYIMPANAN DATA KOTOR KE MASTER TABLE
# Menggabungkan/append data kotor baru ke tabel penampungan laporan
# =====================================================================
print("\n--- SAVING DIRTY RECORDS FOR BUSINESS AUDIT ---")

db_conn.execute("""
    CREATE TABLE IF NOT EXISTS dirty_records_master (
        InvoiceNo VARCHAR,
        StockCode VARCHAR,
        Quantity INTEGER,
        UnitPrice DOUBLE,
        CustomerID VARCHAR,
        source_file_name VARCHAR
    )
""")

db_conn.execute(f"INSERT INTO dirty_records_master {dirty_data_query}")

# =====================================================================
# 4. EKSPOR LAPORAN ANOMALI KE FILE CSV
# Ekspor ke file CSV lokal jika bukan mode DEBUG
# =====================================================================
if target_file_name == 'DEBUG':
    print("\n[DEBUG MODE] Audit test successful! Data NOT exported to CSV to keep environment clean.")
else:
    db_conn.execute("COPY dirty_records_master TO 'dirty_records_report.csv' (HEADER, DELIMITER ',')")
    print("\n[SUCCESS] Audit completed. Anomaly report generated at 'dirty_records_report.csv'.")