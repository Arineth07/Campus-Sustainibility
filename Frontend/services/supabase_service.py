"""Supabase Data Access Service.

Provides centralized queries, connection caching, normalization,
timestamp parsing, and resilience for all telemetry, facility,
sensor, anomaly, and forecast records in Supabase.
"""

from __future__ import annotations

import logging
import os
import sys
import time as time_mod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv

# Ensure PROJECT_ROOT and Frontend are in sys.path
_CURRENT_DIR = Path(__file__).resolve().parent
_FRONTEND_DIR = _CURRENT_DIR.parent
_PROJECT_ROOT = _FRONTEND_DIR.parent

for p in (str(_PROJECT_ROOT), str(_FRONTEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

for _env_path in (_FRONTEND_DIR / ".env", _PROJECT_ROOT / ".env"):
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
        break
else:
    load_dotenv()

from utils.formatting import parse_timestamptz

logger = logging.getLogger("supabase_service")

_CACHE_TTL_SEC = 45.0
_CACHE: Dict[str, Tuple[float, Any]] = {}
_CLIENT_INSTANCE = None


class DataUnavailable(Exception):
    """Raised when Supabase is not reachable or queries fail."""


def _cache_get(key: str) -> Optional[Any]:
    hit = _CACHE.get(key)
    if not hit:
        return None
    expires, value = hit
    if time_mod.time() > expires:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any, ttl: float = _CACHE_TTL_SEC) -> Any:
    _CACHE[key] = (time_mod.time() + ttl, value)
    return value


def get_supabase_config() -> Tuple[Optional[str], Optional[str]]:
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    return url, key


def get_client(refresh: bool = False):
    global _CLIENT_INSTANCE
    if _CLIENT_INSTANCE is not None and not refresh:
        return _CLIENT_INSTANCE

    url, key = get_supabase_config()
    if not url or not key:
        return None
    from supabase import create_client
    _CLIENT_INSTANCE = create_client(url, key)
    return _CLIENT_INSTANCE


def _execute_with_retry(query_builder, max_retries: int = 3):
    last_exc = None
    for attempt in range(max_retries):
        try:
            return query_builder.execute()
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Supabase query attempt %d/%d failed: %s. Retrying...",
                attempt + 1,
                max_retries,
                exc,
            )
            time_mod.sleep(0.4 * (attempt + 1))
            if attempt == max_retries - 2:
                # Force client recreate on next-to-last attempt in case connection died
                get_client(refresh=True)
    raise DataUnavailable(f"Supabase query failed after {max_retries} attempts: {last_exc}")


def check_connection() -> Dict[str, Any]:
    client = get_client()
    if client is None:
        return {
            "ok": False,
            "configured": False,
            "message": "Supabase credentials are not configured. Set SUPABASE_URL and SUPABASE_KEY in .env.",
        }
    try:
        q = client.table("facilities_dim").select("facility_id").limit(1)
        res = _execute_with_retry(q, max_retries=2)
        return {
            "ok": True,
            "configured": True,
            "message": "Connected to Supabase successfully",
            "facility_test": len(res.data or []) > 0,
        }
    except Exception as exc:
        return {
            "ok": False,
            "configured": True,
            "message": f"Supabase connection test failed: {exc}",
        }


def _require_client():
    client = get_client()
    if client is None:
        raise DataUnavailable("Supabase client is not configured.")
    return client


def fetch_facilities() -> List[Dict[str, Any]]:
    """Retrieve all facilities with geometry coordinates and classifications."""
    cached = _cache_get("facilities_all")
    if cached is not None:
        return cached

    client = _require_client()
    q = (
        client.table("facilities_dim")
        .select(
            "facility_id, facility_name, facility_type, zone, capacity, "
            "floor_area_sqm, operating_hours, is_critical, latitude, longitude"
        )
        .order("facility_id")
    )
    res = _execute_with_retry(q)
    data = res.data or []
    return _cache_set("facilities_all", data, ttl=180.0)


def fetch_sensors() -> List[Dict[str, Any]]:
    """Retrieve all sensors metadata."""
    cached = _cache_get("sensors_all")
    if cached is not None:
        return cached

    client = _require_client()
    q = (
        client.table("sensors_dim")
        .select(
            "sensor_id, facility_id, sensor_type, metric_measured, unit, "
            "normal_lower_bound, normal_upper_bound, sampling_interval_min, status"
        )
        .order("sensor_id")
    )
    res = _execute_with_retry(q)
    data = res.data or []
    return _cache_set("sensors_all", data, ttl=180.0)


def fetch_max_recorded_at() -> Optional[str]:
    """Retrieve dataset MAX(recorded_at) as ISO string to serve as the data clock."""
    cached = _cache_get("max_recorded_at")
    if cached is not None:
        return cached

    client = _require_client()
    q = (
        client.table("sensor_readings_fact")
        .select("recorded_at")
        .order("recorded_at", desc=True)
        .limit(1)
    )
    res = _execute_with_retry(q)
    data = res.data or []
    val = data[0]["recorded_at"] if data else None
    return _cache_set("max_recorded_at", val, ttl=45.0)


