"""Compact KPI card used on Overview."""

from __future__ import annotations

from dash import html


def kpi_card(
    title: str,
    value: str,
    *,
    unit: str | None = None,
    subtitle: str | None = None,
    tone: str = "neutral",
    footnote: str | None = None,
) -> html.Div:
    unit_el = html.Span(unit, className="iw-kpi-unit") if unit else None
    return html.Div(
        [
            html.Div(title, className="iw-kpi-title"),
            html.Div(
                [html.Span(value, className="iw-kpi-value"), unit_el],
                className="iw-kpi-value-row",
            ),
            html.Div(subtitle or "", className="iw-kpi-sub"),
            html.Div(footnote or "", className="iw-kpi-note") if footnote else None,
        ],
        className=f"iw-card iw-kpi iw-kpi-{tone}",
    )
