import pytest
from datetime import date
from skypoints.models import TargetMemberRecord
from skypoints.processing.redemptions import (
    flatten_json_redemptions,
    aggregate_member_redemptions,
    enrich_member_profiles_with_redemptions
)

SAMPLE_JSON = [
    {
        "member_id": "223457",
        "feed_date": "20240115",
        "redemptions": [
            {
                "txn_id": "RX10091",
                "txn_date": "20240110",
                "partner": "AeroLink",
                "miles_redeemed": 12000,
                "status": "COMPLETED"
            },
            {
                "txn_id": "RX10092",
                "txn_date": "20240113",
                "partner": "SkyPoints",
                "miles_redeemed": 5000,
                "status": "PENDING"
            }
        ]
    },
    {
        "member_id": "223458",
        "feed_date": "20240115",
        "redemptions": [
            {
                "txn_id": "RX10093",
                "txn_date": "20240111",
                "partner": "AirIndia",
                "miles_redeemed": 8500,
                "status": "COMPLETED"
            }
        ]
    }
]

def test_flatten_json_redemptions():
    txns = flatten_json_redemptions(SAMPLE_JSON)
    assert len(txns) == 3

    t1 = txns[0]
    assert t1.txn_id == "RX10091"
    assert t1.member_id == "223457"
    assert t1.feed_date == date(2024, 1, 15)
    assert t1.txn_date == date(2024, 1, 10)
    assert t1.partner == "AeroLink"
    assert t1.miles_redeemed == 12000
    assert t1.status == "COMPLETED"

    t2 = txns[1]
    assert t2.txn_id == "RX10092"
    assert t2.miles_redeemed == 5000
    assert t2.status == "PENDING"

def test_aggregate_member_redemptions():
    txns = flatten_json_redemptions(SAMPLE_JSON)
    summaries = aggregate_member_redemptions(txns)

    assert "223457" in summaries
    s1 = summaries["223457"]
    assert s1.lifetime_redemptions == 2
    assert s1.total_miles_redeemed == 17000
    assert s1.completed_miles == 12000
    assert s1.pending_miles == 5000
    assert s1.last_redemption_date == date(2024, 1, 13)
    assert s1.top_partner == "AeroLink"

    assert "223458" in summaries
    s2 = summaries["223458"]
    assert s2.lifetime_redemptions == 1
    assert s2.total_miles_redeemed == 8500
    assert s2.top_partner == "AirIndia"

def test_enrich_member_profiles_with_redemptions():
    members = [
        TargetMemberRecord(
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
            source_file="f.dat",
            record_hash="h1"
        ),
        TargetMemberRecord(
            member_name="NeverRedeemed",
            member_id="999999",
            enrollment_date=date(2020, 1, 1),
            last_flight_date=None,
            tier_code="SLV",
            agent_name="Agent",
            state="NY",
            country="USA",
            post_code=None,
            dob=None,
            is_active="A",
            age=None,
            stale_member="Y",
            batch_id="B001",
            source_file="f.dat",
            record_hash="h2"
        )
    ]

    txns = flatten_json_redemptions(SAMPLE_JSON)
    summaries = aggregate_member_redemptions(txns)

    enriched = enrich_member_profiles_with_redemptions(members, summaries)
    assert len(enriched) == 2

    # Elena has redemptions
    elena = enriched[0]
    assert elena["member_id"] == "223457"
    assert elena["lifetime_redemptions"] == 2
    assert elena["total_miles_redeemed"] == 17000
    assert elena["top_partner"] == "AeroLink"

    # NeverRedeemed has 0 redemptions (safe default, no NULL errors)
    never = enriched[1]
    assert never["member_id"] == "999999"
    assert never["lifetime_redemptions"] == 0
    assert never["total_miles_redeemed"] == 0
    assert never["top_partner"] is None
