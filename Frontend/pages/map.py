"""Campus Geographic & Sensor Map Page.

Plots all 12 facilities using coordinates from facilities_dim,
overlaying live operational status, sensor summaries, and anomaly flags.
Does not fabricate building geometry.
"""

from __future__ import annotations

import dash
from dash import Input, Output, callback, dcc, html
import plotly.graph_objects as go

from components.charts import empty_figure
from components.kpi_card import kpi_card
from services import map_service

dash.register_page(__name__, path="/map", name="Campus Map")


def _build_map_figure(facilities: list[dict]) -> go.Figure:
    if not facilities:
        return empty_figure("No facility coordinate data found in facilities_dim.")

    scatter_cls = getattr(go, "Scattermap", None) or getattr(go, "Scattermapbox", None)
    if scatter_cls is None:
        return empty_figure("Plotly map components not available in this environment.")

    lats = [f["latitude"] for f in facilities]
    lons = [f["longitude"] for f in facilities]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)

    fig = go.Figure()

    # Group by status tone for clean legend
    tone_configs = {
        "nominal": {"name": "Nominal Status", "color": "#10b981", "symbol": "circle"},
        "warning": {"name": "Warning / Anomalies", "color": "#f59e0b", "symbol": "circle"},
        "critical": {"name": "Critical Infrastructure Alert", "color": "#f43f5e", "symbol": "circle"},
    }

    for tone, cfg in tone_configs.items():
        subset = [f for f in facilities if f["status_tone"] == tone]
        if not subset:
            continue

        hover_texts = []
        for f in subset:
            crit_badge = " [CRITICAL INFRASTRUCTURE]" if f["is_critical"] else ""
            txt = (
                f"<b>{f['facility_name']} ({f['facility_id']})</b>{crit_badge}<br>"
                f"Zone: {f['zone']} | Type: {f['facility_type']}<br>"
                f"Status: <b>{f['status_label']}</b><br>"
                f"Operating Hours: {f['operating_hours']}<br>"
                f"Sensors ({f['sensors_count']}):<br>{f['sensors_summary']}"
            )
            hover_texts.append(txt)

        fig.add_trace(
            scatter_cls(
                lat=[f["latitude"] for f in subset],
                lon=[f["longitude"] for f in subset],
                mode="markers+text",
                marker=dict(
                    size=16,
                    color=cfg["color"],
                    opacity=0.9,
                ),
                text=[f["facility_name"] for f in subset],
                textposition="top center",
                textfont=dict(size=11, color="#f1f5f9"),
                name=cfg["name"],
                hoverinfo="text",
                hovertext=hover_texts,
            )
        )

    # Apply dark carto map styling
    map_layout_args = dict(
        style="carto-darkmatter",
        center=dict(lat=center_lat, lon=center_lon),
        zoom=15.2,
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, -apple-system, Segoe UI, sans-serif", color="#c5cdd8", size=12),
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.02,
            x=0.02,
            bgcolor="rgba(16, 22, 34, 0.85)",
            bordercolor="rgba(255, 255, 255, 0.1)",
            borderwidth=1,
            font=dict(color="#f1f5f9", size=11),
        ),
    )

    # Accommodate both layout.map and layout.mapbox depending on Plotly version
    if hasattr(fig.layout, "map"):
        fig.update_layout(map=map_layout_args)
    else:
        fig.update_layout(mapbox=map_layout_args)

    return fig


