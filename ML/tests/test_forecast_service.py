"""
Unit tests for ML.forecasting.forecast_service validation logic and configs.
"""

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ML.forecasting.forecast_service import (
    SENSOR_CONFIGS,
    get_sensor_config,
    validate_forecast,
)


class TestForecastService(unittest.TestCase):
    def test_sensor_configs_integrity(self):
        """Verify all 5 target sensors have valid configuration dictionaries."""
        expected_sensors = {"SEN-023", "SEN-021", "SEN-013", "SEN-016", "SEN-019"}
        found_sensors = {cfg["sensor_id"] for cfg in SENSOR_CONFIGS}
        self.assertEqual(found_sensors, expected_sensors)

        for cfg in SENSOR_CONFIGS:
            self.assertIn(cfg["periods"], {96, 192})
            self.assertIn(cfg["sampling_interval_min"], {15, 30})
            self.assertIn(cfg["growth"], {"linear", "logistic"})

    def test_validate_forecast_success(self):
        """Verify validation passes on properly constructed forecast."""
        config = get_sensor_config("SEN-023")
        last_actual_ts = pd.Timestamp("2026-09-20 12:00:00")
        periods = config["periods"]
        interval = config["sampling_interval_min"]

        timestamps = [last_actual_ts + timedelta(minutes=(i + 1) * interval) for i in range(periods)]
        df = pd.DataFrame(
            {
                "ds": timestamps,
                "yhat": [500.0] * periods,
                "yhat_lower": [400.0] * periods,
                "yhat_upper": [600.0] * periods,
            }
        )

        # Should not raise
        validate_forecast(df, last_actual_ts, config)

    def test_validate_forecast_fails_if_empty(self):
        config = get_sensor_config("SEN-023")
        last_actual_ts = pd.Timestamp("2026-09-20 12:00:00")
        df = pd.DataFrame(columns=["ds", "yhat", "yhat_lower", "yhat_upper"])

        with self.assertRaises(ValueError):
            validate_forecast(df, last_actual_ts, config)

    def test_validate_forecast_fails_if_past_timestamp(self):
        config = get_sensor_config("SEN-023")
        last_actual_ts = pd.Timestamp("2026-09-20 12:00:00")
        # First point starts equal to last_actual_ts
        timestamps = [last_actual_ts + timedelta(minutes=i * 15) for i in range(192)]
        df = pd.DataFrame({"ds": timestamps, "yhat": [500.0] * 192})

        with self.assertRaises(ValueError):
            validate_forecast(df, last_actual_ts, config)

    def test_validate_forecast_fails_if_row_count_mismatch(self):
        config = get_sensor_config("SEN-023")
        last_actual_ts = pd.Timestamp("2026-09-20 12:00:00")
        # Only 50 rows instead of 192
        timestamps = [last_actual_ts + timedelta(minutes=(i + 1) * 15) for i in range(50)]
        df = pd.DataFrame({"ds": timestamps, "yhat": [500.0] * 50})

        with self.assertRaises(ValueError):
            validate_forecast(df, last_actual_ts, config)


if __name__ == "__main__":
    unittest.main()
