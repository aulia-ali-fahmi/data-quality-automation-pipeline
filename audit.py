import duckdb
import sys

# Tangkap nama file dari pipeline
nama_file = sys.argv[1] if len(sys.argv) > 1 else 'DEBUG'

print("Memuat dataset E-Commerce UK...")
con = duckdb.connect('latihan_QA.db')

# 1. Query kotor dengan 5 kolom dasar + 1 kolom penanda asal file
query_kotor = f"""
	SELECT 
		InvoiceNo, 
		StockCode, 
		Quantity, 
		UnitPrice, 
		CustomerID, 
		'{nama_file}' AS nama_file_asal
	FROM ritel
	WHERE CustomerID IS NULL
	OR UnitPrice <= 0
	OR Quantity < 0
"""

print("\n--- MENGHITUNG TOTAL DATA ---")
print(con.execute("SELECT COUNT(*) AS total_semua_data FROM ritel").df())

print("\n--- MENGHITUNG DATA KOTOR ---")
print(con.execute(f"SELECT COUNT(*) AS total_kotor FROM ({query_kotor})").df())

print("\n--- MENYIMPAN DATA KOTOR KE CSV UNTUK DI-AUDIT TIM BISNIS ---")

# 2. Buat tabel jika belum ada (tanpa auto insert)
con.execute("""
    CREATE TABLE IF NOT EXISTS laporan_kotor_master (
        InvoiceNo VARCHAR,
        StockCode VARCHAR,
        Quantity INTEGER,
        UnitPrice DOUBLE,
        CustomerID VARCHAR,
        nama_file_asal VARCHAR
    )
""")

# 3. Masukkan (Append) data kotor baru ke tabel master
con.execute(f"INSERT INTO laporan_kotor_master {query_kotor}")

# 3. Simpan seluruh tabel master ke CSV
if nama_file == 'DEBUG':
    print("\n[DEBUG MODE] Tes audit sukses! Data TIDAK diekspor ke CSV agar file laporan tidak kotor.")
else:
    con.execute("COPY laporan_kotor_master TO 'laporan_kotor_uk.csv' (HEADER, DELIMITER ',')")
    print("\nSelesai! Laporan kotor berhasil dibuat.")