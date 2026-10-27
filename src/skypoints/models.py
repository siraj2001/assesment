from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List, Dict, Any

@dataclass
class RawMemberRecord:
    member_name: Optional[str] = None
    member_id: Optional[str] = None
    enrollment_date_raw: Optional[str] = None
    last_flight_date_raw: Optional[str] = None
    tier_code: Optional[str] = None
    agent_name: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    post_code_raw: Optional[str] = None
    dob_raw: Optional[str] = None
    is_active: Optional[str] = "A"
    source_file: str = "unknown"
    row_num: int = 0
    raw_line: str = ""

@dataclass
class StagedMemberRecord:
    member_name: str
    member_id: str
    enrollment_date: date
    last_flight_date: Optional[date]
    tier_code: Optional[str]
    agent_name: Optional[str]
    state: Optional[str]
    country: Optional[str]
    post_code: Optional[int]
    dob: Optional[date]
    is_active: str
    age: Optional[int]
    stale_member: str  # 'Y' or 'N'
    batch_id: str
    source_file: str
    record_hash: str
    staging_timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class TargetMemberRecord(StagedMemberRecord):
    is_current: bool = True
    effective_start_date: Optional[date] = None

@dataclass
class RedemptionTransaction:
    txn_id: str
    member_id: str
    feed_date: date
    txn_date: date
    partner: str
    miles_redeemed: int
    status: str
    batch_id: str = "DEFAULT"

@dataclass
class MemberRedemptionSummary:
    member_id: str
    lifetime_redemptions: int
    total_miles_redeemed: int
    completed_miles: int
    pending_miles: int
    last_redemption_date: Optional[date]
    top_partner: Optional[str]

@dataclass
class QuarantineRecord:
    batch_id: str
    source_file: str
    source_row: int
    raw_payload: str
    error_code: str
    error_message: str
    failed_field: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
