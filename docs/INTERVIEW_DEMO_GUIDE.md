# Live Demonstration & Interview Guide

**SkyPoints Global Airline Loyalty Platform**  
*Incubyte Technical Assessment: Data Craftsperson*  
*Candidate: Sirajuddin Kamaluddin*

---

## 1. Quick Launch for the Interview

During the interview, you can run either the **Interactive Web Dashboard** or the **Terminal CLI**.

### Option A: Launch Interactive Web Dashboard (Recommended for visual impact)
```bash
python -m uvicorn demo.server:app --port 8000 --reload
```
Then open your browser to **`http://localhost:8000`**.

### Option B: Terminal CLI Presentation
```bash
# Run the complete end-to-end pipeline with summary tables
python -m skypoints.cli run

# Inspect Canada table (showing Elena's migration)
python -m skypoints.cli inspect --table TABLE_CAN

# Inspect the Quarantine Dead-Letter Queue
python -m skypoints.cli inspect --table QUARANTINE_REJECTED_RECORDS

# Run the automated test suite
pytest -v
```

---

## 2. 5-Minute Live Demo Script for the Interviewers

### Step 1: Context & Problem Framing (1 minute)
> *"Hello! The SkyPoints platform handles two daily feeds: flat files of member profiles and semi-structured JSON feeds of airline redemptions. Today, I'll demonstrate our production-grade pipeline designed with Software Craftsmanship principles — featuring robust TDD, a resilient Data Quality firewall, 'Latest Record Wins' country routing, and seamless scale to billions of records."*

### Step 2: The Ingestion & Data Quality Isolation (1 minute)
- Click **"⚡ Run Batch (With Migrations & Errors)"** on the top right.
- Point to the KPI banner:
  - **10 Raw Feeds Ingested**
  - **4 Quarantined Bad Records (DLQ)**
  - **6 Staged Clean Records**
- Switch to the **"Quarantine & Anomaly DLQ"** tab:
  > *"Notice how the pipeline never crashes on malformed data. Instead of failing the entire daily batch, our firewall identified missing names, missing IDs, missing enrollment dates, and the invalid '2021-13-13' date from the Australian feed, routing them directly to the Dead-Letter Queue with precise error codes."*

### Step 3: Staging & Required Derived Columns (1 minute)
- Switch to the **"Staging & Derived Columns"** tab:
  > *"Here is Deliverable 2: STG_MEMBER_PROFILES. We computed two key derived fields:*
  > 1. *`Age`: Accurately calculated from DOB, handling unpadded 7-digit strings (like `3051985`) and leap years.*
  > 2. *`Stale_Member`: Evaluated as 'Y' when days since last flight > 90, or if the member has never flown. Members with recent flights (like Ravi who flew 5 days ago) are marked 'ACTIVE'."*

### Step 4: Country Routing & "Latest Record Wins" (1 minute)
- Switch to the **"Per-Country Marts (Latest Wins)"** tab:
  - Click **Canada (TABLE_CAN)**, then **USA (TABLE_USA)**.
  > *"Here is Deliverable 3. Elena was originally registered in the USA with flight date 2012-10-13, but later flew into Canada on 2023-12-01. Our windowed ranking `ROW_NUMBER() OVER (PARTITION BY member_id ORDER BY last_flight_date DESC)` recognized her most recent active residence. She is routed to `TABLE_CAN` and deduplicated from `TABLE_USA`."*

### Step 5: JSON Redemptions & Safe Analytical Join (1 minute)
- Switch to the **"Member 360 Enriched View"** tab:
  > *"In Deliverable 4, we flattened the partner airline JSON feed into `FCT_MILEAGE_REDEMPTIONS`. To join it back to member profiles without causing Cartesian fan-out bugs (which distort financial totals and member counts), we roll up metrics to the member grain (`lifetime_redemptions`, `total_miles_redeemed`, `top_partner`). Elena shows 2 redemptions totaling 17,000 miles with top partner AeroLink."*

### Step 6: Automated Test Verification
- Switch to the **"Automated Pytest Suite"** tab and click **"▶ Re-run Test Suite"**:
  > *"We followed strict Test-Driven Development (TDD). All 23 unit and integration tests execute and pass in ~1.2 seconds, validating date parsing, deduplication, country routing, schema drift, and end-to-end DuckDB persistence."*

---

## 3. Anticipated Technical Questions & Model Answers

### Q1: "How would this pipeline scale to billions of records per day in Snowflake?"
**Answer:**
> *"At billion-row scale, three architectural decisions are critical:*
> 1. *Auto-Ingest via Snowpipe: We chunk flat files and JSON into 100-250MB compressed files in cloud object storage, streaming them directly into raw VARCHAR/VARIANT tables with zero transform overhead.*
> 2. *Clustering & Micro-Partition Pruning: We cluster staging and dimension tables by `(COUNTRY, TIER_CODE)` or `MEMBER_ID`. Instead of running deduplication across the entire historical billion-row table, we dedup only the incoming daily batch and perform an incremental `MERGE`.*
> 3. *Global Partitioned Dimension vs. 195 Physical Tables: While we provide DDLs for separate country tables, at true enterprise scale, maintaining 195 DDLs causes schema drift. The optimal design is a single clustered `DIM_MEMBERS_GLOBAL` with Secure Views per country, enabling Snowflake's query compiler to prune micro-partitions automatically."*

### Q2: "What is your approach to handling dirty data and schema drift?"
**Answer:**
> *"We follow the Dead-Letter Queue (DLQ) pattern. A data pipeline in an enterprise should never have unhandled exceptions. Mandatory fields and date validity are evaluated before type casting. Valid records continue downstream, while malformed records are diverted to `QUARANTINE_REJECTED_RECORDS` with source row numbers and error descriptions. This guarantees zero downtime and enables data governance teams to replay corrected data."*

### Q3: "Why did you aggregate redemptions before joining them back to the member profile?"
**Answer:**
> *"Joining a 1-to-many transaction fact directly to a member profile creates a fan-out dilemma: if a member has 10 redemptions, joining multiplies the member record into 10 rows. This breaks downstream dimension queries and causes double-counting in business reports. By pre-aggregating to a 1-to-1 grain in `AGG_MEMBER_REDEMPTION_METRICS`, each member remains exactly one row with lifetime miles, top partner, and active counts."*
