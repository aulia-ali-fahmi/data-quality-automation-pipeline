import duckdb
import sys

print("=== MEMULAI PROSES STANDARISASI KOLOM MENTAH ===")

# 1. TANGKAP ARGUMEN DINAMIS DARI ORCHESTRATOR
# sys.argv[1] adalah tempat mendaratnya variabel nama file yang dilempar dari pipeline.py
if len(sys.argv) < 2:
    print("[FATAL ERROR] Nama file tidak diberikan ke standardizer!")
    sys.exit(1)

file_target = sys.argv[1]
con = duckdb.connect('latihan_QA.db')

try:
    # 2. BACA FILE SECARA DINAMIS (Pakai f-string, bukan hardcode)
    query_load = f"CREATE OR REPLACE TEMPORARY VIEW cek_kolom AS SELECT * FROM read_csv_auto('{file_target}', encoding='latin-1')"
    con.execute(query_load)
    
    info_tabel = con.execute("PRAGMA table_info('cek_kolom')").fetchall()
    kolom_asli_vendor = [baris[1] for baris in info_tabel]
    
    con.execute("DROP TABLE IF EXISTS ritel")

    if 'ID_Pelanggan' in kolom_asli_vendor:
        con.execute("""
            CREATE TABLE ritel AS 
            SELECT InvoiceNo, StockCode, Quantity, UnitPrice, Country,
                   ID_Pelanggan AS CustomerID
            FROM cek_kolom
        """)
        print(f"[SUCCESS] Terdeteksi kolom 'ID_Pelanggan' di file {file_target}. Distandarisasi.")
        
    elif 'CustomerID' in kolom_asli_vendor:
        con.execute("CREATE TABLE ritel AS SELECT * FROM cek_kolom")
        print(f"[SUCCESS] Kolom di file {file_target} sudah sesuai standar internal.")
        
    else:
        print(f"\n[FATAL ERROR] Kolom identitas tidak ditemukan di {file_target}!")
        sys.exit(1)

except Exception as e:
    print(f"\n[FATAL ERROR] Proses standarisasi gagal: {e}")
    sys.exit(1)