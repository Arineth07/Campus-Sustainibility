# InfraWatch AI — Machine Learning Testing & Evaluation Lab (`ML Test/`)

This directory contains offline validation scripts, exploratory data analysis, backtesting experiments, generated reports, and diagnostic plots for campus forecasting and operational status engines.

> [!NOTE]
> Production and runtime model logic has been refactored into:
> - `ML/`: Pure, database-agnostic model runtimes (`ML.forecasting`, `ML.waste`).
> - `Jobs/`: Database and orchestration services (`Jobs.forecast_job`).

---

## 1. Directory Structure

```text
ML Test/
├── evaluation/
│   ├── evaluate_forecasts.py           # 5-fold rolling-origin Prophet backtester
│   ├── evaluate_waste_short_horizon.py # 6-method short-horizon waste benchmark
│   └── evaluate_waste_status_service.py# WasteStatusEngine full 30-day validator
├── analysis/
│   └── analyze_waste_patterns.py       # Telemetry audit of 36h sawtooth & pulse spikes
├── results/
│   ├── evaluation_results.csv          # Prophet backtest metrics (MAE, RMSE, MAPE)
│   ├── waste_threshold_results.csv     # Waste 85% crossing timing results
│   ├── waste_short_horizon_results.csv # Retrospective short-horizon comparison metrics
│   └── waste_status_service_results.csv# Operational engine online performance logs
├── reports/
│   ├── evaluation_report.md            # Comprehensive Prophet evaluation report
│   ├── waste_pattern_analysis.md       # In-depth analysis of waste cycles & spikes
│   ├── waste_short_horizon_analysis.md # Short-horizon benchmark findings & >100% semantics
│   └── waste_status_service_analysis.md# Operational status engine validation report
├── plots/
│   ├── (30 Prophet backtest & overview figures)
│   └── (6 waste pattern & hourly profile figures)
├── requirements.txt                    # Testing & plotting dependencies
└── README.md
```

---

## 2. Running Evaluation Scripts

All scripts can be executed directly from the project root:

### A. Waste Status Service Operational Evaluation
Tests `ML.waste.waste_status_service.WasteStatusEngine` on the full 30 days of actual sensor readings:
```bash
python "ML Test/evaluation/evaluate_waste_status_service.py"
```
- Outputs metrics to `ML Test/results/waste_status_service_results.csv`.
- Generates report in `ML Test/reports/waste_status_service_analysis.md`.

### B. Waste Short-Horizon Benchmarking
Compares linear regression vs. median fill-rate vs. Theil-Sen estimators across 1h, 3h, and 6h horizons:
```bash
python "ML Test/evaluation/evaluate_waste_short_horizon.py"
```
- Outputs metrics to `ML Test/results/waste_short_horizon_results.csv`.
- Generates report in `ML Test/reports/waste_short_horizon_analysis.md`.

### C. Prophet Rolling-Origin Backtesting
Evaluates 48-hour Prophet forecasts across 5 folds for `SEN-023`, `SEN-021`, `SEN-013`, `SEN-016`, and `SEN-019`:
```bash
python "ML Test/evaluation/evaluate_forecasts.py"
```
- Outputs metrics to `ML Test/results/evaluation_results.csv`.
- Generates report in `ML Test/reports/evaluation_report.md` and charts in `ML Test/plots/`.

### D. Waste Telemetry Pattern Analysis
Audits cycles, true emptyings, spike frequencies, and 85% predictability:
```bash
python "ML Test/analysis/analyze_waste_patterns.py"
```
- Generates report in `ML Test/reports/waste_pattern_analysis.md` and charts in `ML Test/plots/`.
