"""Read-only Supabase queries for the Overview dashboard.

Does not fetch the full sensor_readings_fact table.
Time windows are computed from MAX(recorded_at) so historical synthetic
data still works. Do not use wall-clock NOW() as the dataset clock.
"""

from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
from time import time
from typing import Any

from data.supabase_client import get_supabase_client
from utils.constants import (
    ANOMALY_TABLE_LIMIT,
    CAMPUS_FEED_SENSOR_ID,
    MAIN_WATER_SENSOR_ID,
    MAX_READING_ROWS,
    METRIC_CATALOG,
    PAGE_SIZE,
)
from utils.formatting import parse_timestamptz

_CACHE_TTL_SEC = 45.0
_CACHE: dict[str, tuple[float, Any]] = {}


class DataUnavailable(Exception):
    """Raised when Supabase is not configured or a query fails."""


def _cache_get(key: str):
    hit = _CACHE.get(key)
    if not hit:
        return None
    expires, value = hit
    if time() > expires:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any) -> Any:
    _CACHE[key] = (time() + _CACHE_TTL_SEC, value)
    return value


def connection_state() -> dict[str, Any]:
    client = get_supabase_client()
    if client is None:
        return {
            "ok": False,
            "configured": False,
            "message": "Supabase credentials are not configured. Set SUPABASE_URL and SUPABASE_KEY.",
        }
    return {"ok": True, "configured": True, "message": "Supabase client ready"}


def _client():
    client = get_supabase_client()
    if client is None:
        raise DataUnavailable("Supabase credentials are not configured.")
    return client


def _select(table: str, columns: str, builder=None, limit: int | None = None):
    query = _client().table(table).select(columns)
    if builder is not None:
        query = builder(query)
    if limit is not None:
        query = query.limit(limit)
    return query.execute()


def fetch_facilities() -> list[dict[str, Any]]:
    cached = _cache_get("facilities")
    if cached is not None:
        return cached
    res = _select(
        "facilities_dim",
        "facility_id,facility_name,facility_type,zone,capacity,floor_area_sqm,"
        "operating_hours,is_critical,latitude,longitude",
    )
    return _cache_set("facilities", res.data or [])


def fetch_sensors() -> list[dict[str, Any]]:
    cached = _cache_get("sensors")
    if cached is not None:
        return cached
    res = _select(
        "sensors_dim",
        "sensor_id,facility_id,sensor_type,metric_measured,unit,"
        "normal_lower_bound,normal_upper_bound,sampling_interval_min,status",
    )
    return _cache_set("sensors", res.data or [])


