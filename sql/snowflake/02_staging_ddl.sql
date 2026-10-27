-- ============================================================================
-- Incubyte Data Craftsperson Assessment - SkyPoints Airline Loyalty Program
-- Step 2: Staging Layer (Silver) DDL for Snowflake
-- ============================================================================
-- Design Decision:
-- The Staging table parses raw records into strongly-typed columns, enriches
-- records with business-derived columns (AGE, STALE_MEMBER), and applies
-- deterministic lineage tracking.
--
-- Deliverable 2 Derived Columns:
-- 1. AGE: Computed dynamically/stored as integer from DOB to current batch date.
-- 2. STALE_MEMBER: Flag ('Y'/'N') where days since LAST_FLIGHT_DATE > 90.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS SKYPOINTS_DW.SILVER_STAGING;
USE SCHEMA SKYPOINTS_DW.SILVER_STAGING;

-- ----------------------------------------------------------------------------
-- 1. Staging Member Profiles Table
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE STG_MEMBER_PROFILES (
    -- Natural Business Keys & Attributes (per PDF specification)
    MEMBER_NAME             VARCHAR(255)       NOT NULL,  -- Key column (spec position 1)
    MEMBER_ID               VARCHAR(18)        NOT NULL,  -- Mandatory (spec position 2)
    ENROLLMENT_DATE         DATE               NOT NULL,  -- Mandatory (spec position 3)
    LAST_FLIGHT_DATE        DATE,                         -- Optional (spec position 4)
    TIER_CODE               VARCHAR(5),                   -- Optional: GLD, SLV, PLT
    AGENT_NAME              VARCHAR(255),                 -- Optional (spec position 6)
    STATE                   VARCHAR(5),                   -- Optional: CA, TN, VIC, ONT, NCR
    COUNTRY                 VARCHAR(5),                   -- Optional: USA, IND, AU, CAN, PHIL
    POST_CODE               NUMBER(5, 0),                 -- Optional (spec position 9)
    DOB                     DATE,                         -- Optional (spec position 10)
    IS_ACTIVE               VARCHAR(1),                   -- Optional: 'A' for active, 'I' for inactive

    -- Deliverable 2 Derived Columns
    AGE                     NUMBER(3, 0),                 -- Computed from DOB: DATEDIFF(year, DOB, CURRENT_DATE)
    STALE_MEMBER            VARCHAR(1)         NOT NULL,  -- 'Y' if DATEDIFF(day, LAST_FLIGHT_DATE, CURRENT_DATE) > 90 else 'N'

    -- Data Lineage & Audit Metadata
    BATCH_ID                VARCHAR(64)        NOT NULL,
    SOURCE_FILE_NAME        VARCHAR(255)       NOT NULL,
    RECORD_HASH             VARCHAR(64)        NOT NULL,  -- SHA256 of business payload for change detection
    STAGING_TIMESTAMP       TIMESTAMP_NTZ      DEFAULT CURRENT_TIMESTAMP(),

    -- Constraints
    CONSTRAINT PK_STG_MEMBER PRIMARY KEY (MEMBER_ID, BATCH_ID) RELY
)
CLUSTER BY (COUNTRY, ENROLLMENT_DATE)
COMMENT = 'Cleansed, typed, and enriched member profile staging table';

-- ----------------------------------------------------------------------------
-- 2. Quarantine / Dead-Letter Queue (DLQ) Table
-- Captures records that violate mandatory constraints, have unparseable dates,
-- or contain structural anomalies for debugging without failing the pipeline.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE QUARANTINE_REJECTED_RECORDS (
    REJECT_ID               NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    BATCH_ID                VARCHAR(64)        NOT NULL,
    SOURCE_FILE_NAME        VARCHAR(255)       NOT NULL,
    SOURCE_ROW_NUM          NUMBER(12, 0),
    RECORD_TYPE             VARCHAR(10),       -- 'MEMBER' or 'REDEMPTION'
    RAW_RECORD              VARCHAR(4000),
    ERROR_CODE              VARCHAR(50)        NOT NULL, -- e.g., 'MISSING_MANDATORY_FIELD', 'INVALID_DATE'
    ERROR_MESSAGE           VARCHAR(1000)      NOT NULL,
    FAILED_FIELD            VARCHAR(50),
    REJECTED_TIMESTAMP      TIMESTAMP_NTZ      DEFAULT CURRENT_TIMESTAMP()
)
COMMENT = 'Dead-letter queue for rejected member and redemption records';
