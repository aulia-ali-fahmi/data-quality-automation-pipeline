import duckdb
import sys

# Tangkap nama file dari pipeline
nama_file = sys.argv[1] if len(sys.argv) > 1 else 'DEBUG'

print("Memulai proses Transformasi Data (ETL)...")
con = duckdb.connect('latihan_QA.db')

# 1. Menyiapkan query bersih + MENAMBAHKAN PENANDA NAMA FILE ASAL
query_bersih = f"""
	SELECT
		InvoiceNo,
		StockCode,
		Quantity,
		UnitPrice,
		CustomerID,
		(Quantity * UnitPrice) AS Total_Harga,
		'{nama_file}' AS nama_file_asal
	FROM ritel
	WHERE CustomerID IS NOT NULL
		AND UnitPrice > 0
		AND Quantity > 0
"""

# 2. Buat struktur tabel master bersih tanpa isi (WHERE 1=0) jika belum ada
con.execute("""
    CREATE TABLE IF NOT EXISTS ritel_bersih_master (
        InvoiceNo VARCHAR,
        StockCode VARCHAR,
        Quantity INTEGER,
        UnitPrice DOUBLE,
        CustomerID VARCHAR,
        Total_Harga DOUBLE,
        nama_file_asal VARCHAR
    )
""")

# 3. Masukkan (Append) data bersih baru ke tabel master
con.execute(f"INSERT INTO ritel_bersih_master {query_bersih}")

print("\n--- TOTAL DATA BERSIH SIAP PAKAI ---")
print(con.execute("SELECT COUNT(*) AS jumlah_bersih FROM ritel_bersih_master").df())

print("\n--- 5 BARIS TERATAS DATA BERSIH ---")
print(con.execute("SELECT * FROM ritel_bersih_master LIMIT 5").df())

print("\n--- TOTAL PENJUALAN BERSIH (DALAM GBP) ---")
print(con.execute("SELECT SUM(Total_Harga) AS total_penjualan_bersih_gbp FROM ritel_bersih_master").df())

print("\n--- MENYIMPAN DATA BERSIH KE FORMAT PARQUET ---")

# 4. Ekspor tabel master menjadi file Parquet yang super ringan dan cepat
if nama_file == 'DEBUG':
    print("\n[DEBUG MODE] Tes transformasi sukses! Data TIDAK diekspor ke Parquet agar data_mart tidak kotor.")
else:
    con.execute("COPY ritel_bersih_master TO 'data_mart/data_siap_analisis.parquet' (FORMAT PARQUET)")
    print("\n[SUCCESS] Selesai! Data siap dipakai oleh mesin AI dan Dasbor.")