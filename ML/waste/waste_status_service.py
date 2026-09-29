"""
Campus Sustainability Dashboard - Waste Operational Status Engine
==================================================================
Lightweight, robust, and interpretable operational engine for campus waste bin monitoring.
Provides real-time operational status, surge detection, robust median fill-rate estimation,
and short-horizon (1h and 3h) fill projections without reliance on continuous regression models.

Sensors Supported:
- SEN-013: Boys' Hostel Block 1 (FAC-06)
- SEN-016: Girls' Hostel Block 1 (FAC-07)
- SEN-019: Central Mess & Canteen (FAC-08)

Architectural Guarantees:
- Database-agnostic: Pure Python, NumPy, Pandas. No Supabase or database dependencies.
- Environment-agnostic: No .env loading, no credential dependencies.
- Operates independently from Prophet macro-baseline forecasts.
- Strictly does NOT implement a misleading time-to-85% countdown.
"""

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger("waste_status_service")


@dataclass
class WasteStatusResult:
    """Standardized operational output for a single waste bin reading."""
    sensor_id: str
    facility_id: str
    timestamp: str
    current_fill: float
    status: str                    # "Normal", "Pickup Soon", "Pickup Required", "Overflowing"
    alert_severity: str            # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    fill_rate_pph: Optional[float] # Percentage points per hour (3h median)
    projected_fill_1h: Optional[float]
    projected_fill_3h: Optional[float]
    surge_detected: bool
    surge_magnitude: Optional[float]
    emptying_detected: bool
    emptying_magnitude: Optional[float]
    projection_state: str          # "VALID", "UNSTABLE_SURGE", "EMPTYING_RESET", "STAGNANT_RATE", "ALREADY_FULL", "OVERFLOWING", "INSUFFICIENT_DATA"
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WasteStatusEngine:
    """
    Operational status engine for campus waste bins.
    Calculates current state, surge events, 3h median fill-rate, and 1h/3h projections.
    """

    def __init__(
        self,
        warning_threshold: float = 70.0,
        critical_threshold: float = 85.0,
        overflow_threshold: float = 100.0,
        surge_threshold: float = 15.0,
        emptying_threshold: float = -20.0,
        lookback_hours: float = 3.0,
        sampling_interval_min: int = 30,
    ):
        self.warning_threshold = float(warning_threshold)
        self.critical_threshold = float(critical_threshold)
        self.overflow_threshold = float(overflow_threshold)
        self.surge_threshold = float(surge_threshold)
        self.emptying_threshold = float(emptying_threshold)
        self.lookback_hours = float(lookback_hours)
        self.sampling_interval_min = int(sampling_interval_min)

        # Expected readings in lookback window (e.g., 3h / 0.5h = 6 intervals)
        self.lookback_steps = int(round(self.lookback_hours * (60.0 / self.sampling_interval_min)))

    def evaluate(
        self,
        history_df: pd.DataFrame,
        sensor_id: str = "SEN-013",
        facility_id: str = "FAC-06",
    ) -> WasteStatusResult:
        """
        Evaluates the current operational status and short-horizon projection
        given a dataframe of historical readings up to the current timestamp.
        """
        if history_df.empty:
            return WasteStatusResult(
                sensor_id=sensor_id,
                facility_id=facility_id,
                timestamp="N/A",
                current_fill=0.0,
                status="Unknown",
                alert_severity="LOW",
                fill_rate_pph=None,
                projected_fill_1h=None,
                projected_fill_3h=None,
                surge_detected=False,
                surge_magnitude=None,
                emptying_detected=False,
                emptying_magnitude=None,
                projection_state="INSUFFICIENT_DATA",
                notes="History dataframe is empty.",
            )

        latest_row = history_df.iloc[-1]
        raw_val = float(latest_row["reading_value"])
        current_fill = round(raw_val, 2)  # Strictly UNCLIPPED

        # Format timestamp
        ts = latest_row["recorded_at"]
        if hasattr(ts, "isoformat"):
            ts_str = ts.isoformat()
        else:
            ts_str = str(ts)

        # 1. Operational Status & Severity
        if current_fill > self.overflow_threshold:
            status = "Overflowing"
            severity = "CRITICAL"
        elif current_fill >= self.critical_threshold:
            status = "Pickup Required"
            severity = "HIGH"
        elif current_fill >= self.warning_threshold:
            status = "Pickup Soon"
            severity = "MEDIUM"
        else:
            status = "Normal"
            severity = "LOW"

        # 2. Event Detection: Differences
        n_rows = len(history_df)
        diff_series = history_df["reading_value"].diff()

        last_diff = float(diff_series.iloc[-1]) if n_rows >= 2 and pd.notna(diff_series.iloc[-1]) else 0.0

        # Surge detection (delta >= surge_threshold)
        surge_detected = bool(last_diff >= self.surge_threshold)
        surge_magnitude = round(last_diff, 2) if surge_detected else None

        # Emptying detection (delta <= emptying_threshold AND current_fill <= 15.0%)
        emptying_detected = bool(last_diff <= self.emptying_threshold and current_fill <= 15.0)
        emptying_magnitude = round(abs(last_diff), 2) if emptying_detected else None

        # Check if an unresolved surge occurred within the last 1 hour (last 2 readings)
        recent_surge_active = False
        if n_rows >= 2:
            recent_2_diffs = diff_series.iloc[-2:]
            recent_surge_active = bool((recent_2_diffs >= self.surge_threshold).any())

        # 3. History Length Guardrail
        if n_rows < 3:
            return WasteStatusResult(
                sensor_id=sensor_id,
                facility_id=facility_id,
                timestamp=ts_str,
                current_fill=current_fill,
                status=status,
                alert_severity=severity,
                fill_rate_pph=None,
                projected_fill_1h=None,
                projected_fill_3h=None,
                surge_detected=surge_detected,
                surge_magnitude=surge_magnitude,
                emptying_detected=emptying_detected,
                emptying_magnitude=emptying_magnitude,
                projection_state="INSUFFICIENT_DATA",
                notes="Fewer than 3 readings available in sensor telemetry.",
            )

        # 4. Robust Median Rate over Lookback Window (3 Hours)
        window = history_df.iloc[-self.lookback_steps :]
        window_diffs = window["reading_value"].diff().dropna()

        # Convert step deltas to hourly rates (delta * (60 / interval))
        hourly_multiplier = 60.0 / self.sampling_interval_min
        step_hourly_rates = window_diffs * hourly_multiplier

        # Exclude large drops caused by emptyings (< -20 pp/interval) so they do not distort rate
        clean_rates = step_hourly_rates[step_hourly_rates > -30.0]
        if clean_rates.empty:
            median_rate = 0.0
        else:
            median_rate = float(np.median(clean_rates))
        median_rate = round(median_rate, 2)

        # 5. Projection Validity & Guardrail Evaluation
        if surge_detected or recent_surge_active:
            proj_state = "UNSTABLE_SURGE"
            proj_1h = None
            proj_3h = None
            rate_exposed = None
            notes = f"Disposal surge detected ({last_diff:+.1f} pp); projection suspended due to instability."

        elif emptying_detected:
            # Right at emptying step: bin reset to empty baseline
            proj_state = "EMPTYING_RESET"
            rate_exposed = 0.0
            proj_1h = current_fill
            proj_3h = current_fill
            notes = f"Bin emptying event detected (-{emptying_magnitude:.1f} pp); new filling cycle initialized."

        elif current_fill > self.overflow_threshold:
            proj_state = "OVERFLOWING"
            proj_1h = None
            proj_3h = None
            rate_exposed = median_rate
            notes = f"Bin is currently overflowing at {current_fill:.1f}% (>100%); immediate dispatch mandatory."

        elif current_fill >= self.critical_threshold:
            proj_state = "ALREADY_FULL"
            proj_1h = None
            proj_3h = None
            rate_exposed = median_rate
            notes = f"Bin fill is {current_fill:.1f}% (>=85%); pickup required immediately."

        elif median_rate <= 0.2:
            proj_state = "STAGNANT_RATE"
            proj_1h = current_fill
            proj_3h = current_fill
            rate_exposed = median_rate
            notes = f"Accumulation rate is stagnant ({median_rate:.2f} pp/hr); bin fill projected stable."

        else:
            proj_state = "VALID"
            proj_1h = round(current_fill + median_rate * 1.0, 2)
            proj_3h = round(current_fill + median_rate * 3.0, 2)
            rate_exposed = median_rate
            notes = f"Stable normal accumulation at {median_rate:.2f} pp/hr."

        return WasteStatusResult(
            sensor_id=sensor_id,
            facility_id=facility_id,
            timestamp=ts_str,
            current_fill=current_fill,
            status=status,
            alert_severity=severity,
            fill_rate_pph=rate_exposed,
            projected_fill_1h=proj_1h,
            projected_fill_3h=proj_3h,
            surge_detected=surge_detected,
            surge_magnitude=surge_magnitude,
            emptying_detected=emptying_detected,
            emptying_magnitude=emptying_magnitude,
            projection_state=proj_state,
            notes=notes,
        )

    def process_series(
        self,
        df: pd.DataFrame,
        sensor_id: str = "SEN-013",
        facility_id: str = "FAC-06",
    ) -> pd.DataFrame:
        """
        Executes rolling evaluation over an entire historical dataframe.
        Returns a structured dataframe of all operational results and projections.
        """
        results = []
        n_points = len(df)

        for i in range(n_points):
            history_slice = df.iloc[: i + 1]
            res = self.evaluate(history_slice, sensor_id=sensor_id, facility_id=facility_id)
            results.append(res.to_dict())

        return pd.DataFrame(results)
