-- ============================================================================
-- Incubyte Data Craftsperson Assessment - SkyPoints Airline Loyalty Program
-- Step 8: Comprehensive Data Validations & Quality Suite (Deliverable 5)
-- ============================================================================
-- Deliverable 5 Requirements:
-- "Create the necessary data validations — mandatory field checks,
--  key-column uniqueness, and any checks you would add to catch the kind
--  of data issues visible in the sample data above."
--
-- Categories of Checks:
-- 1. Completeness (Mandatory Field Checks)
-- 2. Uniqueness (Key-column and natural business key checks)
-- 3. Validity & Formatting (Invalid dates, unpadded integers, 'NULL' strings)
-- 4. Temporal Consistency (Future dates, Enrollment > Flight, Age range)
-- 5. Referential Integrity & Domain Rules (Orphan transactions, negative miles)
-- ============================================================================

USE SCHEMA SKYPOINTS_DW.SILVER_STAGING;

-- ----------------------------------------------------------------------------
-- Test 1: Mandatory Field Nullability Check
-- Expected: 0 failures in Staging (all should have been routed to Quarantine)
-- ----------------------------------------------------------------------------
SELECT 
    'CHECK_MANDATORY_FIELDS' AS test_name,
    COUNT(*) AS failure_count,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS test_status
FROM STG_MEMBER_PROFILES
WHERE MEMBER_NAME IS NULL OR TRIM(MEMBER_NAME) = ''
   OR MEMBER_ID IS NULL OR TRIM(MEMBER_ID) = ''
   OR ENROLLMENT_DATE IS NULL;

-- ----------------------------------------------------------------------------
-- Test 2: Key Column Uniqueness & Business Key Integrity
-- Check 2A: Unique Member_Id per batch in Gold Target Tables
-- ----------------------------------------------------------------------------
SELECT 
    'CHECK_GOLD_USA_MEMBER_ID_UNIQUENESS' AS test_name,
    MEMBER_ID,
    COUNT(*) AS occurrence_count
FROM SKYPOINTS_DW.GOLD_MARTS.TABLE_USA
WHERE IS_CURRENT = TRUE
GROUP BY MEMBER_ID
HAVING COUNT(*) > 1;

-- Check 2B: Name-to-ID Collision Detection (Spec position 1 vs 2)
-- Catches scenarios where the same Member ID is associated with different Member Names
SELECT 
    'CHECK_MEMBER_ID_NAME_COLLISION' AS test_name,
    MEMBER_ID,
    COUNT(DISTINCT MEMBER_NAME) AS distinct_name_count
FROM STG_MEMBER_PROFILES
GROUP BY MEMBER_ID
HAVING COUNT(DISTINCT MEMBER_NAME) > 1;

-- ----------------------------------------------------------------------------
-- Test 3: Date Parsing & 'NULL' String Contamination (Caught from AUS.xlsx)
-- Ensure no literal 'NULL' or unparseable dates slipped through
-- ----------------------------------------------------------------------------
SELECT 
    'CHECK_CORRUPT_DATE_STRINGS' AS test_name,
    COUNT(*) AS failure_count
FROM STG_MEMBER_PROFILES
WHERE TO_CHAR(DOB) = '0001-01-01'
   OR TO_CHAR(ENROLLMENT_DATE) = '0001-01-01'
   OR TO_CHAR(LAST_FLIGHT_DATE) = '0001-01-01';

-- ----------------------------------------------------------------------------
-- Test 4: Business Logic & Chronological Sanity Checks
-- ----------------------------------------------------------------------------
-- Check 4A: Chronological order (Flight Date cannot be significantly before Enrollment Date)
SELECT 
    'CHECK_FLIGHT_BEFORE_ENROLLMENT' AS test_name,
    COUNT(*) AS failure_count
FROM STG_MEMBER_PROFILES
WHERE LAST_FLIGHT_DATE IS NOT NULL 
  AND LAST_FLIGHT_DATE < DATEADD(month, -1, ENROLLMENT_DATE);

-- Check 4B: Reasonable Age Limits (0 <= Age <= 120)
SELECT 
    'CHECK_REASONABLE_AGE_RANGE' AS test_name,
    COUNT(*) AS failure_count
FROM STG_MEMBER_PROFILES
WHERE AGE IS NOT NULL 
  AND (AGE < 0 OR AGE > 120);

-- Check 4C: Stale_Member Flag Accuracy (Verify days > 90 equals 'Y')
SELECT 
    'CHECK_STALE_MEMBER_FLAG_CONSISTENCY' AS test_name,
    COUNT(*) AS failure_count
FROM STG_MEMBER_PROFILES
WHERE (STALE_MEMBER = 'Y' AND DATEDIFF(day, COALESCE(LAST_FLIGHT_DATE, '1900-01-01'), CURRENT_DATE()) <= 90)
   OR (STALE_MEMBER = 'N' AND DATEDIFF(day, LAST_FLIGHT_DATE, CURRENT_DATE()) > 90);

-- ----------------------------------------------------------------------------
-- Test 5: Semi-Structured JSON Redemption Feed Checks
-- ----------------------------------------------------------------------------
-- Check 5A: Non-positive redemption miles (Miles must be > 0)
SELECT 
    'CHECK_NON_POSITIVE_REDEMPTION_MILES' AS test_name,
    COUNT(*) AS failure_count
FROM SKYPOINTS_DW.GOLD_MARTS.FCT_MILEAGE_REDEMPTIONS
WHERE MILES_REDEEMED <= 0;

-- Check 5B: Valid redemption status domain
SELECT 
    'CHECK_REDEMPTION_STATUS_DOMAIN' AS test_name,
    COUNT(*) AS failure_count
FROM SKYPOINTS_DW.GOLD_MARTS.FCT_MILEAGE_REDEMPTIONS
WHERE STATUS NOT IN ('COMPLETED', 'PENDING', 'CANCELLED');

-- Check 5C: Orphan Redemptions (Redemptions for non-existent members)
SELECT 
    'CHECK_ORPHAN_REDEMPTIONS' AS test_name,
    COUNT(r.TXN_ID) AS orphan_count
FROM SKYPOINTS_DW.GOLD_MARTS.FCT_MILEAGE_REDEMPTIONS r
LEFT JOIN SKYPOINTS_DW.GOLD_MARTS.DIM_MEMBERS_GLOBAL m
    ON r.MEMBER_ID = m.MEMBER_ID
WHERE m.MEMBER_ID IS NULL;
