"""
Campus Sustainability Dashboard - Machine Learning Runtime Package
===================================================================
Exports pure, database-agnostic ML forecasting and operational services:
- ML.forecasting.forecast_service
- ML.waste.waste_status_service
"""

from ML.forecasting.forecast_service import SENSOR_CONFIGS, train_and_forecast
from ML.waste.waste_status_service import WasteStatusEngine, WasteStatusResult

__all__ = [
    "SENSOR_CONFIGS",
    "train_and_forecast",
    "WasteStatusEngine",
    "WasteStatusResult",
]
