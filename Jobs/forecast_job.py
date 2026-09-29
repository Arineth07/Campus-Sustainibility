"""
Campus Sustainability Dashboard - Prophet Forecasting Scheduled Job
====================================================================
Orchestrates the 48-hour Prophet forecasting pipeline:
1. Connects to Supabase Postgres.
2. Validates sensor-to-facility mappings.
3. Retrieves the most recent 30 days of telemetry from sensor_readings_fact.
4. Prepares the time series and invokes the ML runtime (train_and_forecast).
5. Writes the generated predictions and uncertainty bounds back to the forecasts table.
6. Runs an immediate verification query to ensure database integrity.

Architecture:
  Supabase read -> Jobs (prepare df) -> ML forecast_service -> Jobs -> Supabase write
"""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from dotenv import load_dotenv
from supabase import Client, create_client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("forecast_job")

# Resolve project root and load environment variables
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import pure ML forecasting runtime
from ML.forecasting.forecast_service import SENSOR_CONFIGS, train_and_forecast

# Load .env
env_paths = [SCRIPT_DIR / ".env", PROJECT_ROOT / ".env"]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break
else:
    load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = (
    os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
)


def init_supabase() -> Client:
    """Initialize and return the Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError(
            "Missing SUPABASE_URL or SUPABASE_KEY in environment. "
            "Please configure credentials in .env file."
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def validate_sensor_facility_mappings(supabase: Client) -> None:
    """
    Validate that configured facility_id matches sensors_dim in Supabase
    before proceeding with forecasts.
    """
    logger.info("Validating configured sensor -> facility mappings against sensors_dim...")
    for config in SENSOR_CONFIGS:
        s_id = config["sensor_id"]
        cfg_fac = config["facility_id"]
        res = supabase.table("sensors_dim").select("facility_id").eq("sensor_id", s_id).limit(1).execute()
        if not res.data:
            raise ValueError(f"Sensor {s_id} not found in sensors_dim table!")
        db_fac = res.data[0]["facility_id"]
        if cfg_fac != db_fac:
            raise ValueError(
                f"Facility ID mismatch for {s_id}: configured '{cfg_fac}' != database '{db_fac}'"
            )
    logger.info("All configured sensor -> facility mappings verified against sensors_dim.")


def fetch_sensor_data(supabase: Client, sensor_id: str) -> pd.DataFrame:
    """
    Pull exactly the most recent 30 days of readings based on the sensor's
    latest available recorded_at timestamp in Supabase.
    """
    logger.info(f"Determining latest timestamp for {sensor_id} from Supabase...")

    latest_res = (
        supabase.table("sensor_readings_fact")
        .select("recorded_at")
        .eq("sensor_id", sensor_id)
        .order("recorded_at", desc=True)
        .limit(1)
        .execute()
    )
    if not latest_res.data:
        raise ValueError(f"No readings found for sensor_id: {sensor_id}")

    latest_recorded_at = pd.to_datetime(latest_res.data[0]["recorded_at"])
    start_recorded_at = latest_recorded_at - pd.Timedelta(days=30)

    start_iso = start_recorded_at.isoformat()
    latest_iso = latest_recorded_at.isoformat()

    logger.info(f"Retrieving 30-day window for {sensor_id}: [{start_iso} to {latest_iso}]")

    page_size = 1000
    offset = 0
    all_rows: List[Dict[str, Any]] = []

    while True:
        res = (
            supabase.table("sensor_readings_fact")
            .select("recorded_at, reading_value")
            .eq("sensor_id", sensor_id)
            .gte("recorded_at", start_iso)
            .lte("recorded_at", latest_iso)
            .order("recorded_at", desc=False)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        data = res.data or []
        all_rows.extend(data)
        if len(data) < page_size:
            break
        offset += page_size

    if not all_rows:
        raise ValueError(f"No readings found in 30-day window for sensor_id: {sensor_id}")

    df = pd.DataFrame(all_rows)

    # Convert recorded_at to datetime in IST (Asia/Kolkata)
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    if df["recorded_at"].dt.tz is not None:
        df["recorded_at"] = df["recorded_at"].dt.tz_convert("Asia/Kolkata")
    else:
        df["recorded_at"] = df["recorded_at"].dt.tz_localize("Asia/Kolkata")

    df = df.sort_values("recorded_at").reset_index(drop=True)

    min_ts = df["recorded_at"].min()
    max_ts = df["recorded_at"].max()
    actual_span_days = (max_ts - min_ts).total_seconds() / 86400.0

    if actual_span_days < 29.0:
        logger.warning(
            f"Sensor {sensor_id} has only {actual_span_days:.2f} days of data (< 30 days). "
            f"Proceeding with available historical data."
        )

    print(
        f"Retrieved {len(df)} rows for {sensor_id} "
        f"(Historical Start: {min_ts.strftime('%Y-%m-%d %H:%M:%S IST')}, "
        f"Historical End: {max_ts.strftime('%Y-%m-%d %H:%M:%S IST')})"
    )
    return df


def insert_forecasts(
    supabase: Client,
    forecast_df: pd.DataFrame,
    sensor_id: str,
    facility_id: str,
) -> None:
    """
    Attach sensor_id and facility_id, format ISO timestamps, delete existing
    forecast rows for this sensor, and insert new forecast records in batches.
    """
    df_to_insert = forecast_df.copy()
    df_to_insert["sensor_id"] = sensor_id
    df_to_insert["facility_id"] = facility_id

    logger.info(f"Removing existing forecast rows for {sensor_id} in Supabase...")
    supabase.table("forecasts").delete().eq("sensor_id", sensor_id).execute()

    # Convert forecast_horizon_at to ISO string with IST offset
    horizon_dt = pd.to_datetime(df_to_insert["forecast_horizon_at"])
    if horizon_dt.dt.tz is None:
        ist_series = horizon_dt.dt.tz_localize("Asia/Kolkata")
    else:
        ist_series = horizon_dt.dt.tz_convert("Asia/Kolkata")

    df_to_insert["forecast_horizon_at"] = ist_series.apply(lambda dt: dt.isoformat())

    records = df_to_insert[
        [
            "sensor_id",
            "facility_id",
            "forecast_horizon_at",
            "predicted_value",
            "lower_bound",
            "upper_bound",
        ]
    ].to_dict(orient="records")

    total_rows = len(records)
    batch_size = 500

    for i in range(0, total_rows, batch_size):
        batch = records[i : i + batch_size]
        supabase.table("forecasts").insert(batch).execute()
        inserted_count = min(i + batch_size, total_rows)
        print(f"Inserted {inserted_count}/{total_rows} rows for sensor {sensor_id}")


def verify_forecasts(supabase: Client) -> None:
    """
    Verification query: pulls back 3 rows from forecasts table for SEN-023
    and validates that the forecast begins strictly after the final actual reading.
    """
    print("\n" + "=" * 80)
    print("VERIFICATION QUERY: SEN-023 Forecast Verification")
    print("=" * 80)

    actual_res = (
        supabase.table("sensor_readings_fact")
        .select("recorded_at")
        .eq("sensor_id", "SEN-023")
        .order("recorded_at", desc=True)
        .limit(1)
        .execute()
    )
    last_actual_str = "N/A"
    last_actual_dt = None
    if actual_res.data:
        last_actual_dt = pd.to_datetime(actual_res.data[0]["recorded_at"]).tz_convert("Asia/Kolkata")
        last_actual_str = last_actual_dt.strftime("%Y-%m-%d %H:%M:%S IST")

    sample_res = (
        supabase.table("forecasts")
        .select("forecast_horizon_at, predicted_value, lower_bound, upper_bound")
        .eq("sensor_id", "SEN-023")
        .order("forecast_horizon_at", desc=False)
        .limit(3)
        .execute()
    )

    first_forecast_dt = None
    first_forecast_str = "N/A"
    sample_rows = sample_res.data or []
    if sample_rows:
        first_forecast_dt = pd.to_datetime(sample_rows[0]["forecast_horizon_at"]).tz_convert("Asia/Kolkata")
        first_forecast_str = first_forecast_dt.strftime("%Y-%m-%d %H:%M:%S IST")

    last_fc_res = (
        supabase.table("forecasts")
        .select("forecast_horizon_at")
        .eq("sensor_id", "SEN-023")
        .order("forecast_horizon_at", desc=True)
        .limit(1)
        .execute()
    )
    last_forecast_str = "N/A"
    if last_fc_res.data:
        last_fc_dt = pd.to_datetime(last_fc_res.data[0]["forecast_horizon_at"]).tz_convert("Asia/Kolkata")
        last_forecast_str = last_fc_dt.strftime("%Y-%m-%d %H:%M:%S IST")

    count_res = (
        supabase.table("forecasts")
        .select("id", count="exact")
        .eq("sensor_id", "SEN-023")
        .limit(1)
        .execute()
    )
    row_count = count_res.count if hasattr(count_res, "count") else len(count_res.data)

    print(f"Sensor ID:                   SEN-023 (Campus Feed)")
    print(f"Total Forecast Rows in DB:   {row_count} (Expected: 192)")
    print(f"Last Actual Reading (DB):    {last_actual_str}")
    print(f"First Forecast Point (DB):   {first_forecast_str}")
    print(f"Last Forecast Point (DB):    {last_forecast_str}")

    boundary_valid = False
    if first_forecast_dt and last_actual_dt:
        boundary_valid = first_forecast_dt > last_actual_dt
    print(f"Verification Boundary Test:  {'PASS (strictly future)' if boundary_valid else 'FAIL'}")

    print("\nFirst 3 Forecast Points Sample:")
    for idx, r in enumerate(sample_rows, 1):
        ts_val = pd.to_datetime(r["forecast_horizon_at"]).tz_convert("Asia/Kolkata").strftime("%Y-%m-%d %H:%M:%S IST")
        print(f"  [{idx}] Time: {ts_val} | Predicted: {r['predicted_value']} kW | Range: [{r['lower_bound']} - {r['upper_bound']}] kW")

    print("=" * 80 + "\n")


def run_forecast_pipeline() -> None:
    """Executes the full forecasting pipeline across all 5 target sensors."""
    print("=" * 80)
    print("CAMPUS SUSTAINABILITY DASHBOARD - PROPHET FORECASTING PIPELINE")
    print("=" * 80)

    start_total_time = time.time()
    supabase = init_supabase()

    validate_sensor_facility_mappings(supabase)

    pipeline_summary: List[Dict[str, Any]] = []

    for config in SENSOR_CONFIGS:
        sensor_id = config["sensor_id"]
        facility_id = config["facility_id"]
        metric_name = config["metric_name"]

        print(f"\n[{sensor_id}] Processing forecast for {metric_name} ({facility_id})...")

        df = fetch_sensor_data(supabase, sensor_id)

        # Call pure ML forecast service
        forecast_df, train_duration = train_and_forecast(df, config)

        insert_forecasts(supabase, forecast_df, sensor_id, facility_id)

        pipeline_summary.append(
            {
                "sensor_id": sensor_id,
                "metric": metric_name,
                "rows_inserted": len(forecast_df),
                "duration_sec": round(train_duration, 2),
            }
        )

    verify_forecasts(supabase)

    total_duration = time.time() - start_total_time
    print("=" * 80)
    print("FORECAST PIPELINE EXECUTION SUMMARY")
    print("=" * 80)
    for item in pipeline_summary:
        print(
            f"  * {item['sensor_id']} ({item['metric']}): {item['rows_inserted']} rows inserted "
            f"(Model fit: {item['duration_sec']}s)"
        )
    print(f"\nAll 5 forecasts successfully trained, validated, and updated in {total_duration:.2f} seconds.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_forecast_pipeline()
