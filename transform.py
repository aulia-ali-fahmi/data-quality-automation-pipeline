import duckdb
import sys

# =====================================================================
# 1. TANGKAP ARGUMEN DINAMIS DARI PIPELINE
# Tangkap nama file target dari argument pipeline.py
# =====================================================================
target_file_name = sys.argv[1] if len(sys.argv) > 1 else 'DEBUG'

print("=== STARTING DATA TRANSFORMATIONAL ETL PROCESS ===")

# Hubungkan ke database staging sementara
db_conn = duckdb.connect('temp_staging.db')

# =====================================================================
# 2. FILTER & TRANSFORMASI DATA BERSIH
# Menyeleksi data valid serta menghitung kalkulasi bisnis (Total_Price)
# Read dari tabel 'raw_sales' hasil keluaran standardizer.py
# =====================================================================
clean_data_query = f"""
	SELECT
		InvoiceNo,
		StockCode,
		Quantity,
		UnitPrice,
		CustomerID,
		(Quantity * UnitPrice) AS Total_Price,
		'{target_file_name}' AS source_file_name
	FROM raw_sales
	WHERE CustomerID IS NOT NULL
		AND UnitPrice > 0
		AND Quantity > 0
"""

# =====================================================================
# 3. PENYIMPANAN KE MASTER CLEAN TABLE
# Menggabungkan/append data bersih baru ke tabel master penampungan
# =====================================================================
db_conn.execute("""
    CREATE TABLE IF NOT EXISTS clean_sales_master (
        InvoiceNo VARCHAR,
        StockCode VARCHAR,
        Quantity INTEGER,
        UnitPrice DOUBLE,
        CustomerID VARCHAR,
        Total_Price DOUBLE,
        source_file_name VARCHAR
    )
""")

db_conn.execute(f"INSERT INTO clean_sales_master {clean_data_query}")

print("\n--- TOTAL CLEAN RECORDS READY FOR ANALYSIS ---")
print(db_conn.execute("SELECT COUNT(*) AS clean_records_count FROM clean_sales_master").df())

print("\n--- TOP 5 ROWS OF CLEAN DATA ---")
print(db_conn.execute("SELECT * FROM clean_sales_master LIMIT 5").df())

print("\n--- TOTAL NET SALES (IN GBP) ---")
print(db_conn.execute("SELECT SUM(Total_Price) AS total_net_sales_gbp FROM clean_sales_master").df())

# =====================================================================
# 4. EKSPOR DATA BERSIH KE FORMAT PARQUET
# Ekspor ke file Parquet di folder data_mart jika bukan mode DEBUG
# =====================================================================
print("\n--- EXPORTING CLEAN DATA TO PARQUET FORMAT ---")

if target_file_name == 'DEBUG':
    print("\n[DEBUG MODE] Transformation test successful! Data NOT exported to Parquet to keep data_mart clean.")
else:
    # DISESUAIKAN: Nama file Parquet diubah ke Bahasa Inggris standar
    db_conn.execute("COPY clean_sales_master TO 'data_mart/analytics_ready_data.parquet' (FORMAT PARQUET)")
    print("\n[SUCCESS] Transformation completed. Clean dataset exported to 'data_mart/analytics_ready_data.parquet'.")