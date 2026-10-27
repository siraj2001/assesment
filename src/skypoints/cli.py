import sys
import argparse
from datetime import date
from pathlib import Path
import duckdb
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from skypoints.pipeline import SkyPointsPipeline
from skypoints.config import RAW_DATA_DIR, PROCESSED_DATA_DIR

console = Console()

def run_pipeline_command(args):
    console.print(Panel.fit("[bold cyan]SkyPoints Airline Loyalty Data Pipeline[/bold cyan]\n[dim]Incubyte Data Craftsperson Assessment Engine[/dim]", border_style="cyan"))

    pipeline = SkyPointsPipeline(reference_date=date(2024, 1, 15))
    
    with console.status("[bold green]Executing end-to-end data pipeline...[/bold green]"):
        result = pipeline.run()

    # Pipeline Summary Table
    summary_table = Table(title="Batch Execution Summary", box=box.ROUNDED, header_style="bold magenta")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Batch ID", result["batch_id"])
    summary_table.add_row("Reference Date", result["reference_date"])
    summary_table.add_row("Raw Records Ingested", str(result["raw_records_count"]))
    summary_table.add_row("Staged Records (Silver)", str(result["staged_records_count"]))
    summary_table.add_row("Quarantined Bad Records (DLQ)", f"[bold red]{result['quarantined_records_count']}[/bold red]")
    summary_table.add_row("Deduplicated Active Members", str(result["deduped_records_count"]))
    summary_table.add_row("Flattened Redemptions (Fact)", str(result["redemption_txns_count"]))
    summary_table.add_row("Enriched Members (360 View)", str(result["enriched_members_count"]))
    console.print(summary_table)

    # Country Routing Breakdown
    country_table = Table(title="Target Country Marts Distribution", box=box.ROUNDED, header_style="bold blue")
    country_table.add_column("Country Table", style="yellow")
    country_table.add_column("Member Count", style="green")
    for tbl, count in sorted(result["country_tables"].items()):
        country_table.add_row(tbl, str(count))
    console.print(country_table)

    # Validation Checks
    val_table = Table(title="Data Quality & Integrity Validations", box=box.ROUNDED, header_style="bold yellow")
    val_table.add_column("Check Suite", style="cyan")
    val_table.add_column("Status", style="bold")
    val_table.add_column("Failures Detected", style="white")

    for check_name, info in result["validations"].items():
        status_str = "[bold green]PASS[/bold green]" if info["is_valid"] else "[bold red]FAIL[/bold red]"
        fails_str = ", ".join(info["failures"]) if info["failures"] else "0 failures"
        val_table.add_row(check_name, status_str, fails_str)
    console.print(val_table)

def inspect_table_command(args):
    db_file = PROCESSED_DATA_DIR / "skypoints.duckdb"
    if not db_file.exists():
        console.print("[red]Database not found. Please run 'python -m skypoints.cli run' first.[/red]")
        return

    con = duckdb.connect(str(db_file))
    try:
        df = con.execute(f"SELECT * FROM {args.table} LIMIT {args.limit}").fetchdf()
        # Keep prominent columns if wide
        if len(df.columns) > 8:
            priority_cols = ["member_id", "member_name", "country", "tier_code", "age", "stale_member", "last_flight_date", "enrollment_date"]
            display_cols = [c for c in priority_cols if c in df.columns]
            if not display_cols:
                display_cols = list(df.columns[:8])
            df_disp = df[display_cols]
        else:
            df_disp = df

        table = Table(title=f"Records from {args.table} ({len(df)} rows)", box=box.ROUNDED)
        for col in df_disp.columns:
            table.add_column(str(col), style="cyan")
        for _, row in df_disp.iterrows():
            table.add_row(*[str(val) for val in row])
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error querying {args.table}: {e}[/bold red]")
    finally:
        con.close()

def main():
    parser = argparse.ArgumentParser(description="SkyPoints Data Craftsperson CLI")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run end-to-end pipeline")
    
    inspect_parser = subparsers.add_parser("inspect", help="Inspect a processed table")
    inspect_parser.add_argument("--table", required=True, help="Table name (e.g., STG_MEMBER_PROFILES, TABLE_CAN, V_MEMBER_360)")
    inspect_parser.add_argument("--limit", type=int, default=10, help="Row limit")

    args = parser.parse_args()
    if args.command == "run" or len(sys.argv) == 1:
        run_pipeline_command(args)
    elif args.command == "inspect":
        inspect_table_command(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
