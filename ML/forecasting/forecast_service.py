"""
Campus Sustainability Dashboard - Prophet Forecasting Runtime Service
======================================================================
Pure, database-agnostic forecasting service using Facebook Prophet.
Trains models and generates 48-hour ahead predictions for energy, water,
and waste bin sensors based on prepared DataFrames.

Architectural Guarantees:
- Database-agnostic: No Supabase queries, connections, or writes.
- Environment-agnostic: No .env loading, no credential dependencies.
- Import-safe: No network calls, no process exit, no execution on import.
- Pure runtime interface: train_and_forecast(df, config) -> (forecast_df, duration).
"""

import logging
import time
import warnings
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from prophet import Prophet

logger = logging.getLogger("forecast_service")

# Suppress cmdstanpy / prophet verbose logs
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)
warnings.filterwarnings("ignore")

# Target Sensors Configuration
SENSOR_CONFIGS: List[Dict[str, Any]] = [
    {
        "sensor_id": "SEN-023",
        "facility_id": "FAC-10",
        "metric_name": "Campus Feed (kW)",
        "sampling_interval_min": 15,
        "periods": 192,  # 48 hours * 4
        "freq": "15min",
        "growth": "linear",
        "is_waste_bin": False,
    },
    {
        "sensor_id": "SEN-021",
        "facility_id": "FAC-09",
        "metric_name": "Water Supply L/min",
        "sampling_interval_min": 15,
        "periods": 192,  # 48 hours * 4
        "freq": "15min",
        "growth": "linear",
        "is_waste_bin": False,
    },
    {
        "sensor_id": "SEN-013",
        "facility_id": "FAC-06",
        "metric_name": "Bin Fill % (Boys)",
        "sampling_interval_min": 30,
        "periods": 96,  # 48 hours * 2
        "freq": "30min",
        "growth": "logistic",
        "is_waste_bin": True,
        "cap": 100.0,
        "floor": 0.0,
    },
    {
        "sensor_id": "SEN-016",
        "facility_id": "FAC-07",
        "metric_name": "Bin Fill % (Girls)",
        "sampling_interval_min": 30,
        "periods": 96,  # 48 hours * 2
        "freq": "30min",
        "growth": "logistic",
        "is_waste_bin": True,
        "cap": 100.0,
        "floor": 0.0,
    },
    {
        "sensor_id": "SEN-019",
        "facility_id": "FAC-08",
        "metric_name": "Bin Fill % (Mess)",
        "sampling_interval_min": 30,
        "periods": 96,  # 48 hours * 2
        "freq": "30min",
        "growth": "logistic",
        "is_waste_bin": True,
        "cap": 100.0,
        "floor": 0.0,
    },
]


