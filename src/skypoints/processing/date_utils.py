from datetime import date, datetime
from typing import Optional, Union, Any

def parse_flexible_date(
    val: Any,
    default_format_hint: Optional[str] = None,
    raise_on_error: bool = False
) -> Optional[date]:
    """
    Parses dates across heterogeneous inputs, handling:
    - Standard YYYYMMDD and MMDDYYYY strings
    - Unpadded 7-digit strings losing leading zero (e.g., '3051985' -> '03051985')
    - Slash formats (M/D/YYYY, MM/DD/YYYY)
    - ISO strings (YYYY-MM-DD)
    - datetime/date objects
    - String literals representing nulls ('NULL', 'N/A', '')
    """
    if val is None:
        return None

    if isinstance(val, date):
        if isinstance(val, datetime):
            return val.date()
        return val

    s = str(val).strip()
    if not s or s.upper() in ("NULL", "NONE", "N/A", "NA", "NAN", ""):
        return None

    # Handle unpadded 7-digit integers (e.g. 3051985 or 6152022)
    if s.isdigit() and len(s) == 7:
        s = "0" + s

    formats_to_try = [
        "%Y%m%d",       # 20101012
        "%m%d%Y",       # 03051985
        "%d%m%Y",       # 05031985
        "%Y-%m-%d",     # 2021-12-13
        "%m/%d/%Y",     # 12/1/1998, 6/15/2022
        "%d/%m/%Y",     # 1/12/1998
        "%Y/%m/%d",     # 1998/12/01
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats_to_try:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    if raise_on_error:
        raise ValueError(f"Unable to parse date string: '{s}'")
    return None

def calculate_age(dob: Optional[date], reference_date: Optional[date] = None) -> Optional[int]:
    """
    Calculates exact age in years from DOB to reference_date (defaults to today).
    Accurately accounts for leap years and whether the birthday has occurred yet in reference year.
    """
    if dob is None:
        return None
    ref = reference_date or date.today()
    if dob > ref:
        return 0
    return ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))

def is_stale_member(
    last_flight_date: Optional[date],
    reference_date: Optional[date] = None,
    threshold_days: int = 90
) -> str:
    """
    Returns 'Y' if days since last_flight_date > threshold_days (default 90)
    or if member has never flown (last_flight_date is None). Otherwise returns 'N'.
    """
    if last_flight_date is None:
        return "Y"
    ref = reference_date or date.today()
    delta = (ref - last_flight_date).days
    return "Y" if delta > threshold_days else "N"
