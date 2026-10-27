import os
import duckdb
import pytest
from pathlib import Path
from datetime import date
from typing import Dict, Any, List
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from skypoints.pipeline import SkyPointsPipeline
from skypoints.config import BASE_DIR, RAW_DATA_DIR, PROCESSED_DATA_DIR

app = FastAPI(title="SkyPoints Loyalty Data Platform - Live Interview Demo")

db_path = PROCESSED_DATA_DIR / "skypoints.duckdb"

@app.get("/api/run-pipeline")
def trigger_pipeline(source: str = "anomalies"):
    """
    Triggers the end-to-end pipeline.
    source: 'anomalies' (test dataset with migrations & errors) or 'sample' (PDF clean sample)
    """
    if source == "sample":
        mem_file = RAW_DATA_DIR / "skypoints_members_sample.dat"
    else:
        mem_file = RAW_DATA_DIR / "skypoints_members_with_anomalies.dat"

    json_file = RAW_DATA_DIR / "redemptions_sample.json"

    pipeline = SkyPointsPipeline(reference_date=date(2024, 1, 15))
    result = pipeline.run(member_file=mem_file, json_file=json_file)
    return result

@app.get("/api/table-data")
def get_table_data(table: str = Query(..., description="Table name"), limit: int = 50):
    if not db_path.exists():
        # Auto-run pipeline if not yet generated
        pipeline = SkyPointsPipeline(reference_date=date(2024, 1, 15))
        pipeline.run()

    con = duckdb.connect(str(db_path))
    try:
        # Check if table exists
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        if table not in tables:
            return {"columns": [], "rows": [], "error": f"Table '{table}' does not exist"}

        df = con.execute(f"SELECT * FROM {table} LIMIT {limit}").fetchdf()
        # Convert timestamps/dates to strings for JSON serialization
        for col in df.columns:
            if "date" in col.lower() or "timestamp" in col.lower() or "dob" in col.lower():
                df[col] = df[col].astype(str)
        return {
            "columns": list(df.columns),
            "rows": df.to_dict(orient="records"),
            "total_rows": len(df)
        }
    except Exception as e:
        return {"error": str(e), "columns": [], "rows": []}
    finally:
        con.close()

@app.get("/api/query")
def execute_custom_sql(sql: str = Query(..., description="Custom SQL query")):
    if not db_path.exists():
        pipeline = SkyPointsPipeline(reference_date=date(2024, 1, 15))
        pipeline.run()

    # Safety check: Read only
    clean_sql = sql.strip().upper()
    if not clean_sql.startswith("SELECT") and not clean_sql.startswith("WITH") and not clean_sql.startswith("SHOW"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are permitted in demo runner")

    con = duckdb.connect(str(db_path))
    try:
        df = con.execute(sql).fetchdf()
        for col in df.columns:
            if "date" in col.lower() or "timestamp" in col.lower() or "dob" in col.lower():
                df[col] = df[col].astype(str)
        return {
            "columns": list(df.columns),
            "rows": df.to_dict(orient="records"),
            "row_count": len(df)
        }
    except Exception as e:
        return {"error": str(e), "columns": [], "rows": []}
    finally:
        con.close()

@app.get("/api/run-tests")
def run_tests():
    """Runs pytest and returns test counts and pass status"""
    import io
    import sys
    from contextlib import redirect_stdout, redirect_stderr

    f = io.StringIO()
    # Run pytest programmatically
    code = pytest.main(["-v", str(BASE_DIR / "tests")], stdout=f)
    output = f.getvalue()
    return {
        "exit_code": int(code),
        "status": "PASS" if code == 0 else "FAIL",
        "output": output
    }

@app.get("/", response_class=HTMLResponse)
def index():
    html_file = Path(__file__).parent / "index.html"
    return html_file.read_text(encoding="utf-8")

if __name__ == "__main__":
    uvicorn.run("demo.server:app", host="127.0.0.1", port=8000, reload=True)
