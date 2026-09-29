"""
Unit tests for ML.waste.waste_status_service.WasteStatusEngine.
Verifies operational state machine, rate calculation, surge detection, and guardrails.
"""

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ML.waste.waste_status_service import WasteStatusEngine, WasteStatusResult


def _make_series(values: list[float], interval_min: int = 30) -> pd.DataFrame:
    base_time = datetime(2026, 9, 20, 8, 0)
    rows = []
    for i, v in enumerate(values):
        rows.append(
            {
                "recorded_at": base_time + timedelta(minutes=i * interval_min),
                "reading_value": float(v),
            }
        )
    return pd.DataFrame(rows)


class TestWasteStatusEngine(unittest.TestCase):
    def test_insufficient_data(self):
        engine = WasteStatusEngine()
        df = _make_series([40.0, 42.0])  # only 2 readings
        res = engine.evaluate(df, sensor_id="SEN-013", facility_id="FAC-06")

        self.assertEqual(res.projection_state, "INSUFFICIENT_DATA")
        self.assertIsNone(res.fill_rate_pph)
        self.assertIsNone(res.projected_fill_1h)
        self.assertIsNone(res.projected_fill_3h)

    def test_normal_accumulation(self):
        engine = WasteStatusEngine()
        # Steady fill of +1.0 pp per 30 min (2.0 pp/hr)
        df = _make_series([40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0])
        res = engine.evaluate(df, sensor_id="SEN-013", facility_id="FAC-06")

        self.assertEqual(res.status, "Normal")
        self.assertEqual(res.alert_severity, "LOW")
        self.assertEqual(res.current_fill, 46.0)
        self.assertEqual(res.fill_rate_pph, 2.0)
        self.assertEqual(res.projected_fill_1h, 48.0)
        self.assertEqual(res.projected_fill_3h, 52.0)
        self.assertFalse(res.surge_detected)
        self.assertEqual(res.projection_state, "VALID")

    def test_pickup_soon_and_pickup_required(self):
        engine = WasteStatusEngine()
        # At 75% -> Pickup Soon
        df_soon = _make_series([68.0, 70.0, 72.0, 73.5, 75.0])
        res_soon = engine.evaluate(df_soon)
        self.assertEqual(res_soon.status, "Pickup Soon")
        self.assertEqual(res_soon.alert_severity, "MEDIUM")

        # At 86% -> Pickup Required / Already Full
        df_req = _make_series([80.0, 82.0, 84.0, 85.0, 86.0])
        res_req = engine.evaluate(df_req)
        self.assertEqual(res_req.status, "Pickup Required")
        self.assertEqual(res_req.alert_severity, "HIGH")
        self.assertEqual(res_req.projection_state, "ALREADY_FULL")
        self.assertIsNone(res_req.projected_fill_1h)

    def test_overflow_unclipped(self):
        engine = WasteStatusEngine()
        # Value > 100% (e.g. 104.5%)
        df = _make_series([88.0, 92.0, 95.0, 99.0, 104.5])
        res = engine.evaluate(df)

        self.assertEqual(res.current_fill, 104.5)
        self.assertEqual(res.status, "Overflowing")
        self.assertEqual(res.alert_severity, "CRITICAL")
        self.assertEqual(res.projection_state, "OVERFLOWING")
        self.assertIsNone(res.projected_fill_1h)

    def test_surge_detection_suspends_projection(self):
        engine = WasteStatusEngine(surge_threshold=15.0)
        # Jump of +20 pp over 30 minutes
        df = _make_series([30.0, 31.0, 32.0, 33.0, 53.0])
        res = engine.evaluate(df)

        self.assertTrue(res.surge_detected)
        self.assertEqual(res.surge_magnitude, 20.0)
        self.assertEqual(res.projection_state, "UNSTABLE_SURGE")
        self.assertIsNone(res.projected_fill_1h)
        self.assertIsNone(res.projected_fill_3h)

    def test_emptying_detection(self):
        engine = WasteStatusEngine(emptying_threshold=-20.0)
        # Drop of -65 pp down to 5%
        df = _make_series([60.0, 64.0, 68.0, 70.0, 5.0])
        res = engine.evaluate(df)

        self.assertTrue(res.emptying_detected)
        self.assertEqual(res.emptying_magnitude, 65.0)
        self.assertEqual(res.projection_state, "EMPTYING_RESET")
        self.assertEqual(res.projected_fill_1h, 5.0)
        self.assertEqual(res.projected_fill_3h, 5.0)

    def test_stagnant_fill_rate(self):
        engine = WasteStatusEngine()
        # Flat reading
        df = _make_series([50.0, 50.0, 50.0, 50.0, 50.0, 50.0])
        res = engine.evaluate(df)

        self.assertEqual(res.projection_state, "STAGNANT_RATE")
        self.assertEqual(res.fill_rate_pph, 0.0)
        self.assertEqual(res.projected_fill_1h, 50.0)
        self.assertEqual(res.projected_fill_3h, 50.0)


if __name__ == "__main__":
    unittest.main()
