import duckdb
import logging

print("=== STARTING QA AUTOMATED TESTING ON CLEAN DATASET ===")

# Membuka koneksi database DuckDB dalam memori untuk pengujian
db_conn = duckdb.connect()

# =====================================================================
# 1. MEMATIKAN & MEMBACA PARQUET DATASET BERSIH
# Read dari Parquet hasil ekspor transform.py
# =====================================================================
db_conn.execute("CREATE TABLE data_final AS SELECT * FROM read_parquet('data_mart/analytics_ready_data.parquet')")

# Query validasi integritas data dasar (Null & Non-positive values)
null_check_query = """
    SELECT COUNT(*) 
    FROM data_final 
    WHERE CustomerID IS NULL 
       OR CustomerID = '' 
       OR CustomerID = '0'
"""
negative_price_query = "SELECT COUNT(*) FROM data_final WHERE Total_Price <= 0 OR Total_Price IS NULL"

# =====================================================================
# 2. QUERY TRIPWIRE BISNIS (ANOMALI FRAUD & BULK BUYER)
# Detect pembelian berlebih (reseller/bot) dan transaksi bernilai ekstrem
# =====================================================================
fraud_quantity_query = "SELECT COUNT(*) FROM data_final WHERE Quantity > 10000"
fraud_price_query = "SELECT COUNT(*) FROM data_final WHERE Total_Price > 100000"

# Eksekusi kalkulasi metric pengetesan
null_count = db_conn.execute(null_check_query).fetchone()[0]
negative_count = db_conn.execute(negative_price_query).fetchone()[0]
fraud_qty_count = db_conn.execute(fraud_quantity_query).fetchone()[0]
fraud_price_count = db_conn.execute(fraud_price_query).fetchone()[0]

# =====================================================================
# 3. HARD ASSERTIONS (Gagal total / Hentikan Pipeline jika ada kebocoran)
# =====================================================================
assert null_count == 0, f"[FATAL ERROR] QA FAILED: Found {null_count} invalid records in CustomerID column!"
assert negative_count == 0, f"[FATAL ERROR] QA FAILED: Found {negative_count} invalid records in transaction totals!"

# =====================================================================
# 4. SOFT ASSERTIONS / WARNING BISNIS (Pipeline tetap jalan, catat di Log)
# =====================================================================
if fraud_qty_count > 0:
    qty_warning_msg = f"[WARNING] Found {fraud_qty_count} transactions with Quantity > 10,000! Check for potential bot activity."
    print(qty_warning_msg)
    logging.warning(qty_warning_msg)

if fraud_price_count > 0:
    price_warning_msg = f"[WARNING] Found {fraud_price_count} transactions with Total Price > 100,000 GBP! Check price validity."
    print(price_warning_msg)
    logging.warning(price_warning_msg)

print("[SUCCESS] QA PASSED: Dataset 100% clean from Null/Negative values. Business tripwires verified successfully.")