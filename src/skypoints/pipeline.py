import os
import duckdb
import pandas as pd
from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Any, Optional

from skypoints.config import (
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    QUARANTINE_DATA_DIR,
    DEFAULT_REFERENCE_DATE
)
from skypoints.models import (
    RawMemberRecord,
    StagedMemberRecord,
    TargetMemberRecord,
    RedemptionTransaction,
    QuarantineRecord
)
from skypoints.ingestion.flat_file_reader import read_pipe_delimited_flat_file
from skypoints.ingestion.json_reader import read_json_redemption_file
from skypoints.processing.staging import stage_raw_records
from skypoints.processing.deduplication import deduplicate_latest_records_wins
from skypoints.processing.country_router import route_members_to_country_tables
from skypoints.processing.redemptions import (
    flatten_json_redemptions,
    aggregate_member_redemptions,
    enrich_member_profiles_with_redemptions
)
from skypoints.validation.validator import (
    validate_mandatory_fields,
    validate_key_uniqueness,
    validate_domain_rules,
    validate_redemptions_data_quality,
    ValidationReport
)

class SkyPointsPipeline:
    """
    End-to-End SkyPoints Airline Loyalty Data Pipeline.
    Orchestrates Ingestion -> Validation & Quarantine -> Staging -> Deduplication ->
    Country Splitting -> JSON Flattening -> Aggregation Join -> DuckDB/Parquet Storage.
    """

    def __init__(
        self,
        reference_date: Optional[date] = None,
        db_path: Optional[Path] = None,
        batch_id: Optional[str] = None
    ):
        self.reference_date = reference_date or DEFAULT_REFERENCE_DATE
        self.batch_id = batch_id or f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.db_path = db_path or (PROCESSED_DATA_DIR / "skypoints.duckdb")

        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        QUARANTINE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        member_file: Optional[Path] = None,
        json_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Executes the full pipeline workflow.
        """
        mem_path = member_file or (RAW_DATA_DIR / "skypoints_members_with_anomalies.dat")
        json_path = json_file or (RAW_DATA_DIR / "redemptions_sample.json")

        # 1. Ingestion
        raw_records = read_pipe_delimited_flat_file(mem_path)
        raw_json_data = read_json_redemption_file(json_path)

        # 2. Staging & Quarantine
        staged_records, quarantine_records = stage_raw_records(
            raw_records,
            reference_date=self.reference_date,
            batch_id=self.batch_id
        )

        # 3. Deduplication ("Latest Record Wins")
        deduped_records = deduplicate_latest_records_wins(staged_records)

        # 4. Country Target Splitting
        country_tables = route_members_to_country_tables(deduped_records)

        # 5. JSON Redemptions Flattening & Aggregation
        redemption_txns = flatten_json_redemptions(raw_json_data, batch_id=self.batch_id)
        redemption_summaries = aggregate_member_redemptions(redemption_txns)

        # 6. Analytical Enrichment (Member 360 View - 1-to-1 join)
        enriched_members = enrich_member_profiles_with_redemptions(
            deduped_records,
            redemption_summaries
        )

        # 7. Data Quality Validations
        valid_member_ids = {m.member_id for m in deduped_records}
        val_mandatory = validate_mandatory_fields(staged_records)
        val_uniqueness = validate_key_uniqueness(deduped_records)
        val_domain = validate_domain_rules(staged_records)
        val_redemptions = validate_redemptions_data_quality(redemption_txns, valid_member_ids)

        validation_reports = [val_mandatory, val_uniqueness, val_domain, val_redemptions]

        # 8. Persist to DuckDB and Parquet
        self._persist_to_duckdb(
            staged_records=staged_records,
            quarantine_records=quarantine_records,
            country_tables=country_tables,
            redemption_txns=redemption_txns,
            enriched_members=enriched_members
        )

        return {
            "batch_id": self.batch_id,
            "reference_date": self.reference_date.isoformat(),
            "raw_records_count": len(raw_records),
            "staged_records_count": len(staged_records),
            "quarantined_records_count": len(quarantine_records),
            "deduped_records_count": len(deduped_records),
            "country_tables": {tbl: len(recs) for tbl, recs in country_tables.items()},
            "redemption_txns_count": len(redemption_txns),
            "enriched_members_count": len(enriched_members),
            "validations": {
                r.check_name: {"is_valid": r.is_valid, "failures": r.failures}
                for r in validation_reports
            }
        }

    def _persist_to_duckdb(
        self,
        staged_records: List[StagedMemberRecord],
        quarantine_records: List[QuarantineRecord],
        country_tables: Dict[str, List[TargetMemberRecord]],
        redemption_txns: List[RedemptionTransaction],
        enriched_members: List[Dict[str, Any]]
    ):
        """
        Saves all tables into local DuckDB and exports Parquet files.
        """
        con = duckdb.connect(str(self.db_path))

        # Staging table
        if staged_records:
            df_stg = pd.DataFrame([vars(r) for r in staged_records])
            con.execute("CREATE OR REPLACE TABLE STG_MEMBER_PROFILES AS SELECT * FROM df_stg")
            stg_p = str(PROCESSED_DATA_DIR / "stg_member_profiles.parquet").replace("\\", "/")
            con.execute(f"COPY STG_MEMBER_PROFILES TO '{stg_p}' (FORMAT PARQUET)")

        # Quarantine table
        if quarantine_records:
            df_quar = pd.DataFrame([vars(r) for r in quarantine_records])
            con.execute("CREATE OR REPLACE TABLE QUARANTINE_REJECTED_RECORDS AS SELECT * FROM df_quar")
            df_quar.to_csv(QUARANTINE_DATA_DIR / "rejected_records.csv", index=False)

        # Country tables
        for tbl_name, recs in country_tables.items():
            if recs:
                df_country = pd.DataFrame([vars(r) for r in recs])
                con.execute(f"CREATE OR REPLACE TABLE {tbl_name} AS SELECT * FROM df_country")
                c_p = str(PROCESSED_DATA_DIR / f"{tbl_name.lower()}.parquet").replace("\\", "/")
                con.execute(f"COPY {tbl_name} TO '{c_p}' (FORMAT PARQUET)")

        # Flattened Redemptions
        if redemption_txns:
            df_redemptions = pd.DataFrame([vars(r) for r in redemption_txns])
            con.execute("CREATE OR REPLACE TABLE FCT_MILEAGE_REDEMPTIONS AS SELECT * FROM df_redemptions")
            red_p = str(PROCESSED_DATA_DIR / "fct_mileage_redemptions.parquet").replace("\\", "/")
            con.execute(f"COPY FCT_MILEAGE_REDEMPTIONS TO '{red_p}' (FORMAT PARQUET)")

        # Member 360 Enriched View
        if enriched_members:
            df_enriched = pd.DataFrame(enriched_members)
            con.execute("CREATE OR REPLACE TABLE V_MEMBER_360 AS SELECT * FROM df_enriched")
            m360_p = str(PROCESSED_DATA_DIR / "member_360_enriched.parquet").replace("\\", "/")
            con.execute(f"COPY V_MEMBER_360 TO '{m360_p}' (FORMAT PARQUET)")

        con.close()