def get_sensor_config(sensor_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve configuration dictionary for a given sensor_id."""
    for cfg in SENSOR_CONFIGS:
        if cfg["sensor_id"] == sensor_id:
            return cfg.copy()
    return None


def validate_forecast(
    future_forecast: pd.DataFrame,
    last_actual_ts: pd.Timestamp,
    config: Dict[str, Any],
) -> None:
    """
    Explicit validation for generated forecast:
    A. The forecast is not empty.
    B. The first forecast timestamp is strictly greater than the last actual timestamp.
    C. Forecast timestamps are strictly increasing.
    D. Number of future forecast rows is exactly equal to configured periods.
    E. No forecast timestamp is <= last actual timestamp.
    F. Forecast timestamps span the expected sampling interval (15 min or 30 min).
    """
    sensor_id = config["sensor_id"]
    expected_periods = config["periods"]
    sampling_min = config["sampling_interval_min"]
    expected_delta = pd.Timedelta(minutes=sampling_min)

    # A. Non-empty
    if future_forecast.empty:
        raise ValueError(f"Validation FAILED for {sensor_id}: Forecast is empty.")

    actual_rows = len(future_forecast)

    # D. Row count matches configured periods
    if actual_rows != expected_periods:
        raise ValueError(
            f"Validation FAILED for {sensor_id}: Expected {expected_periods} forecast rows, "
            f"got {actual_rows}."
        )

    forecast_ts = pd.to_datetime(future_forecast["ds"])
    first_forecast_ts = forecast_ts.min()
    last_forecast_ts = forecast_ts.max()

    # B. First forecast timestamp strictly greater than last actual
    if first_forecast_ts <= last_actual_ts:
        raise ValueError(
            f"Validation FAILED for {sensor_id}: First forecast timestamp {first_forecast_ts} "
            f"is not strictly greater than last actual timestamp {last_actual_ts}."
        )

    # E. No forecast timestamp <= last actual
    invalid_mask = forecast_ts <= last_actual_ts
    if invalid_mask.any():
        raise ValueError(
            f"Validation FAILED for {sensor_id}: Found {invalid_mask.sum()} forecast timestamps <= last actual timestamp."
        )

    # C. Timestamps strictly increasing
    if not forecast_ts.is_monotonic_increasing:
        raise ValueError(
            f"Validation FAILED for {sensor_id}: Forecast timestamps are not strictly increasing."
        )

    # F. Sampling interval verification
    first_step = first_forecast_ts - last_actual_ts
    if first_step != expected_delta:
        raise ValueError(
            f"Validation FAILED for {sensor_id}: Initial forecast step {first_step} != expected {expected_delta}."
        )

    diffs = forecast_ts.diff().dropna()
    if not (diffs == expected_delta).all():
        mismatched = diffs[diffs != expected_delta]
        raise ValueError(
            f"Validation FAILED for {sensor_id}: Sampling interval mismatch in forecast! Mismatched: {mismatched.tolist()}"
        )


def train_and_forecast(
    df: pd.DataFrame,
    config: Dict[str, Any],
) -> Tuple[pd.DataFrame, float]:
    """
    Train Prophet model and generate 48-hour ahead forecast.
    Configures daily and weekly seasonality, changepoint_prior_scale=0.05,
    multiplicative seasonality mode, and appropriate growth model.

    Parameters
    ----------
    df : pd.DataFrame
        Historical DataFrame containing 'recorded_at' and 'reading_value'.
    config : Dict[str, Any]
        Configuration dictionary with sensor specifications.

    Returns
    -------
    Tuple[pd.DataFrame, float]
        forecast_df: DataFrame with ['forecast_horizon_at', 'predicted_value', 'lower_bound', 'upper_bound'].
        training_duration: Float seconds elapsed during model fitting.
    """
    sensor_id = config["sensor_id"]
    growth = config["growth"]
    is_waste_bin = config.get("is_waste_bin", False)
    periods = config["periods"]
    freq = config["freq"]

    # Prophet requires 'ds' and 'y' (ds must be timezone-naive)
    train_df = pd.DataFrame()
    recorded_at = pd.to_datetime(df["recorded_at"])
    if recorded_at.dt.tz is not None:
        train_df["ds"] = recorded_at.dt.tz_localize(None)
    else:
        train_df["ds"] = recorded_at
    train_df["y"] = df["reading_value"].astype(float)

    if is_waste_bin:
        train_df["cap"] = config["cap"]
        train_df["floor"] = config["floor"]

    last_actual_ts = train_df["ds"].max()

    # Initialize Prophet model
    model = Prophet(
        growth=growth,
        daily_seasonality=True,
        weekly_seasonality=True,
        changepoint_prior_scale=0.05,
        seasonality_mode="multiplicative",
    )

    # Fit model
    start_time = time.time()
    model.fit(train_df)
    training_duration = time.time() - start_time
    logger.info(f"Prophet model training for {sensor_id} completed in {training_duration:.2f}s.")

    # Generate future dataframe
    future = model.make_future_dataframe(periods=periods, freq=freq)
    if is_waste_bin:
        future["cap"] = config["cap"]
        future["floor"] = config["floor"]

    forecast = model.predict(future)

    # Keep only rows where ds > last actual timestamp
    future_forecast = forecast[forecast["ds"] > last_actual_ts].copy()

    # Validate generated forecast
    validate_forecast(future_forecast, last_actual_ts, config)

    # Extract required columns
    forecast_df = pd.DataFrame()
    forecast_df["forecast_horizon_at"] = future_forecast["ds"]
    forecast_df["predicted_value"] = future_forecast["yhat"].astype(float)
    forecast_df["lower_bound"] = future_forecast["yhat_lower"].astype(float)
    forecast_df["upper_bound"] = future_forecast["yhat_upper"].astype(float)

    # For waste bin sensors, clip values to 0-100%
    if is_waste_bin:
        forecast_df["predicted_value"] = forecast_df["predicted_value"].clip(lower=0.0, upper=100.0)
        forecast_df["lower_bound"] = forecast_df["lower_bound"].clip(lower=0.0, upper=100.0)
        forecast_df["upper_bound"] = forecast_df["upper_bound"].clip(lower=0.0, upper=100.0)

    # Round to 2 decimal places for clean storage and display
    forecast_df["predicted_value"] = forecast_df["predicted_value"].round(2)
    forecast_df["lower_bound"] = forecast_df["lower_bound"].round(2)
    forecast_df["upper_bound"] = forecast_df["upper_bound"].round(2)

    return forecast_df, training_duration
