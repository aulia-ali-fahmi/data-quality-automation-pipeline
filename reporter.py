import duckdb

print("=== GENERATING EXECUTIVE REPORT (BI LAYER) ===")

# Hubungkan langsung ke Database Main Warehouse (DuckDB Permanen)
con = duckdb.connect('data_mart/main_warehouse.duckdb')

# Query analitik untuk merangkum performa bisnis dari tabel sales_dashboard
executive_report_query = """
    SELECT 
        COUNT(InvoiceNo) AS total_clean_transactions,
        ROUND(SUM(Total_Price), 2) AS total_revenue_gbp,
        ROUND(AVG(Total_Price), 2) AS average_order_value,
        COUNT(DISTINCT CustomerID) AS total_unique_customers
    FROM sales_dashboard
"""

# Eksekusi dan ubah hasil query ke DataFrame
report_results = con.execute(executive_report_query).df()

print("\n" + "="*60)
print("       EXECUTIVE RETAIL BUSINESS PERFORMANCE REPORT")
print("="*60)
print(report_results.to_string(index=False))
print("="*60)
print("[SUCCESS] Executive report generated successfully from DuckDB Warehouse.")

con.close()