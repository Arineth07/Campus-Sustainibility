"""Waste Operations & Bin Monitoring Page.

Real-time operational fill monitoring, median fill-rate estimation,
and short-horizon (1h / 3h) projections evaluated via WasteStatusEngine.
Strictly avoids misleading long-term countdown-to-85% predictions.
"""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html
import plotly.graph_objects as go

from components.charts import PLOTLY_LAYOUT, empty_figure
from components.kpi_card import kpi_card
from services import waste_service
from utils.formatting import format_ist, format_number

dash.register_page(__name__, path="/waste", name="Waste Operations")


def _render_bin_card(bin_data: dict) -> html.Div:
    fill = bin_data["current_fill"]
    fill_pct = min(fill, 100.0) if fill is not None else 0.0
    is_overflow = bin_data.get("is_overflow", False)
    
    # Gauge class
    if is_overflow or (fill and fill > 100.0):
        gauge_class = "iw-gauge-bar-fill iw-gauge-critical"
        status_pill_class = "iw-pill iw-pill-critical"
    elif fill and fill >= 85.0:
        gauge_class = "iw-gauge-bar-fill iw-gauge-critical"
        status_pill_class = "iw-pill iw-pill-critical"
    elif fill and fill >= 70.0:
        gauge_class = "iw-gauge-bar-fill iw-gauge-warning"
        status_pill_class = "iw-pill iw-pill-warning"
    else:
        gauge_class = "iw-gauge-bar-fill iw-gauge-normal"
        status_pill_class = "iw-pill iw-pill-normal"

    card_class = "iw-waste-card" + (" is-overflow" if is_overflow else "")

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(bin_data["sensor_id"], className="iw-section-kicker"),
                            html.H3(bin_data["facility_name"], className="iw-section-title"),
                            html.Span(bin_data.get("zone", "Campus"), className="iw-muted"),
                        ]
                    ),
                    html.Span(f"{bin_data['status']} ({bin_data['alert_severity']})", className=status_pill_class),
                ],
                style={"display": "flex", "justifyContent": "space-between", "alignItems": "flex-start"},
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span("Current Fill Level", className="iw-waste-metric-label"),
                            html.Span(bin_data["current_fill_formatted"], className="iw-kpi-value"),
                        ],
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "baseline"},
                    ),
                    html.Div(
                        html.Div(style={"width": f"{fill_pct}%"}, className=gauge_class),
                        className="iw-gauge-bar-bg",
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Fill Rate (3h)", className="iw-waste-metric-label"),
                            html.Div(bin_data["fill_rate_formatted"], className="iw-waste-metric-val"),
                        ]
                    ),
                    html.Div(
                        [
                            html.Div("Projection State", className="iw-waste-metric-label"),
                            html.Div(bin_data["projection_state"], className="iw-waste-metric-val"),
                        ]
                    ),
                    html.Div(
                        [
                            html.Div("1-Hour Projection", className="iw-waste-metric-label"),
                            html.Div(bin_data["projected_fill_1h_formatted"], className="iw-waste-metric-val"),
                        ]
                    ),
                    html.Div(
                        [
                            html.Div("3-Hour Projection", className="iw-waste-metric-label"),
                            html.Div(bin_data["projected_fill_3h_formatted"], className="iw-waste-metric-val"),
                        ]
                    ),
                ],
                className="iw-waste-metrics",
            ),
            html.Div(
                [
                    html.P(f"• Surge detected: {'YES' if bin_data['surge_detected'] else 'None'}", className="iw-muted"),
                    html.P(f"• Emptying reset: {'YES' if bin_data['emptying_detected'] else 'None'}", className="iw-muted"),
                    html.P(f"• Latest Reading: {bin_data['timestamp_formatted']}", className="iw-disclaimer"),
                ]
            ),
        ],
        className=card_class,
    )


