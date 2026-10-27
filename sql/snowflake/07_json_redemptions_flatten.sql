-- ============================================================================
-- Incubyte Data Craftsperson Assessment - SkyPoints Airline Loyalty Program
-- Step 7: Semi-Structured JSON Flattening & Analytical Profile Join (Deliverable 4)
-- ============================================================================
-- Deliverable 4 Requirements:
-- "Parse the semi-structured JSON redemption feed into a flattened, queryable
--  table, and describe how you would join it back to the member profile data."
--
-- Craftsmanship Highlights:
-- 1. Uses Snowflake LATERAL FLATTEN on the nested `redemptions` array.
-- 2. Strongly casts all JSON keys with error handling (TRY_TO_DATE, TRY_TO_NUMBER).
-- 3. Solves the Fan-Out Dilemma: Explains and provides:
--      a) Grain-level Fact-to-Dimension transactional join.
--      b) Member-grain Aggregation Mart to safely join back to Member Profiles
--         without multiplying rows (preventing cartesian fan-out bugs).
-- ============================================================================

USE SCHEMA SKYPOINTS_DW.GOLD_MARTS;

-- ----------------------------------------------------------------------------
-- 1. Parse & Flatten JSON Feed into FCT_MILEAGE_REDEMPTIONS
-- ----------------------------------------------------------------------------
MERGE INTO FCT_MILEAGE_REDEMPTIONS t
USING (
    SELECT
        r.value:txn_id::VARCHAR(64)                        AS txn_id,
        raw.RAW_PAYLOAD:member_id::VARCHAR(18)              AS member_id,
        TRY_TO_DATE(raw.RAW_PAYLOAD:feed_date::VARCHAR, 'YYYYMMDD') AS feed_date,
        TRY_TO_DATE(r.value:txn_date::VARCHAR, 'YYYYMMDD')  AS txn_date,
        r.value:partner::VARCHAR(100)                      AS partner_airline,
        TRY_TO_NUMBER(r.value:miles_redeemed::VARCHAR)     AS miles_redeemed,
        UPPER(r.value:status::VARCHAR(20))                 AS status,
        raw.BATCH_ID                                       AS batch_id,
        raw.INGESTION_TIMESTAMP                            AS ingestion_timestamp
    FROM SKYPOINTS_DW.BRONZE_RAW.RAW_REDEMPTION_FEED_LANDING raw,
         LATERAL FLATTEN(input => raw.RAW_PAYLOAD:redemptions) r
    WHERE r.value:txn_id IS NOT NULL
      AND raw.RAW_PAYLOAD:member_id IS NOT NULL
) s
ON t.TXN_ID = s.TXN_ID
WHEN MATCHED THEN
    UPDATE SET
        t.MEMBER_ID = s.MEMBER_ID,
        t.FEED_DATE = s.FEED_DATE,
        t.TXN_DATE = s.TXN_DATE,
        t.PARTNER_AIRLINE = s.PARTNER_AIRLINE,
        t.MILES_REDEEMED = s.MILES_REDEEMED,
        t.STATUS = s.STATUS,
        t.BATCH_ID = s.BATCH_ID,
        t.INGESTION_TIMESTAMP = s.INGESTION_TIMESTAMP
WHEN NOT MATCHED THEN
    INSERT (
        TXN_ID, MEMBER_ID, FEED_DATE, TXN_DATE, PARTNER_AIRLINE,
        MILES_REDEEMED, STATUS, BATCH_ID, INGESTION_TIMESTAMP
    ) VALUES (
        s.TXN_ID, s.MEMBER_ID, s.FEED_DATE, s.TXN_DATE, s.PARTNER_AIRLINE,
        s.MILES_REDEEMED, s.STATUS, s.BATCH_ID, s.INGESTION_TIMESTAMP
    );

