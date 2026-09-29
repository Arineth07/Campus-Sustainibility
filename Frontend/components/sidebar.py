"""Persistent sidebar navigation."""

from __future__ import annotations

from dash import dcc, html

from utils.constants import NAV_ITEMS


def render_sidebar(pathname: str | None = None) -> html.Aside:
    current = pathname or "/"
    links = []
    for item in NAV_ITEMS:
        active = current.rstrip("/") == item["path"].rstrip("/") or (
            item["path"] == "/" and current in {"", "/"}
        )
        links.append(
            dcc.Link(
                item["label"],
                href=item["path"],
                className="iw-nav-link" + (" is-active" if active else ""),
            )
        )
    return html.Aside(
        [
            html.Div(
                [
                    html.Div("IW", className="iw-mark"),
                    html.Div(
                        [
                            html.Div("InfraWatch AI", className="iw-brand"),
                            html.Div("Operations", className="iw-brand-sub"),
                        ]
                    ),
                ],
                className="iw-brand-row",
            ),
            html.Nav(links, className="iw-nav"),
        ],
        className="iw-sidebar",
    )
