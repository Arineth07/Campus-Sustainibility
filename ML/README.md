# InfraWatch AI — Machine Learning Runtime Package (`ML/`)

This directory contains the production-ready, database-agnostic ML model and operational calculation logic for campus infrastructure monitoring.

---

## 1. Architectural Principles

1. **Database-Agnostic**: Contains zero database drivers, queries, or table dependencies (`supabase`, etc.). All data is passed in as in-memory data structures (Pandas DataFrames, dictionaries).
2. **Environment-Agnostic**: Does not read environment variables, `.env` files, or API credentials.
3. **Import-Safe**: Modules define classes, functions, and constants. Importing them has zero side-effects, starts no background workers, makes no network calls, and never exits the process.
4. **Decoupled Waste Strategy**:
   - **Prophet** (`ML/forecasting/`): Fits diurnal campus baselines (48h macro trends).
   - **WasteStatusEngine** (`ML/waste/`): High-frequency operational engine computing unclipped fill level, 4-tier alert status, robust 3h median fill-rate, and 1h/3h short-horizon projections.

---

## 2. Package Structure

```text
ML/
├── forecasting/
│   ├── __init__.py
│   └── forecast_service.py       # Pure Prophet 48h forecasting runtime
├── waste/
│   ├── __init__.py
│   └── waste_status_service.py   # Pure WasteStatusEngine operational logic
├── tests/
│   ├── __init__.py
│   ├── test_imports.py           # Verifies zero-dependency clean imports
│   ├── test_waste_status_service.py # Unit tests for waste state machine
│   └── test_forecast_service.py  # Unit tests for forecast validation
├── __init__.py                   # Canonical exports
├── README.md                     # Package documentation
└── requirements.txt              # Model runtime dependencies only
```

---

## 3. Callable Runtime Interfaces

### A. Forecasting (`ML.forecasting.forecast_service`)

#### `train_and_forecast(df: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, float]`
Fits Facebook Prophet on prepared historical time series and generates future forecasts.

- **Inputs**:
  - `df`: DataFrame containing `recorded_at` (timestamps) and `reading_value` (numeric).
  - `config`: Dictionary specifying `sensor_id`, `growth` (`"linear"` or `"logistic"`), `periods` (e.g. 192 or 96), `freq` (`"15min"` or `"30min"`), and optional `cap`/`floor`.
- **Returns**:
  - `forecast_df`: DataFrame with `['forecast_horizon_at', 'predicted_value', 'lower_bound', 'upper_bound']`.
  - `training_duration`: Float seconds taken to train.

#### `validate_forecast(future_forecast: pd.DataFrame, last_actual_ts: pd.Timestamp, config: Dict[str, Any]) -> None`
Strict assertion gatekeeper verifying that forecasts are non-empty, strictly increasing, strictly greater than `last_actual_ts`, match the exact period count, and adhere to sampling intervals.

---

### B. Waste Status Engine (`ML.waste.waste_status_service`)

#### `WasteStatusEngine(warning_threshold=70.0, critical_threshold=85.0, overflow_threshold=100.0, surge_threshold=15.0, emptying_threshold=-20.0, lookback_hours=3.0, sampling_interval_min=30)`
Configurable state machine for waste operational awareness.

#### `engine.evaluate(history_df: pd.DataFrame, sensor_id: str, facility_id: str) -> WasteStatusResult`
Evaluates the latest reading in `history_df` against trailing context.

- **Returns `WasteStatusResult`**:
  - `current_fill`: Latest sensor reading (strictly unclipped, e.g. `104.5%`).
  - `status`: `"Normal"`, `"Pickup Soon"`, `"Pickup Required"`, or `"Overflowing"`.
  - `alert_severity`: `"LOW"`, `"MEDIUM"`, `"HIGH"`, or `"CRITICAL"`.
  - `fill_rate_pph`: 3-hour median accumulation rate in percentage points/hour (`pp/hr`), or `None`.
  - `projected_fill_1h`: Predicted fill in 1 hour (`current_fill + rate * 1.0`), or `None` if surge/full.
  - `projected_fill_3h`: Predicted fill in 3 hours (`current_fill + rate * 3.0`), or `None` if surge/full.
  - `surge_detected`: Boolean flag indicating jump $\ge 15\text{ pp}$ over last 30 minutes.
  - `projection_state`: `"VALID"`, `"UNSTABLE_SURGE"`, `"EMPTYING_RESET"`, `"STAGNANT_RATE"`, `"ALREADY_FULL"`, `"OVERFLOWING"`, or `"INSUFFICIENT_DATA"`.

#### `engine.process_series(df: pd.DataFrame, sensor_id: str, facility_id: str) -> pd.DataFrame`
Performs a rolling evaluation over an entire historical series for offline evaluation and backtesting.

---

## 4. Running Unit Tests

Execute the test suite using Python's standard library `unittest`:

```bash
python -m unittest discover -s ML/tests -v
```
