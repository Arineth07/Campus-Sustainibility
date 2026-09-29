"""Water Data Service.

Provides domain-level data structures for Water monitoring:
- Current flow rate & timestamp
- Recent historical telemetry (e.g. 24h, 48h, 7d)
- Persisted 48-hour Prophet forecasts with uncertainty bounds
- Anomaly flags from sensor_readings_fact
- Facility context
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pandas as pd

from services import supabase_service
from utils.constants import MAIN_WATER_SENSOR_ID
from utils.formatting import format_ist, format_number, parse_timestamptz


def get_water_sensors() -> List[Dict[str, Any]]:
    """Return all sensors measuring water flow."""
    sensors = supabase_service.fetch_sensors()
    return [s for s in sensors if s.get("sensor_type") == "WATER_FLOW"]


def get_water_overview(sensor_id: str = MAIN_WATER_SENSOR_ID) -> Dict[str, Any]:
    """
    Get consolidated water context for a given sensor (defaults to SEN-021 Main Supply Flow):
    - Latest reading value & timestamp
    - Sensor & facility metadata
    - Anomaly status of latest reading
    """
    facilities = {f["facility_id"]: f for f in supabase_service.fetch_facilities()}
    sensors = {s["sensor_id"]: s for s in supabase_service.fetch_sensors()}
    
    sensor_meta = sensors.get(sensor_id, {})
    facility_id = sensor_meta.get("facility_id", "")
    facility_meta = facilities.get(facility_id, {})
    
    latest = supabase_service.fetch_latest_reading(sensor_id)
    
    if latest:
        current_val = float(latest["reading_value"]) if latest["reading_value"] is not None else None
        current_ts = latest["recorded_at"]
        is_anomaly = bool(latest.get("is_anomaly", False))
        anomaly_score = float(latest["anomaly_score"]) if latest.get("anomaly_score") is not None else None
    else:
        current_val = None
        current_ts = None
        is_anomaly = False
        anomaly_score = None

    return {
        "sensor_id": sensor_id,
        "metric_name": sensor_meta.get("metric_measured", "Water Flow Rate"),
        "unit": sensor_meta.get("unit", "L/min"),
        "facility_id": facility_id,
        "facility_name": facility_meta.get("facility_name", facility_id or "Pump House & STP"),
        "zone": facility_meta.get("zone", "Utility"),
        "current_val": current_val,
        "current_val_formatted": format_number(current_val, digits=1),
        "latest_timestamp": current_ts,
        "latest_timestamp_formatted": format_ist(current_ts) if current_ts else "Unavailable",
        "is_anomaly": is_anomaly,
        "anomaly_score": anomaly_score,
        "normal_lower_bound": sensor_meta.get("normal_lower_bound"),
        "normal_upper_bound": sensor_meta.get("normal_upper_bound"),
        "status": sensor_meta.get("status", "ACTIVE"),
    }


def get_water_history_and_forecast(
    sensor_id: str = MAIN_WATER_SENSOR_ID,
    history_hours: float = 48.0,
) -> Dict[str, Any]:
    """
    Returns historical readings paired with persisted 48-hour forecast records.
    Historical readings are anchored to dataset MAX(recorded_at).
    """
    overview = get_water_overview(sensor_id)
    
    # 1. Historical Telemetry
    history_df = supabase_service.fetch_recent_readings(sensor_id, hours=history_hours)
    
    # 2. Persisted Forecast (read directly from Supabase, NO ML training)
    forecast_df = supabase_service.fetch_persisted_forecast(sensor_id)
    
    return {
        "overview": overview,
        "history_df": history_df,
        "forecast_df": forecast_df,
        "has_history": not history_df.empty,
        "has_forecast": not forecast_df.empty,
        "history_rows": len(history_df),
        "forecast_rows": len(forecast_df),
    }
