import pytest
from datetime import date
from skypoints.models import StagedMemberRecord, RedemptionTransaction
from skypoints.validation.validator import (
    validate_mandatory_fields,
    validate_key_uniqueness,
    validate_domain_rules,
    validate_redemptions_data_quality
)

def test_validate_mandatory_fields_passes_on_clean_data():
    records = [
        StagedMemberRecord(
            member_name="Elena",
            member_id="223457",
            enrollment_date=date(2010, 10, 12),
            last_flight_date=date(2012, 10, 13),
            tier_code="GLD",
            agent_name="Sam",
            state="CA",
            country="USA",
            post_code=None,
            dob=date(1985, 3, 5),
            is_active="A",
            age=38,
            stale_member="Y",
            batch_id="B001",
            source_file="f1.dat",
            record_hash="h1"
        )
    ]
    res = validate_mandatory_fields(records)
    assert res.is_valid is True
    assert res.failure_count == 0

def test_validate_key_uniqueness_detects_duplicates():
    # Two records with same member_id in the target table (should be deduplicated!)
    records = [
        StagedMemberRecord(
            member_name="Elena",
            member_id="223457",
            enrollment_date=date(2010, 10, 12),
            last_flight_date=date(2012, 10, 13),
            tier_code="GLD",
            agent_name="Sam",
            state="CA",
            country="USA",
            post_code=None,
            dob=date(1985, 3, 5),
            is_active="A",
            age=38,
            stale_member="Y",
            batch_id="B001",
            source_file="f1.dat",
            record_hash="h1"
        ),
        StagedMemberRecord(
            member_name="DuplicateElena",
            member_id="223457",
            enrollment_date=date(2010, 10, 12),
            last_flight_date=date(2013, 10, 13),
            tier_code="PLT",
            agent_name="Sam",
            state="CA",
            country="USA",
            post_code=None,
            dob=date(1985, 3, 5),
            is_active="A",
            age=38,
            stale_member="Y",
            batch_id="B001",
            source_file="f1.dat",
            record_hash="h2"
        )
    ]
    res = validate_key_uniqueness(records)
    assert res.is_valid is False
    assert res.failure_count >= 1
    assert "223457" in res.failures[0]

def test_validate_domain_rules_flags_invalid_age():
    records = [
        StagedMemberRecord(
            member_name="AncientOne",
            member_id="111",
            enrollment_date=date(2020, 1, 1),
            last_flight_date=None,
            tier_code="GLD",
            agent_name=None,
            state=None,
            country="USA",
            post_code=None,
            dob=date(1800, 1, 1),
            is_active="A",
            age=224,  # > 120
            stale_member="Y",
            batch_id="B001",
            source_file="f1.dat",
            record_hash="h1"
        )
    ]
    res = validate_domain_rules(records)
    assert res.is_valid is False
    assert any("age" in f.lower() for f in res.failures)

def test_validate_redemptions_detects_negative_miles_and_orphans():
    txns = [
        RedemptionTransaction(
            txn_id="TX1",
            member_id="999",  # Orphan member
            feed_date=date(2024, 1, 15),
            txn_date=date(2024, 1, 10),
            partner="AeroLink",
            miles_redeemed=-500,  # Negative miles
            status="INVALID_STATUS"
        )
    ]
    valid_members = {"223457", "223458"}
    res = validate_redemptions_data_quality(txns, valid_members)
    assert res.is_valid is False
    assert res.failure_count >= 2
