# SkyPoints Airline Loyalty Data Platform
### *Incubyte Technical Assessment — Data Craftsperson*

**Candidate:** Sirajuddin Kamaluddin  
**Role:** Data Craftsperson  
**Email:** [siraj.kamaluddin@gmail.com](mailto:siraj.kamaluddin@gmail.com)  
**Repository:** [https://github.com/siraj2001/assesment](https://github.com/siraj2001/assesment)  

[![Tests](https://img.shields.io/badge/pytest-23%20passed%20(100%25)-success?style=for-the-badge&logo=pytest)](tests/)
[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Snowflake](https://img.shields.io/badge/Snowflake-Enterprise%20SQL-29B5E8?style=for-the-badge&logo=snowflake)](sql/snowflake/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Embedded%20Engine-FFF000?style=for-the-badge&logo=duckdb)](https://duckdb.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Medallion%20(Lakehouse)-8A2BE2?style=for-the-badge)](docs/ARCHITECTURE.md)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

## 📑 Table of Contents
1. [Executive Summary & Problem Statement](#-executive-summary--problem-statement)
2. [Assessment Deliverables Matrix](#-assessment-deliverables-matrix)
3. [Architecture & Scale-to-Billions Design](#-architecture--scale-to-billions-design)
4. [Dirty Data Findings & Quarantine Engine](#-dirty-data-findings--quarantine-engine)
5. [Core Engineering Solutions](#-core-engineering-solutions)
   - [Deliverable 1: Table DDL Queries](#deliverable-1-table-ddl-queries)
   - [Deliverable 2: Staging Layer & Derived Columns](#deliverable-2-staging-layer--derived-columns)
   - [Deliverable 3: Country Splitting & Latest Record Wins](#deliverable-3-country-splitting--latest-record-wins)
   - [Deliverable 4: JSON Redemptions & Fan-Out Solution](#deliverable-4-json-redemptions--fan-out-solution)
   - [Deliverable 5: Data Validations & Integrity Suite](#deliverable-5-data-validations--integrity-suite)
   - [Deliverable 6: Interactive Live Demonstration](#deliverable-6-interactive-live-demonstration)
6. [Quickstart Setup & Execution Guide](#-quickstart-setup--execution-guide)
7. [Automated TDD Test Suite (23/23 Passing)](#-automated-tdd-test-suite-2323-passing)
8. [Interactive Web Demonstration UI](#-interactive-web-demonstration-ui)
9. [Repository Structure](#-repository-structure)
10. [Git Evolution History](#-git-evolution-history)

---

## 🛫 Executive Summary & Problem Statement

SkyPoints is a global airline loyalty program with millions of members, partner airline lounges, and daily mileage redemption transactions worldwide. Every day, the source system extracts:
1. **A daily flat file** containing member profile data with pipe delimiters (`|H|` header and `|D|` detail records).
2. **A daily semi-structured JSON feed** containing mileage redemptions from partner airlines (e.g., AeroLink, AirIndia, Qantas).

### Assessment Objective
Build an enterprise data engineering solution to:
- Model raw, staging, and per-country target tables in **Snowflake**.
- Compute derived attributes: `Age` (from DOB) and a `Stale_Member` flag (days since Flight_Date > 90).
- Dedup members and route them to country-specific target tables (`TABLE_USA`, `TABLE_IND`, `TABLE_AUS`, etc.) using the **"Latest Record Wins"** rule when a member migrates countries.
- Flatten semi-structured JSON redemptions and join them back to member profiles without data duplication.
- Build a resilient data quality firewall with a **Dead-Letter Queue (DLQ)** to isolate real-world dirty data (such as month 13 dates, unpadded integers, and string `'NULL'` literals).
- Provide automated tests and a live interactive demo for the interview.

---

## 🎯 Assessment Deliverables Matrix

| Deliverable | Technical Requirement | Snowflake SQL Implementation | Local Python / DuckDB Engine | Automated Test Suite |
|---|---|---|---|---|
| **1. Table Queries (DDL)** | Raw/landing, staging, and country-specific target tables | [`01_raw_ddl.sql`](sql/snowflake/01_raw_ddl.sql)<br>[`02_staging_ddl.sql`](sql/snowflake/02_staging_ddl.sql)<br>[`03_country_targets_ddl.sql`](sql/snowflake/03_country_targets_ddl.sql)<br>[`04_redemptions_ddl.sql`](sql/snowflake/04_redemptions_ddl.sql) | [`models.py`](src/skypoints/models.py)<br>[`pipeline.py`](src/skypoints/pipeline.py) | [`test_end_to_end.py`](tests/test_end_to_end.py) |
| **2. Staging Load & Derived Columns** | `Age` (computed from DOB) and `Stale_Member` flag (days since Flight_Date > 90) | [`05_staging_load.sql`](sql/snowflake/05_staging_load.sql) | [`staging.py`](src/skypoints/processing/staging.py)<br>[`date_utils.py`](src/skypoints/processing/date_utils.py) | [`test_staging.py`](tests/test_staging.py)<br>[`test_date_utils.py`](tests/test_date_utils.py) |
| **3. Country Splitting & Latest Record Wins** | Route members into country target tables; apply "latest record wins" on country migration | [`06_latest_record_wins.sql`](sql/snowflake/06_latest_record_wins.sql) | [`deduplication.py`](src/skypoints/processing/deduplication.py)<br>[`country_router.py`](src/skypoints/processing/country_router.py) | [`test_deduplication.py`](tests/test_deduplication.py) |
| **4. JSON Redemption Feed Parsing & Join** | Flatten nested JSON redemptions and join back to member profiles (1-to-1 safe join) | [`07_json_redemptions_flatten.sql`](sql/snowflake/07_json_redemptions_flatten.sql) | [`redemptions.py`](src/skypoints/processing/redemptions.py)<br>[`json_reader.py`](src/skypoints/ingestion/json_reader.py) | [`test_redemptions.py`](tests/test_redemptions.py) |
| **5. Data Validations & Quality Suite** | Mandatory field checks, key-column uniqueness, and dirty data anomaly isolation | [`08_data_validations.sql`](sql/snowflake/08_data_validations.sql) | [`validator.py`](src/skypoints/validation/validator.py)<br>[`legacy_reader.py`](src/skypoints/ingestion/legacy_reader.py) | [`test_validations.py`](tests/test_validations.py)<br>[`test_legacy_readers.py`](tests/test_legacy_readers.py) |
| **6. Live Demonstration** | Interactive runner for live interview demonstration | — | [`cli.py`](src/skypoints/cli.py)<br>[`server.py`](demo/server.py)<br>[`index.html`](demo/index.html) | [Interview Demo Guide](docs/INTERVIEW_DEMO_GUIDE.md) |

---

## 🏛️ Architecture & Scale-to-Billions Design

```mermaid
flowchart TD
    subgraph Sources ["1. Daily Ingestion Feeds"]
        S1["Flat File: Member Profiles\n(|H| Header, |D| Detail)"]
        S2["JSON Feed: Partner Redemptions\n(Semi-Structured API / Stream)"]
        S3["Heterogeneous Files\n(USA.csv, IND.csv, AUS.xlsx)"]
    end

    subgraph Bronze ["2. Bronze Layer (Raw Landing)"]
        B1[("RAW_MEMBER_PROFILES_LANDING\n(Unparsed VARCHAR lines + Metadata)")]
        B2[("RAW_REDEMPTION_FEED_LANDING\n(Snowflake native VARIANT)")]
    end

    subgraph Silver ["3. Silver Layer (Cleansed & Enriched)"]
        V1{"Data Validation &\nIntegrity Firewall"}
        Q[("QUARANTINE_REJECTED_RECORDS\n(DLQ: Line #, Error Code, Payload)")]
        S_STG[("STG_MEMBER_PROFILES\n+ Derived AGE (from DOB)\n+ Derived STALE_MEMBER (>90d)")]
    end

    subgraph Dedup ["4. Deduplication Engine"]
        D1{"Latest Record Wins\nROW_NUMBER() OVER\n(PARTITION BY member_id\nORDER BY last_flight_date DESC)"}
    end

    subgraph Gold ["5. Gold Layer (Target Marts & Analytics)"]
        G_USA[("TABLE_USA")]
        G_IND[("TABLE_IND")]
        G_AUS[("TABLE_AUS")]
        G_CAN[("TABLE_CAN")]
        G_PHIL[("TABLE_PHIL")]
        G_GLOBAL[("DIM_MEMBERS_GLOBAL\n(Clustered Enterprise Mart)")]
        F_RED[("FCT_MILEAGE_REDEMPTIONS\n(Flattened Txn Fact)")]
        A_RED[("AGG_MEMBER_REDEMPTION_METRICS\n(1-to-1 Rollup Mart)")]
        V_360[("V_MEMBER_360\n(Safe 1-to-1 Enriched View)")]
    end

    S1 --> B1
    S3 --> B1
    S2 --> B2
    B1 --> V1
    V1 -- "Malformed Records" --> Q
    V1 -- "Valid Records" --> S_STG
    S_STG --> D1
    D1 --> G_USA
    D1 --> G_IND
    D1 --> G_AUS
    D1 --> G_CAN
    D1 --> G_PHIL
    D1 --> G_GLOBAL
    B2 --> F_RED
    F_RED --> A_RED
    G_GLOBAL --> V_360
    A_RED --> V_360
```

### How This Scales to Billions of Records Per Day
1. **Zero-Transformation Ingestion via Snowpipe**: Daily flat files and JSON feeds are compressed (`zstd` / `gzip`) in 100–250MB chunks in cloud object storage (S3/Azure Blob/GCS) and loaded via Snowpipe directly into unparsed `VARCHAR` and `VARIANT` tables. This guarantees zero ingest transform bottleneck.
2. **Snowflake Clustering Keys**: Staging and Gold tables are clustered by `(COUNTRY, TIER_CODE)` or `MEMBER_ID`. Snowflake's micro-partition pruning automatically skips 95%+ of partitions during query execution.
3. **Incremental Batch Deduplication**: Running window functions over a historical table of billions of records causes memory spills. Our architecture dedups **strictly across the incremental daily batch**, followed by an idempotent `MERGE INTO` the target country tables.
4. **Enterprise Clustered Dimension vs. 195 Physical Tables**: In [03_country_targets_ddl.sql](sql/snowflake/03_country_targets_ddl.sql), we provide both the requested physical tables (`TABLE_USA`, `TABLE_IND`, etc.) populated via **Multi-Table Insert (`INSERT ALL`)**, and a single clustered `DIM_MEMBERS_GLOBAL` table with **Secure Views** to eliminate schema drift across 195+ countries.

*For full architectural decisions, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).*

---

## 🛡️ Dirty Data Findings & Quarantine Engine

In analyzing the files supplied in the assessment email (`USA.csv`, `IND.csv`, `AUS.xlsx`, and `DE_Assessment_file.pdf`), several real-world data entropy issues were uncovered and solved:

```
                      Incoming Raw Records
                                │
                                ▼
                   ┌──────────────────────────┐
                   │ Mandatory Fields Check:  │
                   │  - MEMBER_NAME not empty │
                   │  - MEMBER_ID not empty   │
                   │  - ENROLL_DATE not empty │
                   └────────────┬─────────────┘
                                │
                  ┌─────────────┴─────────────┐
                  ▼                           ▼
               [Valid]                    [Invalid]
                  │                           │
       ┌───────────────────────┐   ┌────────────────────────────────┐
       │ Format Normalization: │   │ Dead-Letter Queue (DLQ):       │
       │  - LPAD unpadded ints │   │  - QUARANTINE_REJECTED_RECORDS │
       │  - Sanitize 'NULL'    │   │  - Captures exact file & line  │
       │  - Flexible date mask │   │  - Descriptive ERROR_CODE      │
       └──────────┬────────────┘   └────────────────────────────────┘
                  │
                  ▼
       Silver Staging & Gold Target Marts
```

| Source File | Raw Anomaly Detected | Issue Classification | Impact & Handling |
|---|---|---|---|
| **`AUS.xlsx`** | Row 2: `'2021-13-13'` | **Invalid Date (Month 13)** | Physically impossible date. Quarantined to `QUARANTINE_REJECTED_RECORDS` with `ERR_INVALID_DATE` without failing the pipeline. |
| **`AUS.xlsx`** | Row 1: `'NULL'` in DOB | **Null String Literal** | String `'NULL'` sanitized cleanly to SQL `NULL`. |
| **`USA.csv`** | `6152022`, `1052022` | **Unpadded Integer / Stripped Zero** | Dates lost leading zeroes (length 7). Padded to length 8 (`06152022`) to parse accurately as June 15, 2022. |
| **`USA.csv`** | 5 columns only | **Schema Drift** | Missing DOB, Country, State. Populates known fields and defaults missing columns to `NULL`. |
| **`IND.csv`** | `12/1/1998`, `6/15/2022` | **Slash Date Formatting** | Non-standard format parsed seamlessly via multi-format date parser. |
| **`IND.csv`** | `Individual or Corporate` | **Undocumented Extra Column** | Source added extra column. Ingestion maps known columns without failure. |
| **`PDF Sample`**| `3051985` vs `03051985` | **Lost Leading Zero in DOB** | Database integer conversion error. Enforces `LPAD(TRIM(dob), 8, '0')` in SQL and Python. |

*For complete data quality analysis, see [docs/DATA_QUALITY_REPORT.md](docs/DATA_QUALITY_REPORT.md).*

---

## 🔧 Core Engineering Solutions

### Deliverable 1: Table DDL Queries
- **Raw Landing Layer**:
  - [`01_raw_ddl.sql`](sql/snowflake/01_raw_ddl.sql): `RAW_MEMBER_PROFILES_LANDING` (stores unparsed lines with audit metadata) and `RAW_REDEMPTION_FEED_LANDING` (stores semi-structured JSON in native `VARIANT`).
- **Silver Staging Layer**:
  - [`02_staging_ddl.sql`](sql/snowflake/02_staging_ddl.sql): `STG_MEMBER_PROFILES` with strongly-typed columns, derived `AGE`, derived `STALE_MEMBER`, and `QUARANTINE_REJECTED_RECORDS` (Dead-Letter Queue).
- **Gold Target Layer**:
  - [`03_country_targets_ddl.sql`](sql/snowflake/03_country_targets_ddl.sql): Country-specific tables (`TABLE_USA`, `TABLE_IND`, `TABLE_AUS`, `TABLE_CAN`, `TABLE_PHIL`) and `DIM_MEMBERS_GLOBAL`.
  - [`04_redemptions_ddl.sql`](sql/snowflake/04_redemptions_ddl.sql): `FCT_MILEAGE_REDEMPTIONS` and `AGG_MEMBER_REDEMPTION_METRICS`.

### Deliverable 2: Staging Layer & Derived Columns
In [`05_staging_load.sql`](sql/snowflake/05_staging_load.sql) and [`staging.py`](src/skypoints/processing/staging.py):
1. **`Age` Computation**: Calculated from DOB to reference date, handling leap years and unpadded 7-digit strings:
   ```sql
   CASE 
       WHEN dob IS NOT NULL THEN DATEDIFF(year, dob, $BATCH_DATE)
       ELSE NULL 
   END AS AGE
   ```
2. **`Stale_Member` Flag**: Evaluates if days since `LAST_FLIGHT_DATE` > 90, or if the member has never flown:
   ```sql
   CASE 
       WHEN last_flight_date IS NULL THEN 'Y'
       WHEN DATEDIFF(day, last_flight_date, $BATCH_DATE) > 90 THEN 'Y'
       ELSE 'N'
   END AS STALE_MEMBER
   ```

### Deliverable 3: Country Splitting & Latest Record Wins
In [`06_latest_record_wins.sql`](sql/snowflake/06_latest_record_wins.sql) and [`deduplication.py`](src/skypoints/processing/deduplication.py):
- Members moving countries are resolved using a window function:
  ```sql
  ROW_NUMBER() OVER (
      PARTITION BY MEMBER_ID 
      ORDER BY 
          COALESCE(LAST_FLIGHT_DATE, DATE '1970-01-01') DESC,
          ENROLLMENT_DATE DESC,
          STAGING_TIMESTAMP DESC
  ) AS rank_order
  ```
- Elena originally registered in the USA (`2012-10-13`), but later flew into Canada (`2023-12-01`). The engine places Elena into `TABLE_CAN` and deduplicates her from `TABLE_USA`.
- High-throughput country routing uses Snowflake's `INSERT ALL` to populate all country tables in a single table scan.

### Deliverable 4: JSON Redemptions & Fan-Out Solution
In [`07_json_redemptions_flatten.sql`](sql/snowflake/07_json_redemptions_flatten.sql) and [`redemptions.py`](src/skypoints/processing/redemptions.py):
- Semi-structured JSON feeds are flattened using Snowflake `LATERAL FLATTEN(input => raw:redemptions)` into `FCT_MILEAGE_REDEMPTIONS`.
- **Solving the Fan-Out Dilemma**: Joining 1-to-many transaction records directly to member profiles multiplies member rows (Cartesian explosion) and distorts KPI reports. We pre-aggregate transactions into `AGG_MEMBER_REDEMPTION_METRICS` at the member grain and join at **1-to-1 cardinality** to produce `V_MEMBER_360`:
  ```sql
  CREATE OR REPLACE VIEW V_MEMBER_360 AS
  SELECT 
      m.*,
      COALESCE(r.LIFETIME_REDEMPTIONS, 0) AS LIFETIME_REDEMPTIONS,
      COALESCE(r.TOTAL_MILES_REDEEMED, 0) AS TOTAL_MILES_REDEEMED,
      r.TOP_PARTNER
  FROM TABLE_USA m
  LEFT JOIN AGG_MEMBER_REDEMPTION_METRICS r ON m.MEMBER_ID = r.MEMBER_ID;
  ```

### Deliverable 5: Data Validations & Integrity Suite
In [`08_data_validations.sql`](sql/snowflake/08_data_validations.sql) and [`validator.py`](src/skypoints/validation/validator.py):
- **Mandatory Field Checks**: Flags null or empty `Member_Name`, `Member_Id`, or `Enrollment_Date`.
- **Key Uniqueness & Identity Collision**: Flags duplicate `Member_Id` entries and detects if a single `Member_Id` has multiple different `Member_Name`s.
- **Domain Sanity Checks**: Validates that Age is between 0 and 120, flights do not precede enrollment, and redemption miles are strictly positive.
- **Quarantine DLQ**: All failing rows are isolated with error codes (`ERR_MANDATORY_NAME_MISSING`, `ERR_INVALID_DATE`, etc.).

### Deliverable 6: Interactive Live Demonstration
Provides two interactive tools for the interview:
1. **Rich Terminal CLI** ([`cli.py`](src/skypoints/cli.py)): Colored terminal tables, summary statistics, and table inspection commands.
2. **Live Web Dashboard** ([`server.py`](demo/server.py) + [`index.html`](demo/index.html)): Browser-based interactive dashboard with live query console and real-time test runner.

*See [docs/INTERVIEW_DEMO_GUIDE.md](docs/INTERVIEW_DEMO_GUIDE.md) for the live interview presentation script.*

---

## ⚡ Quickstart Setup & Execution Guide

### 1. Clone the Repository
```bash
git clone https://github.com/siraj2001/assesment.git
cd assesment
```

### 2. Install Dependencies
```bash
pip install -e .
```

### 3. Run Automated Tests (TDD Verification)
```bash
pytest -v
```

### 4. Run the Pipeline via Terminal CLI
```bash
# Execute end-to-end batch processing
python -m skypoints.cli run

# Inspect Canada table (showing Elena's migration)
python -m skypoints.cli inspect --table TABLE_CAN

# Inspect the Quarantine Dead-Letter Queue
python -m skypoints.cli inspect --table QUARANTINE_REJECTED_RECORDS

# Inspect Member 360 Enriched Profile View
python -m skypoints.cli inspect --table V_MEMBER_360
```

### 5. Launch Interactive Live Demonstration Web Dashboard
```bash
python -m uvicorn demo.server:app --port 8000 --reload
```
Open **`http://localhost:8000`** in your browser to access the live dashboard during the interview.

---

## 🧪 Automated TDD Test Suite (23/23 Passing)

```text
============================= test session starts =============================
platform win32 -- Python 3.12.9, pytest-9.1.1, pluggy-1.7.0
rootdir: E:\Personal\Jobs\incubyrte
configfile: pyproject.toml
testpaths: tests
collected 23 items

tests/test_date_utils.py::test_parse_standard_yyyymmdd PASSED            [  4%]
tests/test_date_utils.py::test_parse_standard_mmddyyyy PASSED            [  8%]
tests/test_date_utils.py::test_parse_unpadded_seven_digit_date PASSED    [ 13%]
tests/test_date_utils.py::test_parse_slash_dates PASSED                  [ 17%]
tests/test_date_utils.py::test_parse_datetime_object PASSED              [ 21%]
tests/test_date_utils.py::test_parse_null_and_empty_strings PASSED       [ 26%]
tests/test_date_utils.py::test_parse_invalid_date_raises PASSED          [ 30%]
tests/test_date_utils.py::test_calculate_age PASSED                      [ 34%]
tests/test_date_utils.py::test_is_stale_member PASSED                    [ 39%]
tests/test_deduplication.py::test_deduplicate_member_moved_country_latest_record_wins PASSED [ 43%]
tests/test_end_to_end.py::test_pipeline_end_to_end PASSED                [ 47%]
tests/test_legacy_readers.py::test_read_usa_csv PASSED                   [ 52%]
tests/test_legacy_readers.py::test_read_ind_csv PASSED                   [ 56%]
tests/test_legacy_readers.py::test_read_aus_xlsx_and_catch_anomalies PASSED [ 60%]
tests/test_redemptions.py::test_flatten_json_redemptions PASSED          [ 65%]
tests/test_redemptions.py::test_aggregate_member_redemptions PASSED      [ 69%]
tests/test_redemptions.py::test_enrich_member_profiles_with_redemptions PASSED [ 73%]
tests/test_staging.py::test_staging_happy_path_with_derived_columns PASSED [ 78%]
tests/test_staging.py::test_staging_quarantines_missing_mandatory_fields PASSED [ 82%]
tests/test_validations.py::test_validate_mandatory_fields_passes_on_clean_data PASSED [ 86%]
tests/test_validations.py::test_validate_key_uniqueness_detects_duplicates PASSED [ 91%]
tests/test_validations.py::test_validate_domain_rules_flags_invalid_age PASSED [ 95%]
tests/test_validations.py::test_validate_redemptions_detects_negative_miles_and_orphans PASSED [100%]

============================= 23 passed in 1.26s ==============================
```

---

## 🖥️ Interactive Web Demonstration UI

The live demo web dashboard (`http://localhost:8000`) provides:
- **Real-Time KPI Cards**: Ingested feeds (10), Staging records (6), Quarantined bad records (4), Deduplicated active members (5), Flattened fact redemptions (4).
- **Staging Explorer**: Interactive table with calculated `Age` and `Stale_Member` (`ACTIVE` / `STALE`) badges.
- **Per-Country Target Marts**: Country tabs (`TABLE_USA`, `TABLE_IND`, `TABLE_AUS`, `TABLE_CAN`, `TABLE_PHIL`) showing Elena's migration to Canada.
- **Member 360 View**: 1-to-1 enriched analytical join showing lifetime redemptions, total miles, and top partner without row multiplication.
- **Quarantine DLQ Viewer**: Displays quarantined records with exact row numbers and failure reasons (`ERR_INVALID_DATE` for month 13, `ERR_MANDATORY_NAME_MISSING`, etc.).
- **Live SQL Query Runner**: Allows the interviewers to execute custom DuckDB queries directly in the browser during the demonstration.
- **Automated Test Runner**: Executes the pytest test suite live and displays passing test counts in real time.

---

## 📂 Repository Structure

```
incubyte-skypoints/
├── .gitignore
├── pyproject.toml                         # Build & pytest configuration
├── README.md                              # Master assessment documentation
├── data/
│   ├── raw/                               # Raw assessment datasets & samples
│   │   ├── DE_Assessment_file.pdf         # Original Incubyte assessment specification
│   │   ├── USA.csv                        # Legacy USA source file
│   │   ├── IND.csv                        # Legacy India source file
│   │   ├── AUS.xlsx                       # Legacy Australia source file
│   │   ├── skypoints_members_sample.dat   # Clean flat file sample from spec
│   │   ├── skypoints_members_with_anomalies.dat # Migrations & edge-case test dataset
│   │   └── redemptions_sample.json        # Partner airline redemption feed
│   ├── processed/                         # Output DuckDB and Parquet marts
│   └── quarantine/                        # Dead-Letter Queue (DLQ) rejected records
├── sql/
│   └── snowflake/                         # Production Snowflake SQL Suite
│       ├── 01_raw_ddl.sql                 # Bronze landing tables (Flat file & VARIANT)
│       ├── 02_staging_ddl.sql             # Silver staging table & DLQ DDL
│       ├── 03_country_targets_ddl.sql     # Gold country tables & global clustered dimension
│       ├── 04_redemptions_ddl.sql         # Fact redemptions & aggregate summary mart
│       ├── 05_staging_load.sql            # Derived Age & Stale_Member transformation
│       ├── 06_latest_record_wins.sql      # Deduplication window & Multi-Table Insert
│       ├── 07_json_redemptions_flatten.sql# LATERAL FLATTEN & Member 360 analytical join
│       └── 08_data_validations.sql        # Comprehensive data validation suite
├── src/
│   └── skypoints/
│       ├── __init__.py
│       ├── config.py                      # Constants & country normalization maps
│       ├── models.py                      # Strongly-typed dataclass domain models
│       ├── pipeline.py                    # End-to-end pipeline orchestrator
│       ├── cli.py                         # Interactive terminal CLI tool
│       ├── ingestion/                     # Ingestion readers
│       │   ├── flat_file_reader.py        # Pipe-delimited file reader
│       │   ├── legacy_reader.py           # Adaptive reader for USA, IND, AUS files
│       │   └── json_reader.py             # JSON feed reader
│       ├── processing/                    # Core business transformations
│       │   ├── date_utils.py              # Robust date parsing, Age & Stale member calculation
│       │   ├── staging.py                 # Staging & quarantine isolation
│       │   ├── deduplication.py           # "Latest record wins" deduplication engine
│       │   ├── country_router.py          # Per-country table routing
│       │   └── redemptions.py             # JSON flattener & Member 360 aggregator
│       └── validation/                    # Data quality framework
│           └── validator.py               # Mandatory, uniqueness, and domain sanity checks
├── tests/                                 # Automated TDD Test Suite (23 tests)
│   ├── test_date_utils.py                 # Date parsing, unpadded ints, leap years
│   ├── test_staging.py                    # Age computation & Stale_Member flag logic
│   ├── test_deduplication.py              # Country migration & latest record wins
│   ├── test_redemptions.py                # JSON flattening & 1-to-1 aggregation join
│   ├── test_validations.py                # Mandatory checks, uniqueness, domain rules
│   ├── test_legacy_readers.py             # Validation of dirty USA, IND, AUS files
│   └── test_end_to_end.py                 # Full integration test with DuckDB persistence
├── demo/                                  # Live Interview Demonstration Application
│   ├── server.py                          # FastAPI backend runner & query engine
│   └── index.html                         # Modern single-page presentation dashboard
└── docs/
    ├── ARCHITECTURE.md                    # Medallion design, scale to billions, ADRs
    ├── DATA_QUALITY_REPORT.md             # In-depth analysis of assessment anomalies
    └── INTERVIEW_DEMO_GUIDE.md            # Live presentation script & interview Q&A
```

---

## 📜 Git Evolution History

As requested (*"Please make incremental commits so we can understand how your solution evolved"*), the repository contains clean, logical commits following Conventional Commits standards:

```text
* f9685fd docs: add comprehensive README, system architecture, data quality analysis, and interview demo guide
* 6c8c539 feat(demo): add interactive CLI inspector and live web demonstration dashboard
* 748ba98 feat(core): implement end-to-end Python pipeline engine, models, and comprehensive TDD test suite
* 7e05691 feat(sql): add production Snowflake DDLs, staging transformations, deduplication, and validation suite
* 032d069 feat(ingestion): initialize project repository and ingest raw assessment datasets
```

---

*Submitted for the Data Craftsperson role at Incubyte. Ready for live demonstration.*
