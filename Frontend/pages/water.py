"""Water Infrastructure Page.

Displays campus water flow telemetry, supply monitoring,
and persisted 48-hour Prophet forecast models with prediction intervals.
"""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html

from components.charts import empty_figure, forecast_overlay_figure
from components.kpi_card import kpi_card
from services import water_service
from utils.constants import MAIN_WATER_SENSOR_ID
from utils.formatting import format_ist, format_number, format_range

dash.register_page(__name__, path="/water", name="Water")


def layout():
    water_sensors = water_service.get_water_sensors()
    sensor_options = [
        {"label": f"{s['sensor_id']} • {s['metric_measured']} ({s['facility_id']})", "value": s["sensor_id"]}
        for s in water_sensors
    ]
    if not sensor_options:
        sensor_options = [{"label": f"{MAIN_WATER_SENSOR_ID} • Main Supply Flow", "value": MAIN_WATER_SENSOR_ID}]

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H1("Water Infrastructure", className="iw-page-title"),
                            html.P(
                                "Campus main water supply flow and facility distribution monitoring. "
                                "Forecasts are read from persisted database records.",
                                className="iw-page-lead",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span("Select Sensor:", className="iw-control-label"),
                                    dcc.Dropdown(
                                        id="water-sensor-select",
                                        options=sensor_options,
                                        value=MAIN_WATER_SENSOR_ID,
                                        clearable=False,
                                        className="iw-dropdown",
                                        style={"minWidth": "280px"},
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Span("History Window:", className="iw-control-label"),
                                    dcc.Dropdown(
                                        id="water-window-select",
                                        options=[
                                            {"label": "24 Hours History", "value": 24.0},
                                            {"label": "48 Hours History", "value": 48.0},
                                            {"label": "7 Days History", "value": 168.0},
                                        ],
                                        value=48.0,
                                        clearable=False,
                                        className="iw-dropdown",
                                        style={"minWidth": "160px"},
                                    ),
                                ]
                            ),
                        ],
                        className="iw-controls",
                    ),
                ],
                className="iw-section-head",
            ),
            html.Div(id="water-kpi-container", className="iw-kpi-grid"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Forecast Model Overlay", className="iw-section-kicker"),
                            html.H2(id="water-chart-title", children="Water Telemetry vs 48-Hour Forecast", className="iw-section-title"),
                            html.P(
                                "Solid green represents historical flow rates; dashed cyan represents Prophet 48h predictions. "
                                "Shaded envelope indicates 80% uncertainty interval.",
                                className="iw-muted",
                            ),
                        ]
                    ),
                    dcc.Loading(
                        dcc.Graph(id="water-forecast-chart", config={"displaylogo": False, "scrollZoom": True}),
                        type="dot",
                    ),
                ],
                className="iw-card iw-chart-card",
            ),
            html.Div(id="water-meta-container"),
        ],
        className="iw-page",
    )


@callback(
    Output("water-kpi-container", "children"),
    Output("water-forecast-chart", "figure"),
    Output("water-chart-title", "children"),
    Output("water-meta-container", "children"),
    Input("water-sensor-select", "value"),
    Input("water-window-select", "value"),
)
def update_water_view(sensor_id, history_hours):
    sensor_id = sensor_id or MAIN_WATER_SENSOR_ID
    history_hours = float(history_hours or 48.0)

    try:
        data = water_service.get_water_history_and_forecast(sensor_id=sensor_id, history_hours=history_hours)
    except Exception as exc:
        empty_fig = empty_figure(f"Unable to load water data: {exc}")
        return [], empty_fig, "Error", html.Div(f"Query error: {exc}", className="iw-banner iw-banner-error")

    ov = data["overview"]
    history_df = data["history_df"]
    forecast_df = data["forecast_df"]

    curr_val = ov.get("current_val_formatted", "—")
    unit = ov.get("unit", "L/min")
    
    peak_hist = format_number(history_df["reading_value"].max(), digits=1) if not history_df.empty else "N/A"
    
    if not forecast_df.empty:
        peak_fc = format_number(forecast_df["predicted_value"].max(), digits=1)
        fc_status = f"{len(forecast_df)} forecast points loaded"
        fc_sub = f"Peak: {peak_fc} {unit}"
    else:
        fc_status = "Forecast unavailable"
        fc_sub = "Not generated for this sub-meter"

    anomaly_count = int(history_df["is_anomaly"].sum()) if not history_df.empty and "is_anomaly" in history_df.columns else 0

    kpis = [
        kpi_card(
            "Current Flow Rate",
            curr_val,
            unit=unit,
            subtitle=ov["latest_timestamp_formatted"],
            footnote=f"Facility: {ov['facility_name']}",
            tone="info",
        ),
        kpi_card(
            "Recent Peak Flow",
            peak_hist,
            unit=unit,
            subtitle=f"Within last {int(history_hours)}h window",
            footnote="Actual telemetry maximum",
        ),
        kpi_card(
            "48h Forecast Status",
            fc_status,
            subtitle=fc_sub,
            footnote="Persisted Prophet model output",
            tone="info" if not forecast_df.empty else "neutral",
        ),
        kpi_card(
            "Window Anomalies",
            str(anomaly_count),
            subtitle="Flagged in selected window",
            footnote="sensor_readings_fact.is_anomaly = True",
            tone="warning" if anomaly_count > 0 else "neutral",
        ),
    ]

    title = f"{ov['facility_name']} ({sensor_id}) — {ov['metric_name']}"
    chart_fig = forecast_overlay_figure(
        history_df=history_df,
        forecast_df=forecast_df,
        metric_name=ov["metric_name"],
        unit=unit,
        title=title,
    )

    meta_panel = html.Div(
        [
            html.Div(
                [
                    html.Div("Facility Specifications", className="iw-section-kicker"),
                    html.H3(ov["facility_name"], className="iw-section-title"),
                    html.P(f"Zone: {ov.get('zone', 'N/A')} • Facility ID: {ov.get('facility_id', 'N/A')}", className="iw-muted"),
                    html.P(
                        f"Expected Operating Bounds: {format_range(ov.get('normal_lower_bound'), ov.get('normal_upper_bound'), unit)}",
                        className="iw-muted",
                    ),
                ],
                className="iw-card",
            )
        ],
        className="iw-meta-grid",
    )

    return kpis, chart_fig, title, meta_panel
