import csv
from pathlib import Path
from typing import List, Union
import openpyxl
from skypoints.models import RawMemberRecord

def read_legacy_usa_csv(file_path: Union[str, Path]) -> List[RawMemberRecord]:
    """
    Parses USA.csv:
    Columns: ID,Name,TierCode,EnrollmentDate,FlightDate
    Example row: 1,Sam,PLT,6152022,8202022
    """
    path = Path(file_path)
    records: List[RawMemberRecord] = []

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            records.append(RawMemberRecord(
                member_id=row.get("ID"),
                member_name=row.get("Name"),
                tier_code=row.get("TierCode"),
                enrollment_date_raw=row.get("EnrollmentDate"),
                last_flight_date_raw=row.get("FlightDate"),
                country="USA",
                source_file=path.name,
                row_num=idx,
                raw_line=str(row)
            ))
    return records

def read_legacy_ind_csv(file_path: Union[str, Path]) -> List[RawMemberRecord]:
    """
    Parses IND.csv:
    Columns: ID,Name,DOB,TierCode,EnrollmentDate,Individual or Corporate,Flight Date
    Example row: 1,Vikas,12/1/1998,SLV,1/1/2022,I,6/15/2022
    """
    path = Path(file_path)
    records: List[RawMemberRecord] = []

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            records.append(RawMemberRecord(
                member_id=row.get("ID"),
                member_name=row.get("Name"),
                dob_raw=row.get("DOB"),
                tier_code=row.get("TierCode"),
                enrollment_date_raw=row.get("EnrollmentDate"),
                last_flight_date_raw=row.get("Flight Date") or row.get("FlightDate"),
                country="IND",
                source_file=path.name,
                row_num=idx,
                raw_line=str(row)
            ))
    return records

def read_legacy_aus_xlsx(file_path: Union[str, Path]) -> List[RawMemberRecord]:
    """
    Parses AUS.xlsx:
    Columns: Unique ID, Member Name, Tier Type, Date of Birth, Date of Enrollment, Date of Flight
    Example row: 1, 'Mike', 'PLT', 'NULL', datetime(2022, 5, 11), datetime(2022, 8, 1)
    """
    path = Path(file_path)
    records: List[RawMemberRecord] = []
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return records

    header = [str(c).strip().lower() for c in rows[0]]
    # Map column headers to positions
    col_map = {name: idx for idx, name in enumerate(header)}

    id_col = col_map.get("unique id", col_map.get("id", 0))
    name_col = col_map.get("member name", col_map.get("name", 1))
    tier_col = col_map.get("tier type", col_map.get("tiercode", 2))
    dob_col = col_map.get("date of birth", col_map.get("dob", 3))
    enroll_col = col_map.get("date of enrollment", col_map.get("enrollmentdate", 4))
    flight_col = col_map.get("date of flight", col_map.get("flightdate", 5))

    for idx, row in enumerate(rows[1:], start=2):
        if not any(row):
            continue

        raw_id = row[id_col] if id_col < len(row) else None
        raw_name = row[name_col] if name_col < len(row) else None
        raw_tier = row[tier_col] if tier_col < len(row) else None
        raw_dob = row[dob_col] if dob_col < len(row) else None
        raw_enroll = row[enroll_col] if enroll_col < len(row) else None
        raw_flight = row[flight_col] if flight_col < len(row) else None

        records.append(RawMemberRecord(
            member_id=str(raw_id) if raw_id is not None else None,
            member_name=str(raw_name) if raw_name is not None else None,
            tier_code=str(raw_tier) if raw_tier is not None else None,
            dob_raw=str(raw_dob) if raw_dob is not None else None,
            enrollment_date_raw=str(raw_enroll) if raw_enroll is not None else None,
            last_flight_date_raw=str(raw_flight) if raw_flight is not None else None,
            country="AUS",
            source_file=path.name,
            row_num=idx,
            raw_line=str(row)
        ))

    return records
