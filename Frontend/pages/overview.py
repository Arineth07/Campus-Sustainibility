"""Overview / Command Center page.

Displays campus-level infrastructure telemetry, campus health rollup,
resource trend charts, and recent anomalies table.
All data is retrieved via the frontend service layer from Supabase.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import dash
import pandas as pd
from dash import Input, Output, callback, dcc, html

from components.anomaly_table import anomaly_table, build_anomaly_rows
from components.charts import empty_figure, metric_timeseries
from components.kpi_card import kpi_card
from services import energy_service, supabase_service, waste_service, water_service
from services.supabase_service import DataUnavailable
from utils.campus_status import derive_campus_status
from utils.constants import (
    CAMPUS_FEED_SENSOR_ID,
    MAIN_WATER_SENSOR_ID,
    METRIC_CATALOG,
)
from utils.formatting import format_ist, format_number, parse_timestamptz

dash.register_page(__name__, path="/", name="Overview")

IST = ZoneInfo("Asia/Kolkata")


def _error_banner(message: str) -> html.Div:
    return html.Div(message, className="iw-banner iw-banner-error")


def _note_banner(message: str) -> html.Div:
    return html.Div(message, className="iw-banner")


def _load_overview_context() -> dict:
    facilities = supabase_service.fetch_facilities()
    sensors = supabase_service.fetch_sensors()
    data_max = supabase_service.fetch_max_recorded_at()
    
    # 24h window calculation relative to data clock
    max_dt = parse_timestamptz(data_max)
    since_24h = (max_dt - timedelta(hours=24)).isoformat() if max_dt else None

    
    sensor_ids = [s["sensor_id"] for s in sensors]
    latest_by_sensor = supabase_service.fetch_latest_readings_for_sensors(sensor_ids)
    critical_ids = [f["facility_id"] for f in facilities if f.get("is_critical")]
    
    # Anomalies
    anomalies = supabase_service.fetch_recent_anomalies(limit=50)
    anomaly_total = len(anomalies)
    
    # Count 24h anomalies
    anomaly_24h = sum(
        1 for a in anomalies 
        if since_24h and a.get("recorded_at") and str(a["recorded_at"]) >= since_24h
    )
    critical_anom = sum(
        1 for a in anomalies 
        if a.get("facility_id") in critical_ids 
        and (not since_24h or str(a.get("recorded_at") or "") >= since_24h)
    )
    
    status = derive_campus_status(
        sensors=sensors,
        latest_by_sensor=latest_by_sensor,
        anomaly_count_window=anomaly_24h,
        critical_facility_anomaly_count=critical_anom,
        data_max_at=data_max,
    )
    
    # Energy, Water, and Waste summaries
    energy_ov = energy_service.get_energy_overview(CAMPUS_FEED_SENSOR_ID)
    water_ov = water_service.get_water_overview(MAIN_WATER_SENSOR_ID)
    waste_ov = waste_service.get_all_operational_waste_statuses()

    return {
        "facilities": facilities,
        "sensors": sensors,
        "data_max": data_max,
        "latest_by_sensor": latest_by_sensor,
        "anomaly_total": anomaly_total,
        "anomaly_24h": anomaly_24h,
        "anomalies": anomalies,
        "status": status,
        "critical_count": len(critical_ids),
        "energy_overview": energy_ov,
        "water_overview": water_ov,
        "waste_overview": waste_ov,
    }


def _kpi_row(ctx: dict) -> html.Div:
    sensors = ctx["sensors"]
    active = sum(1 for s in sensors if str(s.get("status") or "").upper() == "ACTIVE")
    
    e_ov = ctx.get("energy_overview", {})
    w_ov = ctx.get("water_overview", {})
    waste_list = ctx.get("waste_overview", [])
    
    # Calculate highest waste fill among monitored bins
    max_bin = None
    if waste_list:
        valid_bins = [b for b in waste_list if b.get("current_fill") is not None]
        if valid_bins:
            max_bin = max(valid_bins, key=lambda b: b["current_fill"])

    waste_val_str = max_bin["current_fill_formatted"] if max_bin else "N/A"
    waste_sub = (
        f"{max_bin['sensor_id']} ({max_bin['status']}) - {max_bin['facility_name']}"
        if max_bin
        else "Bins offline"
    )
    waste_tone = "critical" if (max_bin and max_bin.get("is_overflow")) else (
        "warning" if (max_bin and max_bin.get("alert_severity") in ("HIGH", "MEDIUM")) else "info"
    )

    feed_sub = (
        f"{CAMPUS_FEED_SENSOR_ID} • {e_ov['latest_timestamp_formatted']}"
        if e_ov.get("latest_timestamp")
        else f"{CAMPUS_FEED_SENSOR_ID} not found"
    )
    water_sub = (
        f"{MAIN_WATER_SENSOR_ID} • {w_ov['latest_timestamp_formatted']}"
        if w_ov.get("latest_timestamp")
        else f"{MAIN_WATER_SENSOR_ID} not found"
    )

    return html.Div(
        [
            kpi_card(
                "Monitored sensors",
                str(len(sensors)) if sensors else "0",
                subtitle=f"{active} active / {len(sensors)} total" if sensors else "No sensors returned",
                footnote="DATA SOURCE: sensors_dim",
            ),
            kpi_card(
                "Campus power demand",
                e_ov.get("current_val_formatted", "—"),
                unit="kW",
                subtitle=feed_sub,
                footnote="Latest SEN-023 reading only. Instantaneous demand.",
                tone="info",
            ),
            kpi_card(
                "Main water flow",
                w_ov.get("current_val_formatted", "—"),
                unit="L/min",
                subtitle=water_sub,
                footnote="Latest SEN-021 reading only. Main supply flow rate.",
                tone="info",
            ),
            kpi_card(
                "Peak waste bin",
                waste_val_str,
                subtitle=waste_sub,
                footnote="Operational WasteStatusEngine evaluation.",
                tone=waste_tone,
            ),
            kpi_card(
                "Active anomalies",
                format_number(ctx["anomaly_total"], digits=0) if ctx["anomaly_total"] is not None else "0",
                subtitle=f"{ctx['anomaly_24h']} in last 24h of dataset",
                footnote="sensor_readings_fact.is_anomaly = True",
                tone="warning" if ctx["anomaly_total"] else "neutral",
            ),
        ],
        className="iw-kpi-grid",
    )


def _status_panel(ctx: dict) -> html.Div:
    status = ctx["status"]
    return html.Div(
        [
            html.Div("Campus health (derived)", className="iw-section-kicker"),
            html.Div(
                [
                    html.Span(status["label"], className=f"iw-pill iw-pill-{status['tone']}"),
                    html.Span("Operational summary", className="iw-muted"),
                ],
                className="iw-status-head",
            ),
            html.Ul([html.Li(reason) for reason in status["reasons"]], className="iw-reason-list"),
            html.P(status["disclaimer"], className="iw-disclaimer"),
        ],
        className="iw-card",
    )


def layout() -> html.Div:
    return html.Div(
        [
            html.H1("Campus Overview", className="iw-page-title"),
            html.P(
                "Command center for campus infrastructure telemetry. Real-time metrics read directly from Supabase.",
                className="iw-page-lead",
            ),
            html.Div(id="overview-body", children=html.Div("Connecting to Supabase...", className="iw-muted")),
        ],
        className="iw-page",
    )


@callback(Output("overview-body", "children"), Input("overview-body", "id"))
def render_overview(_):
    state = supabase_service.check_connection()
    if not state.get("ok"):
        return html.Div(
            [
                _error_banner(state.get("message", "Unable to connect to Supabase.")),
                html.P("Displaying offline shell. Values are not fabricated.", className="iw-muted"),
                html.Div(
                    [
                        kpi_card("Monitored sensors", "Unavailable", subtitle="Database Offline"),
                        kpi_card("Campus power demand", "Unavailable", unit="kW", subtitle="Offline"),
                        kpi_card("Main water flow", "Unavailable", unit="L/min", subtitle="Offline"),
                        kpi_card("Peak waste bin", "Unavailable", subtitle="Offline"),
                        kpi_card("Active anomalies", "Unavailable", subtitle="Offline"),
                    ],
                    className="iw-kpi-grid",
                ),
            ]
        )
    try:
        ctx = _load_overview_context()
    except DataUnavailable as exc:

        return _error_banner(str(exc))
    except Exception as exc:
        return _error_banner(f"Unable to load Overview data: {exc}")

    data_max = parse_timestamptz(ctx["data_max"])
    now = datetime.now(tz=IST)
    banners = []
    if data_max is None:
        banners.append(_note_banner("No telemetry rows found in sensor_readings_fact."))
    else:
        lag_hours = (now - data_max).total_seconds() / 3600
        if lag_hours > 6:
            banners.append(
                _note_banner(
                    f"Dataset is historical. Last data point is {format_ist(data_max)} "
                    f"({lag_hours:.1f} hours behind current IST). "
                    "Time ranges are anchored to this data clock, not wall-clock time."
                )
            )

    metric_options = [{"label": spec["label"], "value": key} for key, spec in METRIC_CATALOG.items()]
    anomaly_rows = build_anomaly_rows(ctx["anomalies"], ctx["sensors"], ctx["facilities"])

    return html.Div(
        [
            *banners,
            _kpi_row(ctx),
            html.Div(
                [
                    _status_panel(ctx),
                    html.Div(
                        [
                            html.Div("Data clock", className="iw-section-kicker"),
                            html.H2(format_ist(ctx["data_max"]), className="iw-clock-value"),
                            html.P("Last data point = MAX(recorded_at) on sensor_readings_fact.", className="iw-muted"),
                            html.P(
                                "Anchors all historical ranges and prevents empty queries.",
                                className="iw-muted",
                            ),
                        ],
                        className="iw-card",
                    ),
                ],
                className="iw-split",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div("Resource trends", className="iw-section-kicker"),
                                    html.H2("Telemetry Stream", className="iw-section-title"),
                                ]
                            ),
                            html.Div(
                                [
                                    dcc.Dropdown(
                                        id="overview-metric",
                                        options=metric_options,
                                        value="power",
                                        clearable=False,
                                        className="iw-dropdown",
                                    ),
                                    dcc.Dropdown(
                                        id="overview-range",
                                        options=[
                                            {"label": "Last 24 hours of dataset", "value": "24h"},
                                            {"label": "Last 7 days of dataset", "value": "7d"},
                                            {"label": "Last 30 days of dataset", "value": "30d"},
                                        ],
                                        value="24h",
                                        clearable=False,
                                        className="iw-dropdown",
                                    ),
                                ],
                                className="iw-controls",
                            ),
                        ],
                        className="iw-section-head",
                    ),
                    html.P(
                        "Power displays SEN-023 campus feed. Water displays SEN-021 main supply flow.",
                        className="iw-muted",
                    ),
                    dcc.Loading(dcc.Graph(id="overview-chart", config={"displaylogo": False, "scrollZoom": True}), type="dot"),
                    html.P(id="overview-chart-note", className="iw-disclaimer"),
                ],
                className="iw-card iw-chart-card",
            ),
            html.Div(
                [
                    html.Div("Flagged readings", className="iw-section-kicker"),
                    html.H2("Recent Anomalies Feed", className="iw-section-title"),
                    html.P(
                        "Persisted anomaly classifications from sensor_readings_fact. Anomaly score is N/A when null.",
                        className="iw-muted",
                    ),
                    anomaly_table(anomaly_rows),
                ],
                className="iw-card",
            ),
        ]
    )


@callback(
    Output("overview-chart", "figure"),
    Output("overview-chart-note", "children"),
    Input("overview-metric", "value"),
    Input("overview-range", "value"),
    prevent_initial_call=True,
)
def update_chart(metric_key, range_key):
    metric_key = metric_key or "power"
    range_key = range_key or "24h"
    spec = METRIC_CATALOG.get(metric_key, METRIC_CATALOG["power"])
    
    hours_map = {"24h": 24.0, "7d": 168.0, "30d": 720.0}
    hours = hours_map.get(range_key, 24.0)

    # Determine sensor IDs
    all_sensors = supabase_service.fetch_sensors()
    if spec.get("sensor_ids"):
        wanted = set(spec["sensor_ids"])
        sensors = [s for s in all_sensors if s.get("sensor_id") in wanted]
    else:
        sensors = [s for s in all_sensors if s.get("sensor_type") == spec["sensor_type"]]

    if not sensors:
        return empty_figure("This metric is not present in sensors_dim."), "Not currently available in schema."

    # Fetch readings for selected sensors
    rows = []
    for s in sensors:
        sid = s["sensor_id"]
        df = supabase_service.fetch_recent_readings(sid, hours=hours, limit=1000)
        for _, r in df.iterrows():
            rows.append({
                "sensor_id": sid,
                "recorded_at": r["recorded_at"].isoformat() if hasattr(r["recorded_at"], "isoformat") else str(r["recorded_at"]),
                "reading_value": r["reading_value"],
                "is_anomaly": r.get("is_anomaly", False),
            })

    payload = {
        "spec": spec,
        "sensors": sensors,
        "rows": rows,
    }

    note = (
        f"DATA SOURCE: sensor_readings_fact. "
        f"Metric: {spec['label']} ({spec['unit']}). Total rows rendered: {len(rows)}."
    )
    return metric_timeseries(payload, range_key), note
