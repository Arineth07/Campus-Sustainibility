"""Frontend-derived campus status indicator.

This is NOT stored in the database and is NOT a certified campus status.
It exists so Overview can show a prototype health rollup until an official
status model (or ML pipeline) is defined.

Replace or override derive_campus_status() when a backend/ML status exists.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from utils.formatting import parse_timestamptz


def derive_campus_status(
    sensors: list[dict[str, Any]],
    latest_by_sensor: dict[str, dict[str, Any]],
    anomaly_count_window: int,
    critical_facility_anomaly_count: int,
    data_max_at,
) -> dict[str, Any]:
    """Derive a prototype status from live schema fields only.

    Inputs use existing columns:
      sensors_dim.status
      sensors_dim.sampling_interval_min
      sensors_dim.facility_id
      facilities_dim.is_critical (passed via sensor row if present)
      sensor_readings_fact.is_anomaly counts already filtered by caller
      latest reading recorded_at per sensor

    Returns a dict with label, tone, and reason strings for the UI.
    """
    data_max = parse_timestamptz(data_max_at)

    fault = [s for s in sensors if str(s.get("status") or "").upper() == "FAULT"]
    inactive = [s for s in sensors if str(s.get("status") or "").upper() == "INACTIVE"]
    maintenance = [s for s in sensors if str(s.get("status") or "").upper() == "MAINTENANCE"]

    stale: list[str] = []
    if data_max is not None:
        for sensor in sensors:
            sid = sensor.get("sensor_id")
            latest = latest_by_sensor.get(sid or "")
            if not latest:
                stale.append(str(sid))
                continue
            latest_ts = parse_timestamptz(latest.get("recorded_at"))
            if latest_ts is None:
                stale.append(str(sid))
                continue
            interval_min = int(sensor.get("sampling_interval_min") or 15)
            # Stale relative to the dataset clock, not wall-clock time.
            threshold = timedelta(minutes=max(interval_min * 3, 45))
            if data_max - latest_ts > threshold:
                stale.append(str(sid))

    reasons: list[str] = []
    label = "Nominal"
    tone = "ok"

    if fault:
        label = "Critical"
        tone = "critical"
        reasons.append(f"{len(fault)} sensor(s) in FAULT")
    elif critical_facility_anomaly_count > 0:
        label = "Critical"
        tone = "critical"
        reasons.append(
            f"{critical_facility_anomaly_count} anomal"
            f"{'y' if critical_facility_anomaly_count == 1 else 'ies'} "
            "on critical facilities in the dataset window"
        )
    elif anomaly_count_window > 0 or maintenance or stale:
        label = "Warning"
        tone = "warning"
        if anomaly_count_window > 0:
            reasons.append(f"{anomaly_count_window} flagged reading(s) in the last 24h of the dataset")
        if maintenance:
            reasons.append(f"{len(maintenance)} sensor(s) in MAINTENANCE")
        if stale:
            reasons.append(f"{len(stale)} sensor(s) stale vs dataset clock")
    else:
        reasons.append("No FAULT sensors and no flagged readings in the last 24h of the dataset")

    if inactive:
        reasons.append(f"{len(inactive)} sensor(s) INACTIVE")

    return {
        "label": label,
        "tone": tone,
        "reasons": reasons,
        "derived": True,
        "disclaimer": (
            "Prototype indicator derived in the frontend from sensor status, "
            "stale readings (vs dataset max recorded_at), and is_anomaly counts. "
            "Not stored in the database. Not an official or certified campus status."
        ),
    }
