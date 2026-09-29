"""Application header with data-clock freshness (not wall-clock time)."""

from __future__ import annotations

from dash import html


def render_header() -> html.Header:
    return html.Header(
        [
            html.Div(
                [
                    html.H1("InfraWatch AI", className="iw-header-title"),
                    html.P(
                        "Campus Sustainability & Infrastructure Monitoring",
                        className="iw-header-sub",
                    ),
                ]
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(className="iw-status-dot", id="header-status-dot"),
                            html.Span(id="header-status-label", children="Checking data?"),
                        ],
                        className="iw-status-pill",
                    ),
                    html.Div(id="header-last-data", className="iw-header-meta"),
                ],
                className="iw-header-right",
            ),
        ],
        className="iw-header",
    )
