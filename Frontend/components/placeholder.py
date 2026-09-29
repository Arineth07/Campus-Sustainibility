"""Placeholder page body for routes not implemented in this step."""

from __future__ import annotations

from dash import html


def coming_soon(page_title: str) -> html.Div:
    return html.Div(
        [
            html.H1(page_title, className="iw-page-title"),
            html.Div(
                [
                    html.P("Coming soon", className="iw-coming-title"),
                    html.P(
                        "This section is reserved in the shell and will be implemented after Overview is confirmed.",
                        className="iw-muted",
                    ),
                ],
                className="iw-card iw-coming-soon",
            ),
        ],
        className="iw-page",
    )
