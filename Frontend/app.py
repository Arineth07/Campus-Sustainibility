"""InfraWatch AI - Campus Sustainability Dashboard Application Entry Point.

Plotly Dash multi-page application with persistent sidebar navigation,
header with live data clock freshness, and clean domain service integration.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Ensure paths are configured
_FRONTEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _FRONTEND_DIR.parent
for p in (str(_PROJECT_ROOT), str(_FRONTEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

import dash
from dash import Input, Output, dcc, html

from components.header import render_header
from components.sidebar import render_sidebar
from services import supabase_service
from utils.formatting import format_ist

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("dashboard_app")

# Initialize Dash application with Dash Pages enabled
app = dash.Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    title="InfraWatch AI - Campus Sustainability",
    update_title="Updating...",
)
server = app.server

# Shell Layout
app.layout = html.Div(
    [
        dcc.Location(id="_iw_url", refresh=False),
        html.Div(id="_iw_sidebar_container", children=render_sidebar("/")),
        html.Div(
            [
                render_header(),
                html.Main(dash.page_container, className="iw-main-content"),
            ],
            className="iw-main",
        ),
    ],
    className="iw-shell",
)


@app.callback(
    Output("_iw_sidebar_container", "children"),
    Input("_iw_url", "pathname"),
)
def update_active_nav(pathname: str | None):
    return render_sidebar(pathname)


@app.callback(
    Output("header-status-dot", "className"),
    Output("header-status-label", "children"),
    Output("header-last-data", "children"),
    Input("_iw_url", "pathname"),
)
def update_header_status(_):
    try:
        conn = supabase_service.check_connection()
        if not conn.get("ok"):
            return "iw-status-dot critical", "Offline / DB Error", "No connection"

        max_ts = supabase_service.fetch_max_recorded_at()
        if max_ts:
            ts_display = format_ist(max_ts, with_seconds=False)
            return "iw-status-dot", "Operational", f"Data Clock: {ts_display}"
        return "iw-status-dot warning", "No Readings", "Empty Fact Table"
    except Exception as exc:
        logger.error("Header status callback error: %s", exc)
        return "iw-status-dot critical", "Connection Failure", "Error"


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8050))
    logger.info("Starting InfraWatch AI Dash server on port %d...", port)
    if hasattr(app, "run"):
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        app.run_server(host="0.0.0.0", port=port, debug=False)

