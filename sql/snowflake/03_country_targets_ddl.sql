-- ============================================================================
-- Incubyte Data Craftsperson Assessment - SkyPoints Airline Loyalty Program
-- Step 3: Country-Specific Target Tables (Gold) DDL for Snowflake
-- ============================================================================
-- Design Decision:
-- The assessment asks to "split up members based on country and load them into
-- corresponding country tables (e.g. Table_USA, Table_IND, Table_AUS, etc.)".
--
-- In Snowflake at billion-row scale, we provide:
-- 1. Explicit physical country tables (as requested by problem statement).
-- 2. Clustered Enterprise Pattern: Single partitioned DIM_MEMBERS_GLOBAL with
--    secure country views for RBAC & zero-maintenance country scaling.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS SKYPOINTS_DW.GOLD_MARTS;
USE SCHEMA SKYPOINTS_DW.GOLD_MARTS;

-- ----------------------------------------------------------------------------
-- 1. Country-Specific Physical Target Tables
-- ----------------------------------------------------------------------------

-- Table for USA Members
CREATE OR REPLACE TABLE TABLE_USA (
    MEMBER_SK               NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    MEMBER_ID               VARCHAR(18)        NOT NULL,
    MEMBER_NAME             VARCHAR(255)       NOT NULL,
    ENROLLMENT_DATE         DATE               NOT NULL,
    LAST_FLIGHT_DATE        DATE,
    TIER_CODE               VARCHAR(5),
    AGENT_NAME              VARCHAR(255),
    STATE                   VARCHAR(5),
    COUNTRY                 VARCHAR(5)         DEFAULT 'USA',
    POST_CODE               NUMBER(5, 0),
    DOB                     DATE,
    IS_ACTIVE               VARCHAR(1),
    AGE                     NUMBER(3, 0),
    STALE_MEMBER            VARCHAR(1)         NOT NULL,
    EFFECTIVE_START_DATE    DATE               NOT NULL,
    IS_CURRENT              BOOLEAN            DEFAULT TRUE,
    LAST_UPDATED_AT         TIMESTAMP_NTZ      DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_TABLE_USA PRIMARY KEY (MEMBER_ID) RELY
)
CLUSTER BY (MEMBER_ID, STATE)
COMMENT = 'Gold country mart for United States SkyPoints members';

-- Table for India Members
CREATE OR REPLACE TABLE TABLE_IND (
    MEMBER_SK               NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    MEMBER_ID               VARCHAR(18)        NOT NULL,
    MEMBER_NAME             VARCHAR(255)       NOT NULL,
    ENROLLMENT_DATE         DATE               NOT NULL,
    LAST_FLIGHT_DATE        DATE,
    TIER_CODE               VARCHAR(5),
    AGENT_NAME              VARCHAR(255),
    STATE                   VARCHAR(5),
    COUNTRY                 VARCHAR(5)         DEFAULT 'IND',
    POST_CODE               NUMBER(5, 0),
    DOB                     DATE,
    IS_ACTIVE               VARCHAR(1),
    AGE                     NUMBER(3, 0),
    STALE_MEMBER            VARCHAR(1)         NOT NULL,
    EFFECTIVE_START_DATE    DATE               NOT NULL,
    IS_CURRENT              BOOLEAN            DEFAULT TRUE,
    LAST_UPDATED_AT         TIMESTAMP_NTZ      DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_TABLE_IND PRIMARY KEY (MEMBER_ID) RELY
)
CLUSTER BY (MEMBER_ID, STATE)
COMMENT = 'Gold country mart for India SkyPoints members';

-- Table for Australia Members
CREATE OR REPLACE TABLE TABLE_AUS (
    MEMBER_SK               NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    MEMBER_ID               VARCHAR(18)        NOT NULL,
    MEMBER_NAME             VARCHAR(255)       NOT NULL,
    ENROLLMENT_DATE         DATE               NOT NULL,
    LAST_FLIGHT_DATE        DATE,
    TIER_CODE               VARCHAR(5),
    AGENT_NAME              VARCHAR(255),
    STATE                   VARCHAR(5),
    COUNTRY                 VARCHAR(5)         DEFAULT 'AU',
    POST_CODE               NUMBER(5, 0),
    DOB                     DATE,
    IS_ACTIVE               VARCHAR(1),
    AGE                     NUMBER(3, 0),
    STALE_MEMBER            VARCHAR(1)         NOT NULL,
    EFFECTIVE_START_DATE    DATE               NOT NULL,
    IS_CURRENT              BOOLEAN            DEFAULT TRUE,
    LAST_UPDATED_AT         TIMESTAMP_NTZ      DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_TABLE_AUS PRIMARY KEY (MEMBER_ID) RELY
)
CLUSTER BY (MEMBER_ID, STATE)
COMMENT = 'Gold country mart for Australia SkyPoints members';