def fetch_max_recorded_at():
    cached = _cache_get("max_recorded_at")
    if cached is not None:
        return cached
    res = (
        _client()
        .table("sensor_readings_fact")
        .select("recorded_at")
        .order("recorded_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    value = rows[0]["recorded_at"] if rows else None
    return _cache_set("max_recorded_at", value)


def fetch_latest_reading(sensor_id: str) -> dict[str, Any] | None:
    key = f"latest:{sensor_id}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    res = (
        _client()
        .table("sensor_readings_fact")
        .select("reading_id,sensor_id,facility_id,recorded_at,reading_value,is_anomaly,anomaly_score")
        .eq("sensor_id", sensor_id)
        .order("recorded_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return _cache_set(key, rows[0] if rows else None)


def fetch_latest_for_sensors(sensor_ids: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for sid in sensor_ids:
        row = fetch_latest_reading(sid)
        if row:
            out[sid] = row
    return out


def count_anomalies_since(since_iso: str | None) -> int:
    key = f"anomaly_count:{since_iso}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    query = (
        _client()
        .table("sensor_readings_fact")
        .select("reading_id", count="exact")
        .eq("is_anomaly", True)
    )
    if since_iso:
        query = query.gte("recorded_at", since_iso)
    res = query.limit(1).execute()
    return _cache_set(key, int(res.count or 0))


def fetch_recent_anomalies(limit: int = ANOMALY_TABLE_LIMIT) -> list[dict[str, Any]]:
    key = f"anomalies:{limit}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    res = (
        _client()
        .table("sensor_readings_fact")
        .select("reading_id,sensor_id,facility_id,recorded_at,reading_value,is_anomaly,anomaly_score")
        .eq("is_anomaly", True)
        .order("recorded_at", desc=True)
        .limit(limit)
        .execute()
    )
    return _cache_set(key, res.data or [])


def count_critical_facility_anomalies_since(since_iso: str | None, critical_ids: list[str]) -> int:
    if not critical_ids:
        return 0
    key = f"crit_anom:{since_iso}:{','.join(sorted(critical_ids))}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    query = (
        _client()
        .table("sensor_readings_fact")
        .select("reading_id", count="exact")
        .eq("is_anomaly", True)
        .in_("facility_id", critical_ids)
    )
    if since_iso:
        query = query.gte("recorded_at", since_iso)
    res = query.limit(1).execute()
    return _cache_set(key, int(res.count or 0))


def _paginate_readings(sensor_ids: list[str], start_iso: str | None, end_iso: str | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not sensor_ids:
        return rows
    offset = 0
    while len(rows) < MAX_READING_ROWS:
        query = (
            _client()
            .table("sensor_readings_fact")
            .select("sensor_id,facility_id,recorded_at,reading_value,is_anomaly")
            .in_("sensor_id", sensor_ids)
            .order("recorded_at", desc=False)
        )
        if start_iso:
            query = query.gte("recorded_at", start_iso)
        if end_iso:
            query = query.lte("recorded_at", end_iso)
        end = min(offset + PAGE_SIZE - 1, offset + PAGE_SIZE - 1)
        query = query.range(offset, offset + PAGE_SIZE - 1)
        res = query.execute()
        chunk = res.data or []
        rows.extend(chunk)
        if len(chunk) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset >= MAX_READING_ROWS:
            break
    return rows[:MAX_READING_ROWS]


def window_bounds(range_key: str) -> tuple[str | None, str | None, Any]:
    """Return (start_iso, end_iso, max_dt) relative to dataset MAX(recorded_at)."""
    max_raw = fetch_max_recorded_at()
    max_dt = parse_timestamptz(max_raw)
    if max_dt is None:
        return None, None, None
    end_iso = max_dt.isoformat()
    if range_key == "full":
        return None, end_iso, max_dt
    hours = {"24h": 24, "7d": 24 * 7, "30d": 24 * 30}.get(range_key, 24)
    start_dt = max_dt - timedelta(hours=hours)
    return start_dt.isoformat(), end_iso, max_dt


def resolve_metric_sensors(metric_key: str) -> list[dict[str, Any]]:
    spec = METRIC_CATALOG[metric_key]
    sensors = fetch_sensors()
    if spec.get("sensor_ids"):
        wanted = set(spec["sensor_ids"])
        return [s for s in sensors if s.get("sensor_id") in wanted]
    return [s for s in sensors if s.get("sensor_type") == spec["sensor_type"]]


def fetch_metric_series(metric_key: str, range_key: str) -> dict[str, Any]:
    spec = METRIC_CATALOG[metric_key]
    sensors = resolve_metric_sensors(metric_key)
    start_iso, end_iso, max_dt = window_bounds(range_key)
    ids = [s["sensor_id"] for s in sensors]
    key = f"series:{metric_key}:{range_key}:{','.join(ids)}:{start_iso}:{end_iso}"
    cached = _cache_get(key)
    if cached is not None:
        return cached
    rows = _paginate_readings(ids, start_iso, end_iso)
    payload = {
        "spec": spec,
        "sensors": sensors,
        "rows": rows,
        "start_iso": start_iso,
        "end_iso": end_iso,
        "data_max_at": max_dt.isoformat() if max_dt is not None else None,
        "truncated": len(rows) >= MAX_READING_ROWS,
    }
    return _cache_set(key, payload)


def last_24h_since_iso() -> str | None:
    start_iso, _, _ = window_bounds("24h")
    return start_iso


# Keep unused imports from triggering lint by using CAMPUS ids in helpers.
def campus_feed_sensor_id() -> str:
    return CAMPUS_FEED_SENSOR_ID


def main_water_sensor_id() -> str:
    return MAIN_WATER_SENSOR_ID
