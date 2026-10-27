# Data Quality & Anomaly Analysis Report

**SkyPoints Global Airline Loyalty Platform**  
*Incubyte Technical Assessment: Data Craftsperson*  
*Author: Sirajuddin Kamaluddin*

---

## 1. Overview

During the exploratory analysis of the assessment package (`DE_Assessment_file.pdf`, `USA.csv`, `IND.csv`, `AUS.xlsx`), significant data quality issues, schema drift, and formatting anomalies were uncovered across the heterogeneous source files.

A true **Data Craftsperson** anticipates real-world data entropy. Rather than writing fragile scripts that crash in production, our platform implements a resilient **Data Quality & Isolation Firewall**.

---

## 2. Detailed Findings from Assessment Source Files

### 2.1. File: `AUS.xlsx` (Australia Source Feed)
| Row | Column | Raw Value | Issue Classification | Impact & Handling |
|---|---|---|---|---|
| Row 1 | Date of Birth | `'NULL'` | **Null String Literal** | String `'NULL'` must not be stored as a string or parsed as date. Our engine sanitizes `'NULL'`, `'N/A'`, `''` to SQL `NULL`. |
| Row 2 | Date of Enrollment | `'2021-13-13'` | **Invalid Date (Month 13)** | The date has month 13, which is physically impossible. Rather than crashing the ETL, this record is quarantined to `QUARANTINE_REJECTED_RECORDS` with `ERR_INVALID_DATE`. |
| Headers | Multiple | `Unique ID`, `Tier Type` | **Schema / Column Drift** | Headers differ from specification (`Unique ID` instead of `Member_Id`; `Tier Type` instead of `Tier_Code`). Handled via adaptive legacy mapping. |

### 2.2. File: `USA.csv` (United States Source Feed)
| Column | Raw Value | Issue Classification | Impact & Handling |
|---|---|---|---|
| `EnrollmentDate` | `6152022`, `1052022` | **Unpadded Integer / Truncated Zero** | Date lost leading zero (e.g. `6152022` for June 15, 2022; length 7). Our date parser pads length 7 strings to length 8 (`06152022`) to parse correctly. |
| Schema Structure | 5 columns only | **Incomplete Schema Drift** | Missing `DOB`, `State`, `Agent_Name`, `Country`. The pipeline populates known fields and safely defaults missing attributes to `NULL`. |

### 2.3. File: `IND.csv` (India Source Feed)
| Column | Raw Value | Issue Classification | Impact & Handling |
|---|---|---|---|
| `DOB`, `Flight Date` | `12/1/1998`, `6/15/2022` | **Slash Date Formatting (M/D/YYYY)** | Dates use slashes instead of ISO `YYYYMMDD`. Adaptive parser tests multiple format masks. |
| `Individual or Corporate` | `'I'`, `'C'` | **Undocumented Extra Column** | Source system introduced auxiliary business metadata. The pipeline ignores or maps to extended attributes without failing. |
| `Flight Date` | Column Header | **Header Whitespace Mismatch** | Column name has an embedded space (`Flight Date` vs `FlightDate`). The ingestion normalizes header casing and whitespace. |

### 2.4. File: `DE_Assessment_file.pdf` (Staging Table Comparison)
| Specification | Staging Sample | Observation | Solution |
|---|---|---|---|
| DOB: `03051985` (len 8) | DOB: `3051985` (len 7) | Classic database conversion error where a string or date column was cast to an `INTEGER` and stripped of its leading zero (`03` &rarr; `3`). | Our ingestion enforces `VARCHAR` landing and LPAD normalization (`LPAD(TRIM(dob), 8, '0')`) before casting to `DATE`. |
| Member Name | Key Column = Y | Member Name is flagged as Key Column in spec, but Member ID is the true operational unique identifier. | Uniqueness and collision checks validate both `MEMBER_ID` uniqueness and check for name collisions (`1 ID -> multiple names`). |

---

## 3. Data Quality Firewall & Quarantine Architecture

```
                   Incoming Raw Stream
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
  ┌───────────────────────┐
  │ Business Derivations: │
  │  - Calculate Age      │
  │  - Stale Member Flag  │
  └──────────┬────────────┘
             │
             ▼
      Silver Staging & Gold Target Marts
```

---

## 4. Automated Validation Suite Summary

Our automated validation engine verifies the following criteria:

| Check Category | Rule Description | Threshold | Action on Violation |
|---|---|---|---|
| **Completeness** | `MEMBER_NAME`, `MEMBER_ID`, `ENROLLMENT_DATE` present | 100% | Route to Quarantine DLQ |
| **Uniqueness** | Unique `MEMBER_ID` per target table | 0 Duplicates | Deduplicate via Latest Record Wins |
| **Integrity** | Single `MEMBER_ID` has consistent `MEMBER_NAME` | 0 Collisions | Flag identity anomaly |
| **Sanity** | Member Age between 0 and 120 years | 0 Out-of-bounds | Flag validation warning |
| **Chronology** | Last flight date cannot precede enrollment by > 1 year | 0 Violations | Flag anomaly |
| **Redemptions** | `MILES_REDEEMED > 0` | Positive | Quarantine transaction |
| **Status Domain** | Status in `('COMPLETED', 'PENDING', 'CANCELLED')` | Strict domain | Flag unrecognized status |
| **Referential** | No orphan redemptions (member must exist) | 0 Orphans | Flag referential integrity error |
