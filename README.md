# Data Quality & Automated ETL Pipeline

An end-to-end, idempotent Data Engineering pipeline built with Python and DuckDB. This project automates raw data ingestion, column standardization, anomaly auditing, business transformation, and automated QA testing.

## System Architecture & Data Flow

```text
[ Input Raw CSV ]
       │
       ▼
[ standardizer.py ]  --> Standardize dynamic schemas
       │
       ▼
[ audit.py ]         --> Isolate corrupt rows to CSV report
       │
       ▼
[ transform.py ]     --> Calculate net sales & export to Parquet
       │
       ▼
[ qa_test.py ]       --> Enforce hard assertions & tripwires
       │
       ▼
[ reporter.py ]      --> Load to DuckDB warehouse & output BI metrics
```

## Key Technical Features

* **Idempotency Engine:** Prevents duplicate processing of incoming CSV files using DuckDB execution logs (`processed_files_log`).
* **Automated Anomaly Isolation:** Filters out invalid customer records, zero/negative pricing, and non-positive quantities into a quarantine reporting layer (`dirty_records_report.csv`).
* **Clean Data Mart Storage:** Transforms valid transactional data into Parquet format (`analytics_ready_data.parquet`) and loads it into the production warehouse (`main_warehouse.duckdb`).
* **Automated QA & Business Tripwires:** Executes hard assertions for structural integrity and soft warnings for potential fraudulent/high-volume transactions before loading to BI tables.

## Project Structure

* `pipeline.py` — Main orchestrator managing execution flow, logging, and warehousing.
* `standardizer.py` — Raw data ingestion and dynamic schema unification.
* `audit.py` — Anomaly isolation and business audit reporting.
* `transform.py` — Metric calculation (`Total_Price`) and Parquet export.
* `qa_test.py` — Automated QA testing suite with hard & soft assertions.
* `reporter.py` — BI layer reporting executive business metrics.

## How to Run

1. Clone the repository:
   ```bash
   git clone https://github.com/aulia-ali-fahmi/data-quality-automation-pipeline.git
   cd data-quality-automation-pipeline
2. Create and activate a virtual environment:
    * Windows:
       ```bash
       python -m venv .venv
       .venv\Scripts\activate
    * macOS / Linux:
       ```bash
       python3 -m venv .venv
       source .venv/bin/activate
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
4. Execute the pipeline to process the prepared sample dataset (`input/data.csv`):
   ```bash
   python pipeline.py
