import pytest
from datetime import date
from skypoints.models import StagedMemberRecord
from skypoints.processing.deduplication import deduplicate_latest_records_wins
from skypoints.processing.country_router import route_members_to_country_tables

def test_deduplicate_member_moved_country_latest_record_wins():
    records = [
        # Older record: Elena in USA with flight 2012-10-13
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
            source_file="file1.dat",
            record_hash="hash1"
        ),
        # Newer record: Elena moved to Canada with flight 2023-12-01
        StagedMemberRecord(
            member_name="Elena",
            member_id="223457",
            enrollment_date=date(2010, 10, 12),
            last_flight_date=date(2023, 12, 1),
            tier_code="PLT",
            agent_name="Sam",
            state="ONT",
            country="CAN",
            post_code=None,
            dob=date(1985, 3, 5),
            is_active="A",
            age=38,
            stale_member="N",
            batch_id="B002",
            source_file="file2.dat",
            record_hash="hash2"
        ),
        # Unrelated member: Ravi in India
        StagedMemberRecord(
            member_name="Ravi",
            member_id="223458",
            enrollment_date=date(2010, 10, 12),
            last_flight_date=date(2024, 1, 10),
            tier_code="SLV",
            agent_name="Sam",
            state="TN",
            country="IND",
            post_code=None,
            dob=date(1985, 3, 5),
            is_active="A",
            age=38,
            stale_member="N",
            batch_id="B002",
            source_file="file2.dat",
            record_hash="hash3"
        )
    ]

    deduped = deduplicate_latest_records_wins(records)

    # There should only be 2 unique members
    assert len(deduped) == 2
    deduped_map = {m.member_id: m for m in deduped}

    # Elena must now be in Canada (latest flight date wins)
    elena = deduped_map["223457"]
    assert elena.country == "CAN"
    assert elena.tier_code == "PLT"
    assert elena.last_flight_date == date(2023, 12, 1)

    # Route to country tables
    country_tables = route_members_to_country_tables(deduped)

    # Elena should be in TABLE_CAN and NOT in TABLE_USA
    assert len(country_tables.get("TABLE_CAN", [])) == 1
    assert country_tables["TABLE_CAN"][0].member_id == "223457"
    assert len(country_tables.get("TABLE_USA", [])) == 0

    # Ravi should be in TABLE_IND
    assert len(country_tables.get("TABLE_IND", [])) == 1
    assert country_tables["TABLE_IND"][0].member_id == "223458"