-- Table for Canada Members
CREATE OR REPLACE TABLE TABLE_CAN (
    MEMBER_SK               NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    MEMBER_ID               VARCHAR(18)        NOT NULL,
    MEMBER_NAME             VARCHAR(255)       NOT NULL,
    ENROLLMENT_DATE         DATE               NOT NULL,
    LAST_FLIGHT_DATE        DATE,
    TIER_CODE               VARCHAR(5),
    AGENT_NAME              VARCHAR(255),
    STATE                   VARCHAR(5),
    COUNTRY                 VARCHAR(5)         DEFAULT 'CAN',
    POST_CODE               NUMBER(5, 0),
    DOB                     DATE,
    IS_ACTIVE               VARCHAR(1),
    AGE                     NUMBER(3, 0),
    STALE_MEMBER            VARCHAR(1)         NOT NULL,
    EFFECTIVE_START_DATE    DATE               NOT NULL,
    IS_CURRENT              BOOLEAN            DEFAULT TRUE,
    LAST_UPDATED_AT         TIMESTAMP_NTZ      DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_TABLE_CAN PRIMARY KEY (MEMBER_ID) RELY
)
CLUSTER BY (MEMBER_ID, STATE)
COMMENT = 'Gold country mart for Canada SkyPoints members';

-- Table for Philippines Members
CREATE OR REPLACE TABLE TABLE_PHIL (
    MEMBER_SK               NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    MEMBER_ID               VARCHAR(18)        NOT NULL,
    MEMBER_NAME             VARCHAR(255)       NOT NULL,
    ENROLLMENT_DATE         DATE               NOT NULL,
    LAST_FLIGHT_DATE        DATE,
    TIER_CODE               VARCHAR(5),
    AGENT_NAME              VARCHAR(255),
    STATE                   VARCHAR(5),
    COUNTRY                 VARCHAR(5)         DEFAULT 'PHIL',
    POST_CODE               NUMBER(5, 0),
    DOB                     DATE,
    IS_ACTIVE               VARCHAR(1),
    AGE                     NUMBER(3, 0),
    STALE_MEMBER            VARCHAR(1)         NOT NULL,
    EFFECTIVE_START_DATE    DATE               NOT NULL,
    IS_CURRENT              BOOLEAN            DEFAULT TRUE,
    LAST_UPDATED_AT         TIMESTAMP_NTZ      DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_TABLE_PHIL PRIMARY KEY (MEMBER_ID) RELY
)
CLUSTER BY (MEMBER_ID, STATE)
COMMENT = 'Gold country mart for Philippines SkyPoints members';

-- ----------------------------------------------------------------------------
-- 2. Enterprise Unified Clustered Dimension (Scale to Billions)
-- Architectural Alternative: Avoids managing hundreds of DDL migrations
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE DIM_MEMBERS_GLOBAL (
    MEMBER_SK               NUMBER AUTOINCREMENT START 1 INCREMENT 1,
    MEMBER_ID               VARCHAR(18)        NOT NULL,
    MEMBER_NAME             VARCHAR(255)       NOT NULL,
    ENROLLMENT_DATE         DATE               NOT NULL,
    LAST_FLIGHT_DATE        DATE,
    TIER_CODE               VARCHAR(5),
    AGENT_NAME              VARCHAR(255),
    STATE                   VARCHAR(5),
    COUNTRY                 VARCHAR(5)         NOT NULL,
    POST_CODE               NUMBER(5, 0),
    DOB                     DATE,
    IS_ACTIVE               VARCHAR(1),
    AGE                     NUMBER(3, 0),
    STALE_MEMBER            VARCHAR(1)         NOT NULL,
    BATCH_ID                VARCHAR(64)        NOT NULL,
    LAST_UPDATED_AT         TIMESTAMP_NTZ      DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_DIM_MEMBERS PRIMARY KEY (MEMBER_ID) RELY
)
CLUSTER BY (COUNTRY, TIER_CODE)
COMMENT = 'Global clustered member dimension with partition pruning across countries';
