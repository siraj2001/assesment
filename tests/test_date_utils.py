import pytest
from datetime import date, datetime
from skypoints.processing.date_utils import parse_flexible_date, calculate_age, is_stale_member

def test_parse_standard_yyyymmdd():
    assert parse_flexible_date("20101012") == date(2010, 10, 12)
    assert parse_flexible_date("20240115") == date(2024, 1, 15)

def test_parse_standard_mmddyyyy():
    assert parse_flexible_date("03051985") == date(1985, 3, 5)

def test_parse_unpadded_seven_digit_date():
    # E.g., '3051985' losing leading zero for March 5, 1985
    assert parse_flexible_date("3051985") == date(1985, 3, 5)
    # E.g., '6152022' from USA.csv
    assert parse_flexible_date("6152022") == date(2022, 6, 15)

def test_parse_slash_dates():
    # E.g., from IND.csv '12/1/1998', '1/1/2022', '6/15/2022'
    assert parse_flexible_date("12/1/1998") == date(1998, 12, 1)
    assert parse_flexible_date("1/1/2022") == date(2022, 1, 1)
    assert parse_flexible_date("6/15/2022") == date(2022, 6, 15)

def test_parse_datetime_object():
    dt = datetime(1997, 12, 13, 0, 0)
    assert parse_flexible_date(dt) == date(1997, 12, 13)

def test_parse_null_and_empty_strings():
    assert parse_flexible_date(None) is None
    assert parse_flexible_date("") is None
    assert parse_flexible_date("   ") is None
    assert parse_flexible_date("NULL") is None
    assert parse_flexible_date("null") is None
    assert parse_flexible_date("N/A") is None

def test_parse_invalid_date_raises():
    # '2021-13-13' from AUS.xlsx has month 13
    with pytest.raises(ValueError):
        parse_flexible_date("2021-13-13", raise_on_error=True)
    assert parse_flexible_date("2021-13-13", raise_on_error=False) is None

def test_calculate_age():
    ref_date = date(2024, 1, 15)
    # Born March 5, 1985 -> birthday not yet reached in Jan 2024 -> age is 38
    assert calculate_age(date(1985, 3, 5), ref_date) == 38
    # Born Jan 10, 1985 -> birthday already reached in Jan 2024 -> age is 39
    assert calculate_age(date(1985, 1, 10), ref_date) == 39
    # None DOB
    assert calculate_age(None, ref_date) is None

def test_is_stale_member():
    ref_date = date(2024, 1, 15)
    # Flight on 2024-01-10 -> 5 days ago (<= 90) -> NOT stale
    assert is_stale_member(date(2024, 1, 10), ref_date, threshold_days=90) == "N"
    # Flight on 2012-10-13 -> > 90 days ago -> STALE
    assert is_stale_member(date(2012, 10, 13), ref_date, threshold_days=90) == "Y"
    # Never flown (None) -> STALE
    assert is_stale_member(None, ref_date, threshold_days=90) == "Y"
