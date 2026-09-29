# InfraWatch AI --- ML & Forecasting Specification

**Version:** 1.1\
**Status:** Corrected\
**Date:** September 2026

## 1. Purpose

This document defines the anomaly detection and forecasting pipeline.

The ML outputs are **decision-support outputs**. They are not official
measurements, safety guarantees, or certified predictions.

## 2. Dataset

-   28 sensors
-   12 facilities
-   30 days
-   105,120 synthetic readings
-   Mixed 5-, 15-, and 30-minute sampling intervals
-   Deliberately seeded anomalies for functional validation

Synthetic anomalies allow controlled testing but do not establish
real-world model performance.

## 3. Anomaly Detection

### Model

Isolation Forest.

One model is trained per sensor in the prototype because different
sensors have different operating regimes.

Example:

-   Data center power is expected to be relatively stable.
-   Academic building power has strong time-of-day behaviour.

Combining them into a single model would mix incompatible baselines.

## 4. Feature Matrix

  Feature             Description
  ------------------- ----------------------------------
  `reading_value`     Current measurement
  `hour`              Hour of day
  `day_of_week`       Day of week
  `is_weekend`        Weekend indicator
  `rolling_mean_1h`   Local one-hour mean
  `deviation`         Current value minus rolling mean

The intent is to detect contextual anomalies rather than relying
exclusively on static thresholds.

## 5. Parameters

Initial prototype parameters:

  Parameter            Value
  ----------------- --------
  `n_estimators`         100
  `contamination`       0.03
  `random_state`          42
  `max_samples`       `auto`

`contamination=0.03` is an application assumption controlling expected
outlier proportion. It is **not a measured ground-truth anomaly rate**.

## 6. Score Handling

Isolation Forest produces model scores whose raw scale is not directly
suitable for the dashboard.

The prototype converts scores to a 0--1 application score using
per-sensor min-max normalization.

Interpretation:

-   Higher value = more anomalous relative to that sensor's scored
    history.
-   Lower value = more normal relative to that sensor's scored history.

### Important limitation

The normalized score is **not a probability**.

A score of `0.8` must not be described as "80% probability of anomaly."

Likewise, normalized scores from different sensors should be treated as
dashboard severity indicators, not statistically calibrated
probabilities.

## 7. Severity

Application-defined bands:

         Score Severity
  ------------ ----------
       `< 0.4` LOW
    `0.4–<0.7` MEDIUM
       `≥ 0.7` HIGH

These thresholds are product rules, not inherent Isolation Forest
thresholds.

Recommendation generation is triggered for MEDIUM and HIGH anomalies.

## 8. Static Thresholds vs ML

The system intentionally uses both:

### Static threshold

Answers:

> Is this value outside the configured operating range?

### ML anomaly detection

Answers:

> Is this behaviour unusual relative to this sensor's contextual
> history?

Both should be shown together where possible.

This provides explainability and allows an administrator to distinguish
rule-based alerts from contextual anomalies.

## 9. Validation Strategy

Because the dataset contains known seeded anomalies, use them for
functional evaluation.

Recommended evaluation outputs:

-   Number of seeded anomalies
-   Number detected
-   False positives on known-normal periods
-   Detection rate against seeded anomalies
-   Detection behaviour by sensor
-   Confusion matrix where seeded labels are available

These metrics describe performance on the synthetic test dataset only.

Do not present them as production accuracy.

## 10. Forecasting

### Model

Prophet.

### Target sensors

1.  `SEN-023` --- campus electrical feed
2.  `SEN-021` --- main water supply
3.  `SEN-013` --- boys hostel waste bin
4.  `SEN-016` --- girls hostel waste bin
5.  `SEN-019` --- mess/canteen waste bin

### Horizon

48 hours.

### Parameters

  Parameter                   Value
  --------------------------- -----------------
  `daily_seasonality`         True
  `weekly_seasonality`        True
  `changepoint_prior_scale`   0.05
  `seasonality_mode`          multiplicative
  Horizon                     48 hours
  Sampling                    Sensor-specific

## 11. Forecast Output

Each forecast row contains:

-   `forecast_horizon_at`
-   `predicted_value`
-   `lower_bound`
-   `upper_bound`
-   `forecasted_at`

The dashboard renders:

``` text
historical readings
       │
       │
       ├─────────────── Now ────────────────
       │                                  /
       │                               forecast
       │                            ┌─────────┐
       │                       uncertainty band
```

## 12. Forecast Interpretation

Forecasts are indicative.

The model assumes that near-term patterns are reasonably represented by
the preceding 30 days.

It does not explicitly model:

-   campus shutdowns
-   festivals
-   unusual events
-   equipment failures
-   sudden policy changes
-   weather-driven effects unless encoded indirectly in the history

Therefore:

> A forecast is a planning signal, not a guaranteed future measurement.

## 13. LLM Recommendation Layer

Claude receives structured context including:

-   sensor type
-   facility
-   current reading
-   unit
-   normal range
-   anomaly score
-   time
-   operating hours
-   criticality

The LLM produces a short advisory recommendation.

### Safety/quality boundary

The LLM:

-   may explain
-   may recommend investigation
-   may suggest operational action

The LLM must not:

-   modify sensor data
-   modify anomaly scores
-   claim certainty not present in the data
-   present itself as an authority overriding facility procedures

## 14. Evaluation Plan

Before integration, verify:

### Anomaly pipeline

-   All 28 sensors produce outputs.
-   No active sensor is silently skipped.
-   Scores are finite.
-   `is_anomaly` is boolean.
-   Known seeded anomalies can be traced.

### Forecast pipeline

-   Five target sensors produce 48-hour forecasts.
-   Forecast timestamps are future timestamps.
-   Lower bound ≤ prediction ≤ upper bound.
-   `forecasted_at` is populated.

### Recommendation pipeline

-   Only qualifying anomalies trigger recommendations.
-   Output is non-empty.
-   Reading/facility/sensor references remain correct.
-   LLM failure does not delete or hide the anomaly.
