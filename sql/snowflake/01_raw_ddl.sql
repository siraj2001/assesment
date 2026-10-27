-- ============================================================================
-- Incubyte Data Craftsperson Assessment - SkyPoints Airline Loyalty Program
-- Step 1: Raw / Landing Layer (Bronze) DDL for Snowflake
-- ============================================================================
-- Design Decision:
-- Raw tables capture raw data with zero parsing transformations, ensuring
-- zero data loss on ingestion. Metadata fields (filename, ingestion_timestamp,
-- row_number) are captured to guarantee complete auditability and lineage.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS SKYPOINTS_DW;
CREATE SCHEMA IF NOT EXISTS SKYPOINTS_DW.BRONZE_RAW;
USE SCHEMA SKYPOINTS_DW.BRONZE_RAW;

-- ----------------------------------------------------------------------------
-- 1. Raw Flat File Member Landing Table
-- Ingests raw lines from daily flat files (|H| header, |D| detail records).
-- In Snowflake, raw text is ingested into VARCHAR/VARIANT to prevent load failures.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE RAW_MEMBER_PROFILES_LANDING (
    RAW_RECORD_ID          NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    RECORD_TYPE            VARCHAR(1),        -- 'H' for Header, 'D' for Detail
    RAW_LINE               VARCHAR(4000),     -- Full raw pipe-delimited record
    SOURCE_FILE_NAME       VARCHAR(255)       NOT NULL,
    SOURCE_FILE_ROW_NUM    NUMBER(12, 0)      NOT NULL,
    INGESTION_TIMESTAMP    TIMESTAMP_NTZ      DEFAULT CURRENT_TIMESTAMP(),
    BATCH_ID               VARCHAR(64)        NOT NULL
)
COMMENT = 'Landing table for unparsed member profile flat files';

-- ----------------------------------------------------------------------------
-- 2. Raw JSON Redemption Feed Landing Table
-- Ingests semi-structured JSON feed using Snowflake native VARIANT column.
-- Supports high-throughput streaming/micro-batch ingestion (Snowpipe).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE RAW_REDEMPTION_FEED_LANDING (
    RAW_FEED_ID            NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    RAW_PAYLOAD            VARIANT            NOT NULL, -- Full JSON document
    SOURCE_FILE_NAME       VARCHAR(255)       NOT NULL,
    INGESTION_TIMESTAMP    TIMESTAMP_NTZ      DEFAULT CURRENT_TIMESTAMP(),
    BATCH_ID               VARCHAR(64)        NOT NULL
)
COMMENT = 'Landing table for raw JSON partner redemption feeds';

-- ----------------------------------------------------------------------------
-- 3. Snowflake File Formats & External Stage Examples (Production Best Practice)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FILE FORMAT FF_PIPE_DELIMITED
    TYPE = 'CSV'
    FIELD_DELIMITER = '|'
    SKIP_HEADER = 0
    FIELD_OPTIONALLY_ENCLOSED_BY = 'NONE'
    TRIM_SPACE = TRUE
    NULL_IF = ('', 'NULL', 'null', 'N/A', 'NA');

CREATE OR REPLACE FILE FORMAT FF_JSON
    TYPE = 'JSON'
    STRIP_OUTER_ARRAY = TRUE
    IGNORE_UTF8_ERRORS = FALSE;
