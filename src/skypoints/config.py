from pathlib import Path
from datetime import date

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
QUARANTINE_DATA_DIR = DATA_DIR / "quarantine"

# Default parameters
DEFAULT_REFERENCE_DATE = date(2024, 1, 15)  # Matches sample feed date
STALE_DAYS_THRESHOLD = 90

# Standard country codes mapping
COUNTRY_NORMALIZE_MAP = {
    "USA": "USA",
    "US": "USA",
    "UNITED STATES": "USA",
    "IND": "IND",
    "INDIA": "IND",
    "AU": "AUS",
    "AUS": "AUS",
    "AUSTRALIA": "AUS",
    "CAN": "CAN",
    "CANADA": "CAN",
    "PHIL": "PHIL",
    "PHL": "PHIL",
    "PHILIPPINES": "PHIL"
}

# Supported country target tables
SUPPORTED_COUNTRY_TABLES = ["TABLE_USA", "TABLE_IND", "TABLE_AUS", "TABLE_CAN", "TABLE_PHIL"]