def layout():
    return html.Div(
        [
            html.Div(
                [
                    html.H1("Campus Geographic & Sensor Map", className="iw-page-title"),
                    html.P(
                        "Interactive spatial view of campus facilities. Coordinates and operational "
                        "telemetry are retrieved directly from facilities_dim and sensor_readings_fact.",
                        className="iw-page-lead",
                    ),
                ]
            ),
            html.Div(id="map-kpi-container", className="iw-kpi-grid"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div("Spatial Telemetry View", className="iw-section-kicker"),
                                    html.H2("Campus Facilities & Infrastructure Network", className="iw-section-title"),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Span("Filter Zone:", className="iw-control-label"),
                                    dcc.Dropdown(
                                        id="map-zone-filter",
                                        options=[
                                            {"label": "All Campus Zones", "value": "ALL"},
                                            {"label": "Academic/Admin", "value": "Academic/Admin"},
                                            {"label": "Residential", "value": "Residential"},
                                            {"label": "Dining/Utility", "value": "Dining/Utility"},
                                            {"label": "Transit/Perimeter", "value": "Transit/Perimeter"},
                                        ],
                                        value="ALL",
                                        clearable=False,
                                        className="iw-dropdown",
                                        style={"minWidth": "220px"},
                                    ),
                                ],
                                className="iw-controls",
                            ),
                        ],
                        className="iw-section-head",
                    ),
                    dcc.Loading(
                        dcc.Graph(
                            id="campus-map-graph",
                            style={"height": "560px", "borderRadius": "8px", "overflow": "hidden"},
                            config={"displaylogo": False, "scrollZoom": True},
                        ),
                        type="dot",
                    ),
                ],
                className="iw-card iw-map-card",
            ),
            html.Div(
                [
                    html.Div("Facilities Inventory", className="iw-section-kicker"),
                    html.H2("Campus Infrastructure Registry", className="iw-section-title"),
                    html.P(
                        "Verified coordinates from facilities_dim (Pune Campus reference ~18.52° N, 73.856° E).",
                        className="iw-muted",
                    ),
                    html.Div(id="facilities-table-container"),
                ],
                className="iw-card",
            ),
        ],
        className="iw-page",
    )


@callback(
    Output("map-kpi-container", "children"),
    Output("campus-map-graph", "figure"),
    Output("facilities-table-container", "children"),
    Input("map-zone-filter", "value"),
)
def update_map_view(zone_filter):
    try:
        all_facs = map_service.get_map_facilities_data()
    except Exception as exc:
        empty_fig = empty_figure(f"Unable to load map data: {exc}")
        return [], empty_fig, html.Div(f"Query error: {exc}", className="iw-banner iw-banner-error")

    total_facs = len(all_facs)
    critical_facs = sum(1 for f in all_facs if f.get("is_critical"))
    anom_facs = sum(1 for f in all_facs if f.get("anomaly_count", 0) > 0)
    total_sensors = sum(f.get("sensors_count", 0) for f in all_facs)

    kpis = [
        kpi_card("Total Facilities", str(total_facs), subtitle="Monitored sites", tone="info"),
        kpi_card("Critical Infrastructure", str(critical_facs), subtitle="24x7 Critical operations", tone="info"),
        kpi_card("Facilities with Anomalies", str(anom_facs), subtitle="Requires inspection", tone="warning" if anom_facs else "neutral"),
        kpi_card("Connected Sensors", str(total_sensors), subtitle="Total deployed", tone="neutral"),
    ]

    # Filter by zone if selected
    if zone_filter and zone_filter != "ALL":
        filtered_facs = [f for f in all_facs if f.get("zone") == zone_filter]
    else:
        filtered_facs = all_facs

    fig = _build_map_figure(filtered_facs)

    # Render a clean grid of facility cards
    cards = []
    for f in filtered_facs:
        pill_class = f"iw-pill iw-pill-{f['status_tone']}"
        crit_tag = html.Span("CRITICAL", className="iw-pill iw-pill-critical", style={"fontSize": "10px", "marginLeft": "6px"}) if f["is_critical"] else None
        
        cards.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.H4(f["facility_name"], style={"color": "#f1f5f9", "fontSize": "14px", "fontWeight": "600"}),
                            html.Span(f["facility_id"], className="iw-muted", style={"fontSize": "12px"}),
                        ],
                        style={"display": "flex", "justifyContent": "space-between", "alignItems": "baseline"},
                    ),
                    html.Div(
                        [
                            html.Span(f["status_label"], className=pill_class),
                            crit_tag,
                        ],
                        style={"marginTop": "8px", "marginBottom": "8px"},
                    ),
                    html.P(f"Zone: {f['zone']} • Type: {f['facility_type']}", className="iw-muted", style={"fontSize": "12px"}),
                    html.P(f"Coordinates: {f['latitude']:.4f}° N, {f['longitude']:.4f}° E", className="iw-disclaimer"),
                    html.P(f"Sensors: {f['sensors_count']} active • Hours: {f['operating_hours']}", className="iw-disclaimer"),
                ],
                className="iw-card",
                style={"padding": "16px"},
            )
        )

    grid = html.Div(cards, style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(280px, 1fr))", "gap": "16px", "marginTop": "16px"})
    return kpis, fig, grid
