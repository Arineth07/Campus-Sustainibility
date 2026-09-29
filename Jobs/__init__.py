"""Jobs package for campus sustainability scheduled tasks."""

from Jobs.forecast_job import run_forecast_pipeline

__all__ = ["run_forecast_pipeline"]
