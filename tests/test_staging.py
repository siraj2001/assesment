import pytest
from datetime import date
from skypoints.models import RawMemberRecord
from skypoints.processing.staging import stage_raw_records

def test_staging_happy_path_with_derived_columns():
    ref_date = date(2024, 1, 15)
    raw = [
        RawMemberRecord(
            member_name="Elena",
            member_id="223457",
            enrollment_date_raw="20101012",
            last_flight_date_raw="20121013",
            tier_code="GLD",
            agent_name="Sam",
            state="CA",
            country="USA",
            dob_raw="03051985",
            is_active="A"
        ),
        RawMemberRecord(
            member_name="RecentFlyer",
            member_id="223458",
            enrollment_date_raw="20200101",
            last_flight_date_raw="20240110",
            tier_code="SLV",
            country="IND",
            dob_raw="3051985",  # Unpadded integer
            is_active="A"
        ),
        RawMemberRecord(
            member_name="NeverFlown",
            member_id="223459",
            enrollment_date_raw="20200101",
            last_flight_date_raw=None,  # Never flown
            tier_code="PLT",
            country="AUS",
            dob_raw="01011990",
            is_active="A"
        )
    ]

    staged, quarantine = stage_raw_records(raw, reference_date=ref_date, batch_id="B001")

    assert len(quarantine) == 0
    assert len(staged) == 3

    # Elena: DOB 1985-03-05 -> Age 38 in Jan 2024. Flight 2012-10-13 (> 90 days) -> Stale 'Y'
    elena = staged[0]
    assert elena.member_name == "Elena"
    assert elena.member_id == "223457"
    assert elena.dob == date(1985, 3, 5)
    assert elena.age == 38
    assert elena.stale_member == "Y"
    assert elena.country == "USA"

    # RecentFlyer: Flight 2024-01-10 (5 days ago <= 90) -> Stale 'N'. Unpadded DOB handled.
    recent = staged[1]
    assert recent.member_id == "223458"
    assert recent.dob == date(1985, 3, 5)
    assert recent.age == 38
    assert recent.stale_member == "N"
    assert recent.country == "IND"

    # NeverFlown: Flight is None -> Stale 'Y'
    never = staged[2]
    assert never.last_flight_date is None
    assert never.stale_member == "Y"

def test_staging_quarantines_missing_mandatory_fields():
    ref_date = date(2024, 1, 15)
    raw = [
        # Missing Member Name
        RawMemberRecord(
            member_name=None,
            member_id="999001",
            enrollment_date_raw="20200101"
        ),
        # Missing Member ID
        RawMemberRecord(
            member_name="John Doe",
            member_id="",
            enrollment_date_raw="20200101"
        ),
        # Missing Enrollment Date
        RawMemberRecord(
            member_name="Jane Doe",
            member_id="999003",
            enrollment_date_raw=None
        ),
        # Invalid Enrollment Date (Month 13)
        RawMemberRecord(
            member_name="Bad Date",
            member_id="999004",
            enrollment_date_raw="2021-13-13"
        )
    ]

    staged, quarantine = stage_raw_records(raw, reference_date=ref_date, batch_id="B002")

    assert len(staged) == 0
    assert len(quarantine) == 4
    error_codes = [q.error_code for q in quarantine]
    assert "ERR_MANDATORY_NAME_MISSING" in error_codes
    assert "ERR_MANDATORY_ID_MISSING" in error_codes
    assert "ERR_MANDATORY_ENROLL_DATE_MISSING" in error_codes
    assert "ERR_INVALID_DATE" in error_codes
