"""Waste Operational Data Service.

Integrates the operational WasteStatusEngine to provide:
- Real-time unclipped fill level (%)
- Standard operational severity (LOW, MEDIUM, HIGH, CRITICAL)
- 3h median fill-rate (pph)
- 1-hour and 3-hour fill projections
- Surge detection and overflow alerts
- History for visualization

Strictly does NOT implement a misleading time-to-85% countdown.
Never imports from ML Test/.
Keeps ML computation cleanly encapsulated inside the service layer.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from services import supabase_service
from ML.waste.waste_status_service import WasteStatusEngine, WasteStatusResult
from utils.formatting import format_ist, format_number

logger = logging.getLogger("waste_service")

# Waste sensors defined in system architecture
WASTE_SENSORS_CONFIG = [
    {
        "sensor_id": "SEN-013",
        "facility_id": "FAC-06",
        "facility_name": "Boys' Hostel Block 1",
        "zone": "Residential",
    },
    {
        "sensor_id": "SEN-016",
        "facility_id": "FAC-07",
        "facility_name": "Girls' Hostel Block 1",
        "zone": "Residential",
    },
    {
        "sensor_id": "SEN-019",
        "facility_id": "FAC-08",
        "facility_name": "Central Mess & Canteen",
        "zone": "Dining/Utility",
    },
]

# Shared instance of the tested ML WasteStatusEngine
_WASTE_ENGINE = WasteStatusEngine(
    warning_threshold=70.0,
    critical_threshold=85.0,
    overflow_threshold=100.0,
    surge_threshold=15.0,
    emptying_threshold=-20.0,
    lookback_hours=3.0,
    sampling_interval_min=30,
)


def get_waste_sensor_configs() -> List[Dict[str, Any]]:
    return WASTE_SENSORS_CONFIG


def get_operational_waste_status(sensor_id: str) -> Dict[str, Any]:
    """
    Evaluates current operational waste status for a given sensor using
    the operational WasteStatusEngine.
    """
    cfg = next((c for c in WASTE_SENSORS_CONFIG if c["sensor_id"] == sensor_id), None)
    facility_id = cfg["facility_id"] if cfg else "UNKNOWN"
    facility_name = cfg["facility_name"] if cfg else sensor_id
    zone = cfg["zone"] if cfg else "Campus"

    # Fetch last 12 hours of readings (covers lookback window of 3h easily at 30-min sampling)
    history_df = supabase_service.fetch_recent_readings(sensor_id, hours=12.0, limit=100)

    if history_df.empty:
        return {
            "sensor_id": sensor_id,
            "facility_id": facility_id,
            "facility_name": facility_name,
            "zone": zone,
            "timestamp": "Unavailable",
            "timestamp_formatted": "Unavailable",
            "current_fill": None,
            "current_fill_formatted": "Unavailable",
            "status": "No Telemetry",
            "alert_severity": "LOW",
            "fill_rate_pph": None,
            "fill_rate_formatted": "N/A",
            "projected_fill_1h": None,
            "projected_fill_3h": None,
            "projected_fill_1h_formatted": "N/A",
            "projected_fill_3h_formatted": "N/A",
            "surge_detected": False,
            "surge_magnitude": None,
            "emptying_detected": False,
            "emptying_magnitude": None,
            "projection_state": "INSUFFICIENT_DATA",
            "notes": "No sensor readings retrieved from database.",
            "is_overflow": False,
        }

    # Execute ML runtime evaluation (pure Python, fast in-memory)
    eval_result: WasteStatusResult = _WASTE_ENGINE.evaluate(
        history_df=history_df,
        sensor_id=sensor_id,
        facility_id=facility_id,
    )

    current_fill = eval_result.current_fill
    is_overflow = bool(current_fill is not None and current_fill > 100.0)

    # Format values clearly
    curr_fill_str = f"{current_fill:.1f}%" if current_fill is not None else "N/A"
    
    fill_rate_str = (
        f"{eval_result.fill_rate_pph:+.1f} %/h"
        if eval_result.fill_rate_pph is not None
        else "N/A (insufficient rate)"
    )

    proj_1h_str = (
        f"{eval_result.projected_fill_1h:.1f}%"
        if eval_result.projected_fill_1h is not None
        else f"Suspended ({eval_result.projection_state})"
    )

    proj_3h_str = (
        f"{eval_result.projected_fill_3h:.1f}%"
        if eval_result.projected_fill_3h is not None
        else f"Suspended ({eval_result.projection_state})"
    )

    ts_formatted = format_ist(eval_result.timestamp) if eval_result.timestamp != "N/A" else "N/A"

    return {
        "sensor_id": sensor_id,
        "facility_id": facility_id,
        "facility_name": facility_name,
        "zone": zone,
        "timestamp": eval_result.timestamp,
        "timestamp_formatted": ts_formatted,
        "current_fill": current_fill,
        "current_fill_formatted": curr_fill_str,
        "status": eval_result.status,
        "alert_severity": eval_result.alert_severity,
        "fill_rate_pph": eval_result.fill_rate_pph,
        "fill_rate_formatted": fill_rate_str,
        "projected_fill_1h": eval_result.projected_fill_1h,
        "projected_fill_3h": eval_result.projected_fill_3h,
        "projected_fill_1h_formatted": proj_1h_str,
        "projected_fill_3h_formatted": proj_3h_str,
        "surge_detected": eval_result.surge_detected,
        "surge_magnitude": eval_result.surge_magnitude,
        "emptying_detected": eval_result.emptying_detected,
        "emptying_magnitude": eval_result.emptying_magnitude,
        "projection_state": eval_result.projection_state,
        "notes": eval_result.notes,
        "is_overflow": is_overflow,
    }


def get_all_operational_waste_statuses() -> List[Dict[str, Any]]:
    """Return operational status for all monitored waste bins."""
    return [get_operational_waste_status(cfg["sensor_id"]) for cfg in WASTE_SENSORS_CONFIG]


def get_waste_history(sensor_id: str, hours: float = 48.0) -> pd.DataFrame:
    """Retrieve historical telemetry for chart plotting."""
    return supabase_service.fetch_recent_readings(sensor_id, hours=hours, limit=500)
