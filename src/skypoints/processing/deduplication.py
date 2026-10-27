from datetime import date
from typing import List, Dict
from collections import defaultdict
from skypoints.models import StagedMemberRecord

def deduplicate_latest_records_wins(records: List[StagedMemberRecord]) -> List[StagedMemberRecord]:
    """
    Applies the 'latest record wins' rule to resolve member updates and migrations.
    Groups records by member_id and orders each group by:
      1. last_flight_date DESC (nulls last)
      2. enrollment_date DESC
      3. staging_timestamp DESC
    Returns the single most recent record for each member.
    """
    grouped: Dict[str, List[StagedMemberRecord]] = defaultdict(list)
    for rec in records:
        grouped[rec.member_id].append(rec)

    deduped: List[StagedMemberRecord] = []
    epoch = date(1970, 1, 1)

    for member_id, member_records in grouped.items():
        # Sort descending so index 0 is the latest
        sorted_records = sorted(
            member_records,
            key=lambda r: (
                r.last_flight_date or epoch,
                r.enrollment_date or epoch,
                r.staging_timestamp
            ),
            reverse=True
        )
        deduped.append(sorted_records[0])

    return deduped
