"""Plotly chart builders for Overview, Energy, Water, and Waste."""

from __future__ import annotations

from typing import Any
import pandas as pd
import plotly.graph_objects as go

from utils.formatting import parse_timestamptz

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, -apple-system, Segoe UI, sans-serif", color="#c5cdd8", size=12),
    margin=dict(l=56, r=24, t=36, b=48),
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False, showspikes=True),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zeroline=False, title_standoff=8),
)


def empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=14, color="#8b95a5"),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxis(visible=False)
    return fig


def metric_timeseries(payload: dict[str, Any], range_key: str) -> go.Figure:
    rows = payload.get("rows") or []
    spec = payload.get("spec") or {}
    sensors = {s["sensor_id"]: s for s in payload.get("sensors") or []}
    if not rows:
        return empty_figure("No readings in the selected window.")

    frame = pd.DataFrame(rows)
    frame["recorded_at"] = frame["recorded_at"].map(parse_timestamptz)
    frame = frame.dropna(subset=["recorded_at"])
    frame["reading_value"] = pd.to_numeric(frame["reading_value"], errors="coerce")
    frame = frame.dropna(subset=["reading_value"])
    if frame.empty:
        return empty_figure("No numeric readings in the selected window.")

    resample = range_key in {"7d", "30d", "full"}
    fig = go.Figure()
    for sensor_id, group in frame.groupby("sensor_id"):
        group = group.sort_values("recorded_at")
        if resample:
            indexed = group.set_index("recorded_at")["reading_value"].resample("1h").mean().dropna()
            x = indexed.index
            y = indexed.values
            name_suffix = " (hourly mean)"
        else:
            x = group["recorded_at"]
            y = group["reading_value"]
            name_suffix = ""
        meta = sensors.get(sensor_id, {})
        name = f"{sensor_id} • {meta.get('metric_measured', spec.get('label', sensor_id))}{name_suffix}"
        fig.add_trace(
            go.Scatter(
                x=list(x),
                y=list(y),
                mode="lines",
                name=name,
                line=dict(width=1.8),
                hovertemplate="%{x}<br>%{y:.2f} " + spec.get("unit", "") + "<extra>%{fullData.name}</extra>",
            )
        )

    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_yaxes(title=f"{spec.get('label', 'Value')} ({spec.get('unit', '')})")
    fig.update_xaxes(title="Time (IST)")
    fig.update_layout(
        xaxis_rangeslider_visible=False,
        dragmode="zoom",
    )
    return fig


def forecast_overlay_figure(
    history_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    metric_name: str,
    unit: str,
    title: str = "",
) -> go.Figure:
    """
    Renders historical actuals seamlessly joined with persisted Prophet forecast
    and 80% uncertainty bounds [lower_bound, upper_bound].
    """
    if history_df.empty and forecast_df.empty:
        return empty_figure("No telemetry or forecast data available.")

    fig = go.Figure()

    # 1. Uncertainty intervals (Forecast)
    if not forecast_df.empty and "lower_bound" in forecast_df.columns and "upper_bound" in forecast_df.columns:
        fig.add_trace(
            go.Scatter(
                x=forecast_df["forecast_horizon_at"],
                y=forecast_df["upper_bound"],
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=forecast_df["forecast_horizon_at"],
                y=forecast_df["lower_bound"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(56, 189, 248, 0.15)",
                name="Confidence Band",
                hoverinfo="skip",
            )
        )
        # Central forecast prediction
        fig.add_trace(
            go.Scatter(
                x=forecast_df["forecast_horizon_at"],
                y=forecast_df["predicted_value"],
                mode="lines",
                line=dict(color="#38bdf8", width=2.5, dash="dash"),
                name="48h Prophet Forecast",
                hovertemplate="%{x}<br>Forecast: <b>%{y:.2f} " + unit + "</b><extra></extra>",
            )
        )

    # 2. Historical actual telemetry
    if not history_df.empty:
        fig.add_trace(
            go.Scatter(
                x=history_df["recorded_at"],
                y=history_df["reading_value"],
                mode="lines",
                line=dict(color="#10b981", width=2),
                name="Historical Actuals",
                hovertemplate="%{x}<br>Actual: <b>%{y:.2f} " + unit + "</b><extra></extra>",
            )
        )

        # Anomaly markers if any
        if "is_anomaly" in history_df.columns:
            anom_df = history_df[history_df["is_anomaly"] == True]
            if not anom_df.empty:
                fig.add_trace(
                    go.Scatter(
                        x=anom_df["recorded_at"],
                        y=anom_df["reading_value"],
                        mode="markers",
                        marker=dict(color="#f43f5e", size=8, symbol="diamond"),
                        name="Anomaly",
                        hovertemplate="%{x}<br>Flagged Anomaly: <b>%{y:.2f} " + unit + "</b><extra></extra>",
                    )
                )

    # 3. Vertical boundary line between actuals and forecast
    if not history_df.empty and not forecast_df.empty:
        split_dt = history_df["recorded_at"].max()
        fig.add_vline(
            x=split_dt,
            line_width=1.5,
            line_dash="dot",
            line_color="rgba(255, 255, 255, 0.4)",
            annotation_text="Forecast Horizon",
            annotation_position="top left",
            annotation_font=dict(color="#94a3b8", size=10),
        )

    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#f1f5f9")) if title else None,
        yaxis=dict(
            title=f"{metric_name} ({unit})",
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
        ),
        xaxis=dict(
            title="Time (IST)",
            gridcolor="rgba(255,255,255,0.06)",
            zeroline=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
            bgcolor="rgba(0,0,0,0)",
        ),
        dragmode="zoom",
    )
    return fig
