-- ============================================================================
-- Incubyte Data Craftsperson Assessment - SkyPoints Airline Loyalty Program
-- Step 5: Staging Load Logic with Derived Columns (Deliverable 2)
-- ============================================================================
-- Deliverable 2 Requirements:
-- 1. Age: Computed from DOB.
-- 2. Stale_Member: Flag where days since Flight_Date > 90.
--
-- Craftsmanship Highlights:
-- - Uses TRY_TO_DATE to prevent hard failures on corrupted dates.
-- - Supports unpadded date formats (e.g., '3051985' -> '03051985').
-- - Uses BATCH_DATE / CURRENT_DATE for deterministic age and stale calculations.
-- - Filters out malformed records to QUARANTINE_REJECTED_RECORDS with reason.
-- ============================================================================

USE SCHEMA SKYPOINTS_DW.SILVER_STAGING;

-- Session or parameter variable for deterministic batch execution
SET BATCH_DATE = COALESCE($BATCH_DATE, CURRENT_DATE());
SET CURRENT_BATCH_ID = COALESCE($CURRENT_BATCH_ID, 'BATCH_' || TO_CHAR(CURRENT_TIMESTAMP(), 'YYYYMMDD_HH24MISS'));

-- ----------------------------------------------------------------------------
-- 1. Route Malformed Records directly to Quarantine (DLQ)
-- Checks for missing mandatory columns (Member_Name, Member_Id, Enrollment_Date)
-- or invalid date structures.
-- ----------------------------------------------------------------------------
INSERT INTO QUARANTINE_REJECTED_RECORDS (
    BATCH_ID,
    SOURCE_FILE_NAME,
    SOURCE_ROW_NUM,
    RECORD_TYPE,
    RAW_RECORD,
    ERROR_CODE,
    ERROR_MESSAGE,
    FAILED_FIELD
)
SELECT 
    l.BATCH_ID,
    l.SOURCE_FILE_NAME,
    l.SOURCE_FILE_ROW_NUM,
    'MEMBER' AS RECORD_TYPE,
    l.RAW_LINE AS RAW_RECORD,
    CASE
        WHEN NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 2)), '') IS NULL THEN 'ERR_MANDATORY_NAME_MISSING'
        WHEN NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 3)), '') IS NULL THEN 'ERR_MANDATORY_ID_MISSING'
        WHEN NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 4)), '') IS NULL THEN 'ERR_MANDATORY_ENROLL_DATE_MISSING'
        WHEN TRY_TO_DATE(TRIM(SPLIT_PART(l.RAW_LINE, '|', 4)), 'YYYYMMDD') IS NULL THEN 'ERR_INVALID_ENROLL_DATE'
        WHEN NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 5)), '') IS NOT NULL 
             AND TRY_TO_DATE(TRIM(SPLIT_PART(l.RAW_LINE, '|', 5)), 'YYYYMMDD') IS NULL THEN 'ERR_INVALID_FLIGHT_DATE'
        ELSE 'ERR_UNKNOWN'
    END AS ERROR_CODE,
    CASE
        WHEN NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 2)), '') IS NULL THEN 'Mandatory field Member Name is null or empty'
        WHEN NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 3)), '') IS NULL THEN 'Mandatory field Member ID is null or empty'
        WHEN NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 4)), '') IS NULL THEN 'Mandatory field Enrollment Date is null or empty'
        WHEN TRY_TO_DATE(TRIM(SPLIT_PART(l.RAW_LINE, '|', 4)), 'YYYYMMDD') IS NULL THEN 'Enrollment Date cannot be parsed as YYYYMMDD'
        WHEN NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 5)), '') IS NOT NULL 
             AND TRY_TO_DATE(TRIM(SPLIT_PART(l.RAW_LINE, '|', 5)), 'YYYYMMDD') IS NULL THEN 'Flight Date cannot be parsed as YYYYMMDD'
        ELSE 'Validation error in member record'
    END AS ERROR_MESSAGE,
    CASE
        WHEN NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 2)), '') IS NULL THEN 'MEMBER_NAME'
        WHEN NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 3)), '') IS NULL THEN 'MEMBER_ID'
        WHEN NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 4)), '') IS NULL THEN 'ENROLLMENT_DATE'
        WHEN TRY_TO_DATE(TRIM(SPLIT_PART(l.RAW_LINE, '|', 4)), 'YYYYMMDD') IS NULL THEN 'ENROLLMENT_DATE'
        WHEN NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 5)), '') IS NOT NULL 
             AND TRY_TO_DATE(TRIM(SPLIT_PART(l.RAW_LINE, '|', 5)), 'YYYYMMDD') IS NULL THEN 'LAST_FLIGHT_DATE'
        ELSE 'GENERAL'
    END AS FAILED_FIELD
FROM SKYPOINTS_DW.BRONZE_RAW.RAW_MEMBER_PROFILES_LANDING l
WHERE l.RECORD_TYPE = 'D'
  AND (
      NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 2)), '') IS NULL
      OR NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 3)), '') IS NULL
      OR NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 4)), '') IS NULL
      OR TRY_TO_DATE(TRIM(SPLIT_PART(l.RAW_LINE, '|', 4)), 'YYYYMMDD') IS NULL
      OR (NULLIF(TRIM(SPLIT_PART(l.RAW_LINE, '|', 5)), '') IS NOT NULL 
          AND TRY_TO_DATE(TRIM(SPLIT_PART(l.RAW_LINE, '|', 5)), 'YYYYMMDD') IS NULL)
  );

