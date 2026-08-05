import duckdb

print("=== MENYUSUN LAPORAN EKSEKUTIF (BI LAYER) ===")

# Hubungkan langsung ke Database Permanen Utama (Bukan database sementara)
con = duckdb.connect('data_mart/database_utama.duckdb')

# Query analitik untuk merangkum performa bisnis dari tabel sales_dashboard
query_laporan = """
    SELECT 
        COUNT(InvoiceNo) AS total_transaksi_bersih,
        ROUND(SUM(Total_Harga), 2) AS total_pendapatan_gbp,
        ROUND(AVG(Total_Harga), 2) AS rata_rata_nilai_transaksi,
        COUNT(DISTINCT CustomerID) AS total_pelanggan_unik
    FROM sales_dashboard
"""

# Eksekusi dan ubah jadi DataFrame
hasil_laporan = con.execute(query_laporan).df()

print("\n" + "="*50)
print("         LAPORAN KESEHATAN & PERFORMA BISNIS RITEL")
print("="*50)
print(hasil_laporan.to_string(index=False))
print("="*50)
print("[SUCCESS] Laporan eksekutif berhasil digenerate secara otomatis dari DuckDB.")

con.close()