def layout():
    sensor_options = [
        {"label": f"{c['sensor_id']} • {c['facility_name']}", "value": c["sensor_id"]}
        for c in waste_service.get_waste_sensor_configs()
    ]

    return html.Div(
        [
            html.Div(
                [
                    html.H1("Waste Operations & Bin Monitoring", className="iw-page-title"),
                    html.P(
                        "Real-time operational fill levels, median fill-rate estimation, and short-horizon (1h / 3h) "
                        "projections using the operational WasteStatusEngine. Unclipped overflow readings remain visible.",
                        className="iw-page-lead",
                    ),
                ]
            ),
            html.Div(id="waste-cards-container", className="iw-waste-grid"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div("Telemetry Deep Dive", className="iw-section-kicker"),
                                    html.H2("Bin Fill History & Operational Thresholds", className="iw-section-title"),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Span("Select Bin:", className="iw-control-label"),
                                            dcc.Dropdown(
                                                id="waste-sensor-select",
                                                options=sensor_options,
                                                value="SEN-013",
                                                clearable=False,
                                                className="iw-dropdown",
                                                style={"minWidth": "260px"},
                                            ),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            html.Span("History Window:", className="iw-control-label"),
                                            dcc.Dropdown(
                                                id="waste-window-select",
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
                    dcc.Loading(
                        dcc.Graph(id="waste-trend-chart", config={"displaylogo": False, "scrollZoom": True}),
                        type="dot",
                    ),
                    html.Div(
                        [
                            html.H4("Operational Guardrails & Semantics", style={"color": "#94a3b8", "marginBottom": "6px"}),
                            html.P(
                                "• < 70%: Normal (LOW) | 70–84.9%: Pickup Soon (MEDIUM) | 85–100%: Pickup Required (HIGH) | > 100%: Overflowing (CRITICAL)",
                                className="iw-disclaimer",
                            ),
                            html.P(
                                "• Projection states: VALID, UNSTABLE_SURGE (projections suspended during sudden disposal bursts), "
                                "EMPTYING_RESET (projections paused after bin is emptied), STAGNANT_RATE, ALREADY_FULL, OVERFLOWING.",
                                className="iw-disclaimer",
                            ),
                        ],
                        style={"marginTop": "16px", "paddingTop": "12px", "borderTop": "1px solid rgba(255,255,255,0.06)"},
                    ),
                ],
                className="iw-card iw-chart-card",
            ),
        ],
        className="iw-page",
    )


@callback(
    Output("waste-cards-container", "children"),
    Input("waste-cards-container", "id"),
)
def render_waste_cards(_):
    try:
        bins = waste_service.get_all_operational_waste_statuses()
        return [_render_bin_card(b) for b in bins]
    except Exception as exc:
        return html.Div(f"Unable to load waste operational statuses: {exc}", className="iw-banner iw-banner-error")


@callback(
    Output("waste-trend-chart", "figure"),
    Input("waste-sensor-select", "value"),
    Input("waste-window-select", "value"),
)
def update_waste_chart(sensor_id, history_hours):
    sensor_id = sensor_id or "SEN-013"
    history_hours = float(history_hours or 48.0)

    try:
        history_df = waste_service.get_waste_history(sensor_id, hours=history_hours)
    except Exception as exc:
        return empty_figure(f"Unable to load history: {exc}")

    if history_df.empty:
        return empty_figure("No waste fill readings in selected window.")

    fig = go.Figure()

    # Add threshold reference lines
    fig.add_hline(
        y=70,
        line_dash="dot",
        line_color="#f59e0b",
        annotation_text="Warning (70%)",
        annotation_position="top right",
        annotation_font=dict(color="#f59e0b", size=10),
    )
    fig.add_hline(
        y=85,
        line_dash="dash",
        line_color="#f43f5e",
        annotation_text="Critical (85%)",
        annotation_position="top right",
        annotation_font=dict(color="#f43f5e", size=10),
    )
    fig.add_hline(
        y=100,
        line_dash="solid",
        line_color="#e11d48",
        annotation_text="Overflow (100%)",
        annotation_position="top right",
        annotation_font=dict(color="#e11d48", size=10),
    )

    # Actual readings
    fig.add_trace(
        go.Scatter(
            x=history_df["recorded_at"],
            y=history_df["reading_value"],
            mode="lines+markers",
            marker=dict(size=4),
            line=dict(color="#38bdf8", width=2),
            name="Bin Fill Level (%)",
            hovertemplate="%{x}<br>Fill: <b>%{y:.1f}%</b><extra></extra>",
        )
    )

    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(
        yaxis=dict(
            title="Bin Fill Level (%)",
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
        ),
        xaxis=dict(
            title="Time (IST)",
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
        ),
        dragmode="zoom",
    )
    return fig
