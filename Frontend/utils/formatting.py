"""Display formatting. Timestamps are shown in IST."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from utils.constants import IST_TZ

IST = ZoneInfo(IST_TZ)


def parse_timestamptz(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def format_ist(value, with_seconds: bool = True) -> str:
    dt = parse_timestamptz(value)
    if dt is None:
        return "?"
    fmt = "%Y-%m-%d %H:%M:%S IST" if with_seconds else "%Y-%m-%d %H:%M IST"
    return dt.strftime(fmt)


def format_number(value, digits: int = 1) -> str:
    if value is None:
        return "?"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "?"
    if abs(number) >= 1000:
        return f"{number:,.0f}"
    return f"{number:,.{digits}f}"


def format_range(lower, upper, unit: str = "") -> str:
    unit_suffix = f" {unit}" if unit else ""
    has_lo = lower is not None and str(lower) != ""
    has_hi = upper is not None and str(upper) != ""
    if has_lo and has_hi:
        return f"{format_number(lower)} ? {format_number(upper)}{unit_suffix}"
    if has_hi:
        return f"? {format_number(upper)}{unit_suffix}"
    if has_lo:
        return f"? {format_number(lower)}{unit_suffix}"
    return "Not configured"


def format_anomaly_score(value) -> str:
    if value is None or value == "":
        return "N/A"
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "N/A"
