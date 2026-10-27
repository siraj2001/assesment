-- ============================================================================
-- Incubyte Data Craftsperson Assessment - SkyPoints Airline Loyalty Program
-- Step 4: Flattened Redemptions Table (Gold Fact) DDL for Snowflake
-- ============================================================================
-- Deliverable 4 Requirement:
-- "Parse the semi-structured JSON redemption feed into a flattened, queryable
--  table, and describe how you would join it back to the member profile data."
-- ============================================================================

USE SCHEMA SKYPOINTS_DW.GOLD_MARTS;

-- ----------------------------------------------------------------------------
-- 1. Flattened Mileage Redemptions Fact Table
-- Grain: One row per redemption transaction.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE FCT_MILEAGE_REDEMPTIONS (
    REDEMPTION_SK           NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    TXN_ID                  VARCHAR(64)        NOT NULL,  -- Unique transaction identifier
    MEMBER_ID               VARCHAR(18)        NOT NULL,  -- Foreign key to member dimension
    FEED_DATE               DATE               NOT NULL,  -- Feed batch date (YYYYMMDD)
    TXN_DATE                DATE               NOT NULL,  -- Transaction date (YYYYMMDD)
    PARTNER_AIRLINE         VARCHAR(100)       NOT NULL,  -- e.g., AeroLink, SkyPoints, AirIndia, Qantas
    MILES_REDEEMED          NUMBER(12, 0)      NOT NULL,  -- Miles quantity redeemed
    STATUS                  VARCHAR(20)        NOT NULL,  -- COMPLETED, PENDING, CANCELLED
    
    -- Lineage metadata
    BATCH_ID                VARCHAR(64)        NOT NULL,
    INGESTION_TIMESTAMP     TIMESTAMP_NTZ      DEFAULT CURRENT_TIMESTAMP(),
    
    CONSTRAINT PK_FCT_REDEMPTIONS PRIMARY KEY (TXN_ID) RELY
)
CLUSTER BY (MEMBER_ID, TXN_DATE)
COMMENT = 'Flattened transaction-level fact table for partner airline mileage redemptions';

-- ----------------------------------------------------------------------------
-- 2. Member Redemptions Summary Mart (Enrichment Aggregation)
-- Grain: One row per member. Provides 1-to-1 analytical enrichment
-- without causing cartesian explosion when joining with member profiles.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE AGG_MEMBER_REDEMPTION_METRICS (
    MEMBER_ID               VARCHAR(18)        NOT NULL,
    LIFETIME_REDEMPTIONS    NUMBER(10, 0)      DEFAULT 0,
    TOTAL_MILES_REDEEMED    NUMBER(18, 0)      DEFAULT 0,
    COMPLETED_MILES         NUMBER(18, 0)      DEFAULT 0,
    PENDING_MILES           NUMBER(18, 0)      DEFAULT 0,
    LAST_REDEMPTION_DATE    DATE,
    TOP_PARTNER             VARCHAR(100),
    LAST_CALCULATED_AT      TIMESTAMP_NTZ      DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_AGG_MEMBER_METRICS PRIMARY KEY (MEMBER_ID) RELY
)
CLUSTER BY (MEMBER_ID)
COMMENT = 'Pre-aggregated loyalty redemption metrics for fast 1-to-1 member profile enrichment';