def fetch_latest_reading(sensor_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve the most recent reading for a given sensor."""
    key = f"latest:{sensor_id}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    client = _require_client()
    q = (
        client.table("sensor_readings_fact")
        .select("reading_id, sensor_id, facility_id, recorded_at, reading_value, is_anomaly, anomaly_score")
        .eq("sensor_id", sensor_id)
        .order("recorded_at", desc=True)
        .limit(1)
    )
    try:
        res = _execute_with_retry(q)
        data = res.data or []
        val = data[0] if data else None
        return _cache_set(key, val, ttl=45.0)
    except Exception as exc:
        logger.error("Failed to fetch latest reading for %s: %s", sensor_id, exc)
        return None


def fetch_latest_readings_for_sensors(sensor_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Batch/mapped fetch of latest readings for a list of sensor IDs."""
    out: Dict[str, Dict[str, Any]] = {}
    for sid in sensor_ids:
        row = fetch_latest_reading(sid)
        if row:
            out[sid] = row
    return out


def fetch_recent_readings(
    sensor_id: str,
    hours: Optional[float] = 48.0,
    limit: int = 1500,
) -> pd.DataFrame:
    """
    Retrieve historical readings anchored to the dataset MAX(recorded_at).
    Returns a pandas DataFrame sorted chronologically.
    """
    key = f"readings:{sensor_id}:{hours}:{limit}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    client = _require_client()
    query = (
        client.table("sensor_readings_fact")
        .select("recorded_at, reading_value, is_anomaly, anomaly_score")
        .eq("sensor_id", sensor_id)
    )

    if hours is not None:
        max_ts_raw = fetch_max_recorded_at()
        max_dt = parse_timestamptz(max_ts_raw)
        if max_dt is not None:
            start_dt = max_dt - timedelta(hours=hours)
            query = query.gte("recorded_at", start_dt.isoformat()).lte("recorded_at", max_dt.isoformat())

    query = query.order("recorded_at", desc=False).limit(limit)
    try:
        res = _execute_with_retry(query)
        data = res.data or []
    except Exception as exc:
        logger.error("Failed to fetch readings for %s: %s", sensor_id, exc)
        data = []

    if not data:
        df = pd.DataFrame(columns=["recorded_at", "reading_value", "is_anomaly", "anomaly_score"])
    else:
        df = pd.DataFrame(data)
        df["recorded_at"] = pd.to_datetime(df["recorded_at"])
        df["reading_value"] = pd.to_numeric(df["reading_value"], errors="coerce")
        df = df.sort_values("recorded_at").reset_index(drop=True)

    return _cache_set(key, df, ttl=60.0)


def fetch_persisted_forecast(sensor_id: str) -> pd.DataFrame:
    """
    Retrieve persisted Prophet predictions from the forecasts table.
    Guarantees that NO ML training occurs inside dashboard callbacks.
    """
    key = f"forecast:{sensor_id}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    client = _require_client()
    q = (
        client.table("forecasts")
        .select("forecast_horizon_at, predicted_value, lower_bound, upper_bound, facility_id")
        .eq("sensor_id", sensor_id)
        .order("forecast_horizon_at", desc=False)
    )
    try:
        res = _execute_with_retry(q)
        data = res.data or []
    except Exception as exc:
        logger.error("Failed to fetch forecast for %s: %s", sensor_id, exc)
        data = []

    if not data:
        df = pd.DataFrame(
            columns=["forecast_horizon_at", "predicted_value", "lower_bound", "upper_bound", "facility_id"]
        )
    else:
        df = pd.DataFrame(data)
        df["forecast_horizon_at"] = pd.to_datetime(df["forecast_horizon_at"])
        df["predicted_value"] = pd.to_numeric(df["predicted_value"], errors="coerce")
        df["lower_bound"] = pd.to_numeric(df["lower_bound"], errors="coerce")
        df["upper_bound"] = pd.to_numeric(df["upper_bound"], errors="coerce")
        df = df.sort_values("forecast_horizon_at").reset_index(drop=True)

    return _cache_set(key, df, ttl=90.0)


def fetch_recent_anomalies(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve recent anomaly records from sensor_readings_fact."""
    key = f"anomalies_feed:{limit}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    client = _require_client()
    q = (
        client.table("sensor_readings_fact")
        .select("reading_id, sensor_id, facility_id, recorded_at, reading_value, is_anomaly, anomaly_score")
        .eq("is_anomaly", True)
        .order("recorded_at", desc=True)
        .limit(limit)
    )
    try:
        res = _execute_with_retry(q)
        data = res.data or []
    except Exception as exc:
        logger.error("Failed to fetch anomalies: %s", exc)
        data = []
    return _cache_set(key, data, ttl=45.0)
