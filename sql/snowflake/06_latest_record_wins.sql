-- ============================================================================
-- Incubyte Data Craftsperson Assessment - SkyPoints Airline Loyalty Program
-- Step 6: Transformation Logic - Per-Country Splitting & Latest Record Wins (Deliverable 3)
-- ============================================================================
-- Deliverable 3 Requirement:
-- "Write the transformation logic (SQL and/or Python) to split members into
--  their per-country target tables, applying the 'latest record wins' rule
--  when a member has moved countries."
--
-- Craftsmanship Highlights:
-- 1. Deduplication Strategy ("Latest Record Wins"):
--    Uses ROW_NUMBER() window function partitioned by MEMBER_ID.
--    Ordered by:
--      a) LAST_FLIGHT_DATE DESC (most recent flight activity indicates current residence)
--      b) ENROLLMENT_DATE DESC
--      c) STAGING_TIMESTAMP DESC (latest batch tiebreaker)
-- 2. Target Routing:
--    Demonstrates both:
--      a) High-performance Snowflake Multi-Table INSERT (INSERT ALL) for static country targets
--      b) MERGE statements for idempotent upserts into individual country tables
--      c) Clustered DIM_MEMBERS_GLOBAL ingestion for dynamic partition pruning
-- ============================================================================

USE SCHEMA SKYPOINTS_DW.GOLD_MARTS;

-- ----------------------------------------------------------------------------
-- CTE / Temporary View: Deduplicated Staging Records with Latest Record Wins
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TEMPORARY VIEW V_LATEST_MEMBERS AS
WITH ranked_members AS (
    SELECT
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
        STAGING_TIMESTAMP,
        ROW_NUMBER() OVER (
            PARTITION BY MEMBER_ID
            ORDER BY 
                COALESCE(LAST_FLIGHT_DATE, DATE '1970-01-01') DESC,
                ENROLLMENT_DATE DESC,
                STAGING_TIMESTAMP DESC
        ) AS rank_order
    FROM SKYPOINTS_DW.SILVER_STAGING.STG_MEMBER_PROFILES
)
SELECT
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
    STAGING_TIMESTAMP
FROM ranked_members
WHERE rank_order = 1;

-- ----------------------------------------------------------------------------
-- Method A: Snowflake High-Throughput MULTI-TABLE INSERT (INSERT ALL)
-- Evaluates the country condition in a single pass over the deduplicated dataset.
-- ----------------------------------------------------------------------------
INSERT ALL
    WHEN COUNTRY = 'USA' THEN
        INTO TABLE_USA (
            MEMBER_ID, MEMBER_NAME, ENROLLMENT_DATE, LAST_FLIGHT_DATE,
            TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB,
            IS_ACTIVE, AGE, STALE_MEMBER, EFFECTIVE_START_DATE, IS_CURRENT, LAST_UPDATED_AT
        ) VALUES (
            MEMBER_ID, MEMBER_NAME, ENROLLMENT_DATE, LAST_FLIGHT_DATE,
            TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB,
            IS_ACTIVE, AGE, STALE_MEMBER, CURRENT_DATE(), TRUE, CURRENT_TIMESTAMP()
        )
    WHEN COUNTRY = 'IND' THEN
        INTO TABLE_IND (
            MEMBER_ID, MEMBER_NAME, ENROLLMENT_DATE, LAST_FLIGHT_DATE,
            TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB,
            IS_ACTIVE, AGE, STALE_MEMBER, EFFECTIVE_START_DATE, IS_CURRENT, LAST_UPDATED_AT
        ) VALUES (
            MEMBER_ID, MEMBER_NAME, ENROLLMENT_DATE, LAST_FLIGHT_DATE,
            TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB,
            IS_ACTIVE, AGE, STALE_MEMBER, CURRENT_DATE(), TRUE, CURRENT_TIMESTAMP()
        )
    WHEN COUNTRY IN ('AU', 'AUS') THEN
        INTO TABLE_AUS (
            MEMBER_ID, MEMBER_NAME, ENROLLMENT_DATE, LAST_FLIGHT_DATE,
            TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB,
            IS_ACTIVE, AGE, STALE_MEMBER, EFFECTIVE_START_DATE, IS_CURRENT, LAST_UPDATED_AT
        ) VALUES (
            MEMBER_ID, MEMBER_NAME, ENROLLMENT_DATE, LAST_FLIGHT_DATE,
            TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB,
            IS_ACTIVE, AGE, STALE_MEMBER, CURRENT_DATE(), TRUE, CURRENT_TIMESTAMP()
        )
    WHEN COUNTRY = 'CAN' THEN
        INTO TABLE_CAN (
            MEMBER_ID, MEMBER_NAME, ENROLLMENT_DATE, LAST_FLIGHT_DATE,
            TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB,
            IS_ACTIVE, AGE, STALE_MEMBER, EFFECTIVE_START_DATE, IS_CURRENT, LAST_UPDATED_AT
        ) VALUES (
            MEMBER_ID, MEMBER_NAME, ENROLLMENT_DATE, LAST_FLIGHT_DATE,
            TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB,
            IS_ACTIVE, AGE, STALE_MEMBER, CURRENT_DATE(), TRUE, CURRENT_TIMESTAMP()
        )
    WHEN COUNTRY = 'PHIL' THEN
        INTO TABLE_PHIL (
            MEMBER_ID, MEMBER_NAME, ENROLLMENT_DATE, LAST_FLIGHT_DATE,
            TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB,
            IS_ACTIVE, AGE, STALE_MEMBER, EFFECTIVE_START_DATE, IS_CURRENT, LAST_UPDATED_AT
        ) VALUES (
            MEMBER_ID, MEMBER_NAME, ENROLLMENT_DATE, LAST_FLIGHT_DATE,
            TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB,
            IS_ACTIVE, AGE, STALE_MEMBER, CURRENT_DATE(), TRUE, CURRENT_TIMESTAMP()
        )
