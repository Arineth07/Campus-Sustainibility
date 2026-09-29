"""Recent anomaly table. Columns map to existing schema fields only."""

from __future__ import annotations

from typing import Any

from dash import dash_table, html

from utils.formatting import format_anomaly_score, format_ist, format_number, format_range


def build_anomaly_rows(
    anomalies: list[dict[str, Any]],
    sensors: list[dict[str, Any]],
    facilities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sensor_map = {s["sensor_id"]: s for s in sensors}
    facility_map = {f["facility_id"]: f for f in facilities}
    rows = []
    for item in anomalies:
        sensor = sensor_map.get(item.get("sensor_id"), {})
        facility = facility_map.get(item.get("facility_id"), {})
        unit = sensor.get("unit") or ""
        rows.append(
            {
                "Time": format_ist(item.get("recorded_at")),
                "Facility": facility.get("facility_name") or item.get("facility_id") or "?",
                "Sensor": item.get("sensor_id") or "?",
                "Metric": sensor.get("metric_measured") or "?",
                "Reading": format_number(item.get("reading_value")),
                "Unit": unit or "?",
                "Expected range": format_range(
                    sensor.get("normal_lower_bound"),
                    sensor.get("normal_upper_bound"),
                    unit,
                ),
                "Anomaly score": format_anomaly_score(item.get("anomaly_score")),
                "Sensor status": sensor.get("status") or "?",
            }
        )
    return rows


def anomaly_table(rows: list[dict[str, Any]]) -> html.Div:
    if not rows:
        return html.Div(
            "No anomaly records found in the current dataset.",
            className="iw-empty",
        )
    columns = [
        {"name": name, "id": name}
        for name in [
            "Time",
            "Facility",
            "Sensor",
            "Metric",
            "Reading",
            "Unit",
            "Expected range",
            "Anomaly score",
            "Sensor status",
        ]
    ]
    return dash_table.DataTable(
        data=rows,
        columns=columns,
        page_size=12,
        sort_action="native",
        style_table={"overflowX": "auto"},
        style_header={
            "backgroundColor": "#151b24",
            "color": "#9aa6b6",
            "fontWeight": "600",
            "border": "none",
            "fontSize": "12px",
            "textTransform": "uppercase",
            "letterSpacing": "0.04em",
        },
        style_cell={
            "backgroundColor": "#10151c",
            "color": "#d7deea",
            "border": "1px solid #1e2632",
            "fontSize": "13px",
            "padding": "8px 10px",
            "fontFamily": "IBM Plex Sans, Segoe UI, sans-serif",
            "whiteSpace": "nowrap",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#121821"},
        ],
    )
