import hashlib
from datetime import date, datetime
from typing import List, Tuple, Optional
from skypoints.models import RawMemberRecord, StagedMemberRecord, QuarantineRecord
from skypoints.config import COUNTRY_NORMALIZE_MAP, STALE_DAYS_THRESHOLD
from skypoints.processing.date_utils import parse_flexible_date, calculate_age, is_stale_member

def stage_raw_records(
    records: List[RawMemberRecord],
    reference_date: Optional[date] = None,
    batch_id: str = "DEFAULT"
) -> Tuple[List[StagedMemberRecord], List[QuarantineRecord]]:
    """
    Transforms raw member records into validated, staged silver records.
    Enriches with:
    - Age (computed from DOB)
    - Stale_Member flag (days since Flight_Date > 90 or never flown)
    - Hash of attributes for change data capture
    Routes malformed rows to Quarantine (Dead-Letter Queue).
    """
    ref_date = reference_date or date.today()
    staged: List[StagedMemberRecord] = []
    quarantine: List[QuarantineRecord] = []

    for raw in records:
        # Mandatory Field Check 1: Member Name
        name = (raw.member_name or "").strip()
        if not name:
            quarantine.append(QuarantineRecord(
                batch_id=batch_id,
                source_file=raw.source_file,
                source_row=raw.row_num,
                raw_payload=raw.raw_line or str(raw),
                error_code="ERR_MANDATORY_NAME_MISSING",
                error_message="Member Name is mandatory but was empty or missing.",
                failed_field="MEMBER_NAME"
            ))
            continue

        # Mandatory Field Check 2: Member ID
        mem_id = (raw.member_id or "").strip()
        if not mem_id:
            quarantine.append(QuarantineRecord(
                batch_id=batch_id,
                source_file=raw.source_file,
                source_row=raw.row_num,
                raw_payload=raw.raw_line or str(raw),
                error_code="ERR_MANDATORY_ID_MISSING",
                error_message="Member ID is mandatory but was empty or missing.",
                failed_field="MEMBER_ID"
            ))
            continue

        # Mandatory Field Check 3: Enrollment Date
        enroll_raw = (raw.enrollment_date_raw or "").strip()
        if not enroll_raw:
            quarantine.append(QuarantineRecord(
                batch_id=batch_id,
                source_file=raw.source_file,
                source_row=raw.row_num,
                raw_payload=raw.raw_line or str(raw),
                error_code="ERR_MANDATORY_ENROLL_DATE_MISSING",
                error_message="Enrollment Date is mandatory but was missing.",
                failed_field="ENROLLMENT_DATE"
            ))
            continue

        # Parse Enrollment Date
        try:
            enroll_date = parse_flexible_date(enroll_raw, raise_on_error=True)
            if enroll_date is None:
                raise ValueError("Parsed to None")
        except Exception as e:
            quarantine.append(QuarantineRecord(
                batch_id=batch_id,
                source_file=raw.source_file,
                source_row=raw.row_num,
                raw_payload=raw.raw_line or str(raw),
                error_code="ERR_INVALID_DATE",
                error_message=f"Invalid Enrollment Date '{enroll_raw}': {e}",
                failed_field="ENROLLMENT_DATE"
            ))
            continue

        # Parse Flight Date
        last_flight_date: Optional[date] = None
        if raw.last_flight_date_raw:
            try:
                last_flight_date = parse_flexible_date(raw.last_flight_date_raw, raise_on_error=True)
            except Exception as e:
                quarantine.append(QuarantineRecord(
                    batch_id=batch_id,
                    source_file=raw.source_file,
                    source_row=raw.row_num,
                    raw_payload=raw.raw_line or str(raw),
                    error_code="ERR_INVALID_DATE",
                    error_message=f"Invalid Flight Date '{raw.last_flight_date_raw}': {e}",
                    failed_field="LAST_FLIGHT_DATE"
                ))
                continue

        # Parse DOB
        dob: Optional[date] = None
        if raw.dob_raw:
            try:
                dob = parse_flexible_date(raw.dob_raw, raise_on_error=False)
            except Exception:
                dob = None

        # Parse Post Code
        post_code: Optional[int] = None
        if raw.post_code_raw:
            try:
                post_code = int(str(raw.post_code_raw).strip())
            except (ValueError, TypeError):
                post_code = None

        # Normalize Country
        country_norm = None
        if raw.country:
            c_clean = raw.country.strip().upper()
            country_norm = COUNTRY_NORMALIZE_MAP.get(c_clean, c_clean)

        # Derived Column 1: Age computed from DOB
        age = calculate_age(dob, ref_date)

        # Derived Column 2: Stale_Member flag where days since Flight_Date > 90
        stale_flag = is_stale_member(last_flight_date, ref_date, threshold_days=STALE_DAYS_THRESHOLD)

        # Record hash for CDC
        hash_str = f"{name}|{mem_id}|{enroll_date}|{last_flight_date}|{country_norm}"
        record_hash = hashlib.sha256(hash_str.encode("utf-8")).hexdigest()

        staged.append(StagedMemberRecord(
            member_name=name,
            member_id=mem_id,
            enrollment_date=enroll_date,
            last_flight_date=last_flight_date,
            tier_code=(raw.tier_code or "").strip() or None,
            agent_name=(raw.agent_name or "").strip() or None,
            state=(raw.state or "").strip() or None,
            country=country_norm,
            post_code=post_code,
            dob=dob,
            is_active=(raw.is_active or "A").strip(),
            age=age,
            stale_member=stale_flag,
            batch_id=batch_id,
            source_file=raw.source_file,
            record_hash=record_hash
        ))

    return staged, quarantine
