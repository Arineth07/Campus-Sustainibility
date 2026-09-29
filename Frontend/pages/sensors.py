"""Placeholder route ? not implemented in this step."""

from __future__ import annotations

import dash
from components.placeholder import coming_soon

dash.register_page(__name__, path="/sensors", name="Sensors")


def layout():
    return coming_soon("Sensors")
