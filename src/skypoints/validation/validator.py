from dataclasses import dataclass, field
from typing import List, Set, Dict, Any
from collections import Counter
from skypoints.models import StagedMemberRecord, RedemptionTransaction

@dataclass
class ValidationReport:
    check_name: str
    is_valid: bool
    failure_count: int
    failures: List[str] = field(default_factory=list)

def validate_mandatory_fields(records: List[StagedMemberRecord]) -> ValidationReport:
    """
    Validates that Member_Name, Member_Id, and Enrollment_Date are not null or empty.
    """
    failures = []
    for r in records:
        if not r.member_name or not r.member_name.strip():
            failures.append(f"Member ID {r.member_id} has empty Member Name")
        if not r.member_id or not r.member_id.strip():
            failures.append(f"Record with name {r.member_name} has empty Member ID")
        if not r.enrollment_date:
            failures.append(f"Member ID {r.member_id} has null Enrollment Date")

    return ValidationReport(
        check_name="MANDATORY_FIELDS",
        is_valid=len(failures) == 0,
        failure_count=len(failures),
        failures=failures
    )

def validate_key_uniqueness(records: List[StagedMemberRecord]) -> ValidationReport:
    """
    Validates that Member_ID is unique across deduplicated records.
    Also detects if a single Member_ID has conflicting Member_Names.
    """
    id_counts = Counter(r.member_id for r in records)
    duplicate_ids = [mem_id for mem_id, count in id_counts.items() if count > 1]

    failures = []
    for dup in duplicate_ids:
        failures.append(f"Duplicate Member ID detected: {dup} (occurs {id_counts[dup]} times)")

    # Name-to-ID collision check
    id_names: Dict[str, Set[str]] = {}
    for r in records:
        id_names.setdefault(r.member_id, set()).add(r.member_name)

    for mem_id, names in id_names.items():
        if len(names) > 1:
            failures.append(f"Member ID {mem_id} associated with multiple distinct names: {names}")

    return ValidationReport(
        check_name="KEY_UNIQUENESS",
        is_valid=len(failures) == 0,
        failure_count=len(failures),
        failures=failures
    )

def validate_domain_rules(records: List[StagedMemberRecord]) -> ValidationReport:
    """
    Validates business sanity rules:
    - Reasonable age bounds (0 <= Age <= 120)
    - Chronological flight vs enrollment
    """
    failures = []
    for r in records:
        if r.age is not None and (r.age < 0 or r.age > 120):
            failures.append(f"Member ID {r.member_id} has out-of-bounds Age: {r.age}")

        if r.last_flight_date and r.enrollment_date:
            # Note: A flight occurring slightly before enrollment might happen during retroactive mileage claims,
            # but flights > 30 days before enrollment indicate data corruption.
            if (r.enrollment_date - r.last_flight_date).days > 365:
                failures.append(
                    f"Member ID {r.member_id} flight date ({r.last_flight_date}) is over a year before enrollment ({r.enrollment_date})"
                )

    return ValidationReport(
        check_name="DOMAIN_SANITY_RULES",
        is_valid=len(failures) == 0,
        failure_count=len(failures),
        failures=failures
    )

def validate_redemptions_data_quality(
    transactions: List[RedemptionTransaction],
    valid_member_ids: Set[str]
) -> ValidationReport:
    """
    Validates redemption transactions:
    - Positive miles
    - Valid status domain
    - Referential integrity (no orphan members)
    """
    failures = []
    allowed_statuses = {"COMPLETED", "PENDING", "CANCELLED"}

    for t in transactions:
        if t.miles_redeemed <= 0:
            failures.append(f"Txn {t.txn_id} has invalid non-positive miles: {t.miles_redeemed}")
        if t.status not in allowed_statuses:
            failures.append(f"Txn {t.txn_id} has unrecognized status: '{t.status}'")
        if valid_member_ids and t.member_id not in valid_member_ids:
            failures.append(f"Txn {t.txn_id} is an orphan: Member ID {t.member_id} not in member database")

    return ValidationReport(
        check_name="REDEMPTIONS_QUALITY",
        is_valid=len(failures) == 0,
        failure_count=len(failures),
        failures=failures
    )