-- ----------------------------------------------------------------------------
-- 2. Load Valid Cleansed Records into Staging with Derived Columns
-- ----------------------------------------------------------------------------
INSERT INTO STG_MEMBER_PROFILES (
    MEMBER_NAME,
    MEMBER_ID,
    ENROLLMENT_DATE,
    LAST_FLIGHT_DATE,
    TIER_CODE,
    AGENT_NAME,
    STATE,
    COUNTRY,
    POST_CODE,
    DOB,
    IS_ACTIVE,
    AGE,
    STALE_MEMBER,
    BATCH_ID,
    SOURCE_FILE_NAME,
    RECORD_HASH
)
WITH parsed_raw AS (
    SELECT
        TRIM(SPLIT_PART(RAW_LINE, '|', 2)) AS raw_name,
        TRIM(SPLIT_PART(RAW_LINE, '|', 3)) AS raw_id,
        TRIM(SPLIT_PART(RAW_LINE, '|', 4)) AS raw_enroll_dt,
        NULLIF(TRIM(SPLIT_PART(RAW_LINE, '|', 5)), '') AS raw_flight_dt,
        NULLIF(TRIM(SPLIT_PART(RAW_LINE, '|', 6)), '') AS raw_tier,
        NULLIF(TRIM(SPLIT_PART(RAW_LINE, '|', 7)), '') AS raw_agent,
        NULLIF(TRIM(SPLIT_PART(RAW_LINE, '|', 8)), '') AS raw_state,
        UPPER(NULLIF(TRIM(SPLIT_PART(RAW_LINE, '|', 9)), '')) AS raw_country,
        -- Handle unpadded DOB strings (e.g., '3051985' -> '03051985' where 3 is March)
        CASE 
            WHEN LENGTH(TRIM(SPLIT_PART(RAW_LINE, '|', 10))) = 7 
            THEN LPAD(TRIM(SPLIT_PART(RAW_LINE, '|', 10)), 8, '0')
            ELSE NULLIF(TRIM(SPLIT_PART(RAW_LINE, '|', 10)), '')
        END AS raw_dob,
        COALESCE(NULLIF(TRIM(SPLIT_PART(RAW_LINE, '|', 11)), ''), 'A') AS raw_is_active,
        SOURCE_FILE_NAME,
        BATCH_ID
    FROM SKYPOINTS_DW.BRONZE_RAW.RAW_MEMBER_PROFILES_LANDING
    WHERE RECORD_TYPE = 'D'
),
typed_records AS (
    SELECT
        raw_name AS member_name,
        raw_id AS member_id,
        TRY_TO_DATE(raw_enroll_dt, 'YYYYMMDD') AS enrollment_date,
        TRY_TO_DATE(raw_flight_dt, 'YYYYMMDD') AS last_flight_date,
        raw_tier AS tier_code,
        raw_agent AS agent_name,
        raw_state AS state,
        raw_country AS country,
        TRY_TO_NUMBER(NULL) AS post_code, -- Mapped from extended layout if available
        -- DOB format in sample: '03051985' (MMDDYYYY)
        COALESCE(
            TRY_TO_DATE(raw_dob, 'MMDDYYYY'),
            TRY_TO_DATE(raw_dob, 'YYYYMMDD'),
            TRY_TO_DATE(raw_dob, 'DDMMYYYY')
        ) AS dob,
        raw_is_active AS is_active,
        BATCH_ID,
        SOURCE_FILE_NAME
    FROM parsed_raw
    WHERE raw_name IS NOT NULL 
      AND raw_id IS NOT NULL 
      AND TRY_TO_DATE(raw_enroll_dt, 'YYYYMMDD') IS NOT NULL
      AND (raw_flight_dt IS NULL OR TRY_TO_DATE(raw_flight_dt, 'YYYYMMDD') IS NOT NULL)
)
SELECT
    member_name,
    member_id,
    enrollment_date,
    last_flight_date,
    tier_code,
    agent_name,
    state,
    country,
    post_code,
    dob,
    is_active,
    -- DERIVED COLUMN 1: Age computed from DOB
    CASE 
        WHEN dob IS NOT NULL THEN DATEDIFF(year, dob, $BATCH_DATE)
        ELSE NULL
    END AS age,
    -- DERIVED COLUMN 2: Stale_Member flag where days since Flight_Date > 90
    -- (If last_flight_date is NULL, member has never flown -> classified as Stale 'Y')
    CASE 
        WHEN last_flight_date IS NULL THEN 'Y'
        WHEN DATEDIFF(day, last_flight_date, $BATCH_DATE) > 90 THEN 'Y'
        ELSE 'N'
    END AS stale_member,
    BATCH_ID,
    SOURCE_FILE_NAME,
    SHA2(CONCAT_WS('||', member_name, member_id, enrollment_date, COALESCE(last_flight_date, '1900-01-01'), COALESCE(country, 'UNKNOWN')), 256) AS record_hash
FROM typed_records;