-- ----------------------------------------------------------------------------
-- 2. Populate Member Redemptions Summary Mart (Grain: 1 row per Member)
-- ----------------------------------------------------------------------------
MERGE INTO AGG_MEMBER_REDEMPTION_METRICS t
USING (
    WITH partner_ranking AS (
        SELECT 
            MEMBER_ID,
            PARTNER_AIRLINE,
            SUM(MILES_REDEEMED) AS partner_miles,
            ROW_NUMBER() OVER (PARTITION BY MEMBER_ID ORDER BY SUM(MILES_REDEEMED) DESC) AS rnk
        FROM FCT_MILEAGE_REDEMPTIONS
        GROUP BY MEMBER_ID, PARTNER_AIRLINE
    )
    SELECT
        f.MEMBER_ID,
        COUNT(f.TXN_ID)                                             AS lifetime_redemptions,
        SUM(f.MILES_REDEEMED)                                       AS total_miles_redeemed,
        SUM(CASE WHEN f.STATUS = 'COMPLETED' THEN f.MILES_REDEEMED ELSE 0 END) AS completed_miles,
        SUM(CASE WHEN f.STATUS = 'PENDING' THEN f.MILES_REDEEMED ELSE 0 END)   AS pending_miles,
        MAX(f.TXN_DATE)                                             AS last_redemption_date,
        p.PARTNER_AIRLINE                                           AS top_partner
    FROM FCT_MILEAGE_REDEMPTIONS f
    LEFT JOIN partner_ranking p 
        ON f.MEMBER_ID = p.MEMBER_ID AND p.rnk = 1
    GROUP BY f.MEMBER_ID, p.PARTNER_AIRLINE
) s
ON t.MEMBER_ID = s.MEMBER_ID
WHEN MATCHED THEN
    UPDATE SET
        t.LIFETIME_REDEMPTIONS = s.lifetime_redemptions,
        t.TOTAL_MILES_REDEEMED = s.total_miles_redeemed,
        t.COMPLETED_MILES = s.completed_miles,
        t.PENDING_MILES = s.pending_miles,
        t.LAST_REDEMPTION_DATE = s.last_redemption_date,
        t.TOP_PARTNER = s.top_partner,
        t.LAST_CALCULATED_AT = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
    INSERT (
        MEMBER_ID, LIFETIME_REDEMPTIONS, TOTAL_MILES_REDEEMED,
        COMPLETED_MILES, PENDING_MILES, LAST_REDEMPTION_DATE, TOP_PARTNER, LAST_CALCULATED_AT
    ) VALUES (
        s.MEMBER_ID, s.lifetime_redemptions, s.total_miles_redeemed,
        s.completed_miles, s.pending_miles, s.last_redemption_date, s.top_partner, CURRENT_TIMESTAMP()
    );

-- ----------------------------------------------------------------------------
-- 3. How to Join Back to Member Profile Data
-- ----------------------------------------------------------------------------
-- Pattern A: Member 360 View (1-to-1 Safe Join - NO Fan-out)
-- Joins country member profiles with pre-aggregated redemption metrics.
-- Every member remains exactly 1 row; member counts and financial totals stay accurate.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW V_MEMBER_360_USA AS
SELECT 
    m.MEMBER_ID,
    m.MEMBER_NAME,
    m.TIER_CODE,
    m.STATE,
    m.COUNTRY,
    m.DOB,
    m.AGE,
    m.ENROLLMENT_DATE,
    m.LAST_FLIGHT_DATE,
    m.STALE_MEMBER,
    COALESCE(r.LIFETIME_REDEMPTIONS, 0)    AS LIFETIME_REDEMPTIONS,
    COALESCE(r.TOTAL_MILES_REDEEMED, 0)    AS TOTAL_MILES_REDEEMED,
    COALESCE(r.COMPLETED_MILES, 0)         AS COMPLETED_MILES,
    COALESCE(r.PENDING_MILES, 0)           AS PENDING_MILES,
    r.LAST_REDEMPTION_DATE,
    r.TOP_PARTNER
FROM TABLE_USA m
LEFT JOIN AGG_MEMBER_REDEMPTION_METRICS r
    ON m.MEMBER_ID = r.MEMBER_ID;

-- ----------------------------------------------------------------------------
-- Pattern B: Detailed Transactional View (1-to-Many Join)
-- Used when business needs granular event audit or partner reconciliation.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW V_MEMBER_REDEMPTION_TRANSACTIONS AS
SELECT 
    m.COUNTRY,
    m.MEMBER_ID,
    m.MEMBER_NAME,
    m.TIER_CODE,
    r.TXN_ID,
    r.TXN_DATE,
    r.PARTNER_AIRLINE,
    r.MILES_REDEEMED,
    r.STATUS
FROM DIM_MEMBERS_GLOBAL m
INNER JOIN FCT_MILEAGE_REDEMPTIONS r
    ON m.MEMBER_ID = r.MEMBER_ID;
