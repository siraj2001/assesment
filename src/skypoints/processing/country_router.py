from typing import List, Dict
from collections import defaultdict
from skypoints.models import StagedMemberRecord, TargetMemberRecord
from skypoints.config import COUNTRY_NORMALIZE_MAP, SUPPORTED_COUNTRY_TABLES

def route_members_to_country_tables(
    records: List[StagedMemberRecord]
) -> Dict[str, List[TargetMemberRecord]]:
    """
    Routes deduplicated members into country-specific target tables.
    Matches tables like TABLE_USA, TABLE_IND, TABLE_AUS, TABLE_CAN, TABLE_PHIL.
    Unknown or missing countries are routed to TABLE_OTHER.
    """
    country_tables: Dict[str, List[TargetMemberRecord]] = defaultdict(list)

    for rec in records:
        country_norm = None
        if rec.country:
            c = rec.country.strip().upper()
            country_norm = COUNTRY_NORMALIZE_MAP.get(c, c)

        table_name = f"TABLE_{country_norm}" if country_norm else "TABLE_OTHER"

        target_rec = TargetMemberRecord(
            member_name=rec.member_name,
            member_id=rec.member_id,
            enrollment_date=rec.enrollment_date,
            last_flight_date=rec.last_flight_date,
            tier_code=rec.tier_code,
            agent_name=rec.agent_name,
            state=rec.state,
            country=country_norm or "UNKNOWN",
            post_code=rec.post_code,
            dob=rec.dob,
            is_active=rec.is_active,
            age=rec.age,
            stale_member=rec.stale_member,
            batch_id=rec.batch_id,
            source_file=rec.source_file,
            record_hash=rec.record_hash,
            staging_timestamp=rec.staging_timestamp,
            is_current=True,
            effective_start_date=rec.enrollment_date
        )

        country_tables[table_name].append(target_rec)

    return dict(country_tables)
