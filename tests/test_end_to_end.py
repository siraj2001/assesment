import pytest
import duckdb
from pathlib import Path
from datetime import date
from skypoints.pipeline import SkyPointsPipeline
from skypoints.config import RAW_DATA_DIR, PROCESSED_DATA_DIR

def test_pipeline_end_to_end(tmp_path):
    db_file = tmp_path / "test_skypoints.duckdb"
    pipeline = SkyPointsPipeline(
        reference_date=date(2024, 1, 15),
        db_path=db_file,
        batch_id="TEST_BATCH_001"
    )

    mem_file = RAW_DATA_DIR / "skypoints_members_with_anomalies.dat"
    json_file = RAW_DATA_DIR / "redemptions_sample.json"

    result = pipeline.run(member_file=mem_file, json_file=json_file)

    # 1. Verification of counts
    assert result["batch_id"] == "TEST_BATCH_001"
    assert result["raw_records_count"] == 10
    # 4 bad records quarantined (Missing Name, Missing ID, Missing Enroll, Invalid Date)
    assert result["quarantined_records_count"] == 4
    # 6 staged records (Elena x2, Ravi, Mateo, Nora, Jacob)
    assert result["staged_records_count"] == 6
    # 5 deduped records (Elena deduped into CAN; Ravi, Mateo, Nora, Jacob)
    assert result["deduped_records_count"] == 5

    # 2. Country Routing verification
    country_counts = result["country_tables"]
    assert country_counts.get("TABLE_CAN") == 2  # Elena (moved to CAN) and Nora
    assert country_counts.get("TABLE_IND") == 1  # Ravi
    assert country_counts.get("TABLE_PHIL") == 1 # Mateo
    assert country_counts.get("TABLE_AUS") == 1  # Jacob
    assert country_counts.get("TABLE_USA", 0) == 0 # Elena moved to CAN!

    # 3. DuckDB Table Verification
    con = duckdb.connect(str(db_file))
    tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
    assert "STG_MEMBER_PROFILES" in tables
    assert "QUARANTINE_REJECTED_RECORDS" in tables
    assert "TABLE_CAN" in tables
    assert "TABLE_IND" in tables
    assert "FCT_MILEAGE_REDEMPTIONS" in tables
    assert "V_MEMBER_360" in tables

    # Query Staging derived columns
    stg_df = con.execute("SELECT member_id, member_name, age, stale_member FROM STG_MEMBER_PROFILES").fetchdf()
    assert len(stg_df) == 6
    # Elena: age 38
    elena_stg = stg_df[stg_df["member_id"] == "223457"]
    assert elena_stg.iloc[0]["age"] == 38

    # Query Elena in TABLE_CAN (Latest Record Wins verification)
    can_df = con.execute("SELECT member_id, member_name, tier_code, country FROM TABLE_CAN WHERE member_id = '223457'").fetchdf()
    assert len(can_df) == 1
    assert can_df.iloc[0]["tier_code"] == "PLT"
    assert can_df.iloc[0]["country"] == "CAN"

    # Query V_MEMBER_360 enriched join
    m360_df = con.execute("SELECT member_id, lifetime_redemptions, total_miles_redeemed, top_partner FROM V_MEMBER_360 WHERE member_id = '223457'").fetchdf()
    assert len(m360_df) == 1
    assert m360_df.iloc[0]["lifetime_redemptions"] == 2
    assert m360_df.iloc[0]["total_miles_redeemed"] == 17000
    assert m360_df.iloc[0]["top_partner"] == "AeroLink"

    con.close()
