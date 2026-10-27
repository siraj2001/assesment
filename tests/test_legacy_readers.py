from pathlib import Path
from skypoints.config import RAW_DATA_DIR
from skypoints.ingestion.legacy_reader import (
    read_legacy_usa_csv,
    read_legacy_ind_csv,
    read_legacy_aus_xlsx
)
from skypoints.processing.staging import stage_raw_records

def test_read_usa_csv():
    usa_file = RAW_DATA_DIR / "USA.csv"
    records = read_legacy_usa_csv(usa_file)
    assert len(records) == 3
    # 1,Sam,PLT,6152022,8202022
    sam = records[0]
    assert sam.member_name == "Sam"
    assert sam.tier_code == "PLT"
    assert sam.country == "USA"

    # Stage them
    staged, quarantine = stage_raw_records(records)
    assert len(staged) == 3
    assert len(quarantine) == 0

def test_read_ind_csv():
    ind_file = RAW_DATA_DIR / "IND.csv"
    records = read_legacy_ind_csv(ind_file)
    assert len(records) == 3
    # 1,Vikas,12/1/1998,SLV,1/1/2022,I,6/15/2022
    vikas = records[0]
    assert vikas.member_name == "Vikas"
    assert vikas.tier_code == "SLV"
    assert vikas.country == "IND"

    # Stage them
    staged, quarantine = stage_raw_records(records)
    assert len(staged) == 3
    assert len(quarantine) == 0

def test_read_aus_xlsx_and_catch_anomalies():
    aus_file = RAW_DATA_DIR / "AUS.xlsx"
    records = read_legacy_aus_xlsx(aus_file)
    assert len(records) == 3

    # Row 1: Mike with 'NULL' DOB
    mike = records[0]
    assert mike.member_name == "Mike"
    assert mike.dob_raw == "NULL"

    # Row 2: Jonnathan with invalid date '2021-13-13' (month 13!)
    jonnathan = records[1]
    assert jonnathan.enrollment_date_raw == "2021-13-13"

    # Stage them: Jonnathan should be routed to quarantine due to invalid enrollment date!
    staged, quarantine = stage_raw_records(records)
    assert len(quarantine) == 1
    assert quarantine[0].error_code == "ERR_INVALID_DATE"
    assert "2021-13-13" in quarantine[0].error_message

    # Mike and Cristina should be staged successfully
    assert len(staged) == 2
    staged_names = [s.member_name for s in staged]
    assert "Mike" in staged_names
    assert "Cristina" in staged_names
