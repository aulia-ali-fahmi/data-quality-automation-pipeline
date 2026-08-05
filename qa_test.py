import duckdb
import logging

print("Menjalankan QA Automated Testing pada Data Bersih...")
con = duckdb.connect()

# Kita tes file CSV yang baru aja lo bersihin di langkah sebelumnya
con.execute("CREATE TABLE data_final AS SELECT * FROM read_parquet('data_mart/data_siap_analisis.parquet')")

query_cek_null = """
    SELECT COUNT(*) 
    FROM data_final 
    WHERE CustomerID IS NULL 
       OR CustomerID = '' 
       OR CustomerID = '0'
"""
query_cek_minus = "SELECT COUNT(*) FROM data_final WHERE Total_Harga <= 0 OR Total_Harga IS NULL"

# [TAMBAHAN] 1. Tripwire Fraud: Mengecek apakah ada pembelian tidak wajar (> 10.000 item per transaksi)
query_cek_fraud_quantity = "SELECT COUNT(*) FROM data_final WHERE Quantity > 10000"

# [TAMBAHAN] 2. Tripwire Paus (Whale): Mengecek apakah ada transaksi dengan nilai > 100.000 GBP (indikasi salah harga atau B2B bulk buying tak terduga)
query_cek_fraud_harga = "SELECT COUNT(*) FROM data_final WHERE Total_Harga > 100000"

jumlah_null = con.execute(query_cek_null).fetchone()[0]
jumlah_minus = con.execute(query_cek_minus).fetchone()[0]
jumlah_fraud_qty = con.execute(query_cek_fraud_quantity).fetchone()[0]
jumlah_fraud_harga = con.execute(query_cek_fraud_harga).fetchone()[0]

# HARD ASSERTION (Pipeline Mati kalau melanggar ini)
assert jumlah_null == 0, f"[FATAL ERROR] QA FAILED: Ditemukan {jumlah_null} kesalahan data pada kolom CustomerID!"
assert jumlah_minus == 0, f"[FATAL ERROR] QA FAILED: Ditemukan {jumlah_minus} kesalahan data pada kolom transaksi!"

# SOFT ASSERTION / BUSINESS WARNING (Pipeline lanjut, tapi catat di log merah)
if jumlah_fraud_qty > 0:
    pesan_fraud_qty = f"[WARNING] Ditemukan {jumlah_fraud_qty} transaksi dengan Quantity > 10.000! Cek indikasi bot/reseller."
    print(pesan_fraud_qty)
    logging.warning(pesan_fraud_qty)

if jumlah_fraud_harga > 0:
    pesan_fraud_harga = f"[WARNING] Ditemukan {jumlah_fraud_harga} transaksi dengan Total Harga > 100.000 GBP! Cek validitas harga."
    print(pesan_fraud_harga)
    logging.warning(pesan_fraud_harga)

print("[SUCCESS] QA PASSED: Data 100% Bersih dari Null/Minus. Business Tripwire selesai diperiksa.")