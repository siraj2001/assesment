import os
from pathlib import Path
from typing import List, Union
from skypoints.models import RawMemberRecord

def read_pipe_delimited_flat_file(file_path: Union[str, Path]) -> List[RawMemberRecord]:
    """
    Reads daily standard flat file according to the SkyPoints specification:
    Header: |H|Member_Name|Member_Id|Enrollment_Date|Last_Flight_Date|Tier_Code|Agent_Name|State|Country|DOB|Is_Active
    Detail: |D|Elena|223457|20101012|20121013|GLD|Sam|CA|USA|03051985|A
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    records: List[RawMemberRecord] = []

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for row_idx, line in enumerate(f, start=1):
            line_str = line.strip()
            if not line_str:
                continue

            parts = [p.strip() for p in line_str.split("|")]
            # Filter empty boundary elements from leading/trailing pipes
            if parts and parts[0] == "":
                parts = parts[1:]
            if parts and parts[-1] == "":
                parts = parts[:-1]

            if not parts:
                continue

            record_type = parts[0].upper()
            if record_type == "H":
                # Header record, skip
                continue

            if record_type == "D":
                # Detail record: unpack by position based on spec
                # |D|Member_Name|Member_Id|Enrollment_Date|Last_Flight_Date|Tier_Code|Agent_Name|State|Country|DOB|Is_Active
                member_name = parts[1] if len(parts) > 1 else None
                member_id = parts[2] if len(parts) > 2 else None
                enroll_dt = parts[3] if len(parts) > 3 else None
                flight_dt = parts[4] if len(parts) > 4 else None
                tier_code = parts[5] if len(parts) > 5 else None
                agent_name = parts[6] if len(parts) > 6 else None
                state = parts[7] if len(parts) > 7 else None
                country = parts[8] if len(parts) > 8 else None
                dob_or_post = parts[9] if len(parts) > 9 else None
                is_active = parts[10] if len(parts) > 10 else "A"

                records.append(RawMemberRecord(
                    member_name=member_name,
                    member_id=member_id,
                    enrollment_date_raw=enroll_dt,
                    last_flight_date_raw=flight_dt,
                    tier_code=tier_code,
                    agent_name=agent_name,
                    state=state,
                    country=country,
                    post_code_raw=None,
                    dob_raw=dob_or_post,
                    is_active=is_active,
                    source_file=path.name,
                    row_num=row_idx,
                    raw_line=line_str
                ))

    return records