SELECT * FROM V_LATEST_MEMBERS;

-- ----------------------------------------------------------------------------
-- Method B: Idempotent MERGE Pattern (Handles Member Migrations Across Countries)
-- If a member moved from USA to CAN, their previous entry in TABLE_USA is
-- marked IS_CURRENT = FALSE or deleted, and inserted into TABLE_CAN.
-- Example for TABLE_USA:
-- ----------------------------------------------------------------------------
MERGE INTO TABLE_USA t
USING (
    SELECT * FROM V_LATEST_MEMBERS WHERE COUNTRY = 'USA'
) s
ON t.MEMBER_ID = s.MEMBER_ID
WHEN MATCHED THEN
    UPDATE SET 
        t.MEMBER_NAME = s.MEMBER_NAME,
        t.ENROLLMENT_DATE = s.ENROLLMENT_DATE,
        t.LAST_FLIGHT_DATE = s.LAST_FLIGHT_DATE,
        t.TIER_CODE = s.TIER_CODE,
        t.AGENT_NAME = s.AGENT_NAME,
        t.STATE = s.STATE,
        t.POST_CODE = s.POST_CODE,
        t.DOB = s.DOB,
        t.IS_ACTIVE = s.IS_ACTIVE,
        t.AGE = s.AGE,
        t.STALE_MEMBER = s.STALE_MEMBER,
        t.IS_CURRENT = TRUE,
        t.LAST_UPDATED_AT = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
    INSERT (
        MEMBER_ID, MEMBER_NAME, ENROLLMENT_DATE, LAST_FLIGHT_DATE,
        TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB,
        IS_ACTIVE, AGE, STALE_MEMBER, EFFECTIVE_START_DATE, IS_CURRENT, LAST_UPDATED_AT
    ) VALUES (
        s.MEMBER_ID, s.MEMBER_NAME, s.ENROLLMENT_DATE, s.LAST_FLIGHT_DATE,
        s.TIER_CODE, s.AGENT_NAME, s.STATE, s.COUNTRY, s.POST_CODE, s.DOB,
        s.IS_ACTIVE, s.AGE, s.STALE_MEMBER, CURRENT_DATE(), TRUE, CURRENT_TIMESTAMP()
    );

-- Deactivate members in TABLE_USA who have migrated to another country
UPDATE TABLE_USA
SET IS_CURRENT = FALSE, LAST_UPDATED_AT = CURRENT_TIMESTAMP()
WHERE MEMBER_ID IN (
    SELECT MEMBER_ID FROM V_LATEST_MEMBERS WHERE COUNTRY != 'USA'
);

-- ----------------------------------------------------------------------------
-- Method C: Ingestion into Global Clustered Dimension (Enterprise Architecture)
-- ----------------------------------------------------------------------------
MERGE INTO DIM_MEMBERS_GLOBAL t
USING V_LATEST_MEMBERS s
ON t.MEMBER_ID = s.MEMBER_ID
WHEN MATCHED THEN
    UPDATE SET
        t.MEMBER_NAME = s.MEMBER_NAME,
        t.ENROLLMENT_DATE = s.ENROLLMENT_DATE,
        t.LAST_FLIGHT_DATE = s.LAST_FLIGHT_DATE,
        t.TIER_CODE = s.TIER_CODE,
        t.AGENT_NAME = s.AGENT_NAME,
        t.STATE = s.STATE,
        t.COUNTRY = s.COUNTRY,
        t.POST_CODE = s.POST_CODE,
        t.DOB = s.DOB,
        t.IS_ACTIVE = s.IS_ACTIVE,
        t.AGE = s.AGE,
        t.STALE_MEMBER = s.STALE_MEMBER,
        t.BATCH_ID = s.BATCH_ID,
        t.LAST_UPDATED_AT = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
    INSERT (
        MEMBER_ID, MEMBER_NAME, ENROLLMENT_DATE, LAST_FLIGHT_DATE,
        TIER_CODE, AGENT_NAME, STATE, COUNTRY, POST_CODE, DOB,
        IS_ACTIVE, AGE, STALE_MEMBER, BATCH_ID, LAST_UPDATED_AT
    ) VALUES (
        s.MEMBER_ID, s.MEMBER_NAME, s.ENROLLMENT_DATE, s.LAST_FLIGHT_DATE,
        s.TIER_CODE, s.AGENT_NAME, s.STATE, s.COUNTRY, s.POST_CODE, s.DOB,
        s.IS_ACTIVE, s.AGE, s.STALE_MEMBER, s.BATCH_ID, CURRENT_TIMESTAMP()
    );
