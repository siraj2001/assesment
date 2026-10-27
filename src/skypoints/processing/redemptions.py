import json
from datetime import date
from typing import List, Dict, Any, Union, Optional
from collections import defaultdict
from skypoints.models import RedemptionTransaction, MemberRedemptionSummary, TargetMemberRecord
from skypoints.processing.date_utils import parse_flexible_date

def flatten_json_redemptions(
    payload: Union[str, List[Dict[str, Any]], Dict[str, Any]],
    batch_id: str = "DEFAULT"
) -> List[RedemptionTransaction]:
    """
    Parses semi-structured JSON redemption feed and flattens nested transactions.
    Extracts member_id, feed_date, txn_id, txn_date, partner, miles_redeemed, and status.
    """
    if isinstance(payload, str):
        data = json.loads(payload)
    else:
        data = payload

    if isinstance(data, dict):
        records = [data]
    elif isinstance(data, list):
        records = data
    else:
        records = []

    transactions: List[RedemptionTransaction] = []

    for entry in records:
        member_id = str(entry.get("member_id", "")).strip()
        feed_date_raw = entry.get("feed_date")
        feed_date = parse_flexible_date(feed_date_raw) or date.today()

        raw_redemptions = entry.get("redemptions", [])
        if not isinstance(raw_redemptions, list):
            continue

        for r in raw_redemptions:
            if not isinstance(r, dict):
                continue
            txn_id = str(r.get("txn_id", "")).strip()
            if not txn_id or not member_id:
                continue

            txn_date = parse_flexible_date(r.get("txn_date")) or feed_date
            partner = str(r.get("partner", "Unknown")).strip()
            try:
                miles = int(r.get("miles_redeemed", 0))
            except (ValueError, TypeError):
                miles = 0

            status = str(r.get("status", "PENDING")).strip().upper()

            transactions.append(RedemptionTransaction(
                txn_id=txn_id,
                member_id=member_id,
                feed_date=feed_date,
                txn_date=txn_date,
                partner=partner,
                miles_redeemed=miles,
                status=status,
                batch_id=batch_id
            ))

    return transactions

def aggregate_member_redemptions(
    transactions: List[RedemptionTransaction]
) -> Dict[str, MemberRedemptionSummary]:
    """
    Rolls up redemption transactions to the member grain.
    Provides 1-to-1 analytical metrics to enrich member profile data safely.
    """
    grouped: Dict[str, List[RedemptionTransaction]] = defaultdict(list)
    for t in transactions:
        grouped[t.member_id].append(t)

    summaries: Dict[str, MemberRedemptionSummary] = {}

    for member_id, txns in grouped.items():
        lifetime_redemptions = len(txns)
        total_miles = sum(t.miles_redeemed for t in txns)
        completed_miles = sum(t.miles_redeemed for t in txns if t.status == "COMPLETED")
        pending_miles = sum(t.miles_redeemed for t in txns if t.status == "PENDING")

        valid_dates = [t.txn_date for t in txns if t.txn_date]
        last_date = max(valid_dates) if valid_dates else None

        # Top partner by total miles
        partner_miles: Dict[str, int] = defaultdict(int)
        for t in txns:
            partner_miles[t.partner] += t.miles_redeemed
        top_partner = max(partner_miles.items(), key=lambda x: x[1])[0] if partner_miles else None

        summaries[member_id] = MemberRedemptionSummary(
            member_id=member_id,
            lifetime_redemptions=lifetime_redemptions,
            total_miles_redeemed=total_miles,
            completed_miles=completed_miles,
            pending_miles=pending_miles,
            last_redemption_date=last_date,
            top_partner=top_partner
        )

    return summaries

def enrich_member_profiles_with_redemptions(
    members: List[TargetMemberRecord],
    summaries: Dict[str, MemberRedemptionSummary]
) -> List[Dict[str, Any]]:
    """
    Joins member profiles with aggregated redemption metrics at 1-to-1 cardinality.
    Produces a Member 360 analytical dataset.
    """
    enriched: List[Dict[str, Any]] = []

    for m in members:
        s = summaries.get(m.member_id)
        enriched.append({
            "member_id": m.member_id,
            "member_name": m.member_name,
            "country": m.country,
            "state": m.state,
            "tier_code": m.tier_code,
            "enrollment_date": m.enrollment_date,
            "last_flight_date": m.last_flight_date,
            "dob": m.dob,
            "age": m.age,
            "stale_member": m.stale_member,
            "lifetime_redemptions": s.lifetime_redemptions if s else 0,
            "total_miles_redeemed": s.total_miles_redeemed if s else 0,
            "completed_miles": s.completed_miles if s else 0,
            "pending_miles": s.pending_miles if s else 0,
            "last_redemption_date": s.last_redemption_date if s else None,
            "top_partner": s.top_partner if s else None
        })

    return enriched
