# InfraWatch AI --- System Design Specification

**Version:** 1.1\
**Status:** Corrected technical design\
**Date:** September 2026

## 1. Purpose

This document describes how the requirements in the InfraWatch AI PRD
are implemented. It deliberately contains technical details that are not
necessary in the PRD.

## 2. Architecture

``` text
                         ┌─────────────────────┐
                         │   Supabase Auth     │
                         │       + JWT         │
                         └──────────┬──────────┘
                                    │
┌──────────────────┐                │
│ Synthetic Data   │                │
│ Generator        │                │
└────────┬─────────┘                │
         │                          │
         ▼                          │
┌───────────────────────────────────┴───┐
│          Supabase PostgreSQL          │
│ facilities_dim                        │
│ sensors_dim                           │
│ sensor_readings_fact                  │
│ forecasts                             │
│ anomaly_insights                      │
└───────┬───────────────────────┬───────┘
        │                       │
        │                       ▼
        │               ┌───────────────┐
        │               │   Dash UI     │
        │               │   Read path   │
        │               └───────────────┘
        │
        ▼
┌──────────────────────┐
│ Offline ML Pipeline  │
│ Isolation Forest     │
│ Prophet              │
└──────────┬───────────┘
           │
           ▼
     ┌────────────┐
     │  FastAPI   │
     │ write path │
     └─────┬──────┘
           │
           ▼
     ┌────────────┐
     │ Claude API │
     └────────────┘
```

The prototype intentionally uses a direct Dash → Supabase read path for
pre-computed data. FastAPI is not a general-purpose read API.

## 3. Components

### Supabase PostgreSQL

Responsibilities:

-   Persistent data storage
-   Relational schema
-   Indexes
-   RLS where configured
-   Authentication integration
-   Realtime subscriptions where used

Does not:

-   Run ML models
-   Generate LLM recommendations
-   Render the dashboard

### ML Pipeline

Python batch processes:

-   Read sensor data
-   Build per-sensor features
-   Train Isolation Forest models
-   Score readings
-   Generate Prophet forecasts
-   Write outputs

### FastAPI

Responsibilities:

-   Validate protected write requests
-   Validate ML result payloads
-   Generate LLM insights
-   Enforce API-level authorization
-   Log write operations where required

Prototype endpoints:

``` text
POST /anomalies/score
POST /forecasts
POST /insights
```

### Plotly Dash

Responsibilities:

-   Render dashboard
-   Query pre-computed data
-   Provide navigation
-   Filter cached data
-   Render charts, tables, maps, and recommendations

It should not:

-   Run ML inference
-   Call Claude during page rendering
-   Perform database writes directly

### Claude API

Responsibilities:

-   Convert anomaly context into plain-language advisory
    recommendations.

It is not the source of truth for measurements or anomaly
classification.

## 4. Database Schema

### `facilities_dim`

  Column            Type      Purpose
  ----------------- --------- ------------------------------
  facility_id       TEXT PK   Facility identifier
  facility_name     TEXT      Display name
  facility_type     TEXT      Facility classification
  zone              TEXT      Operational zone
  capacity          INT       Maximum occupants
  floor_area_sqm    FLOAT     Area
  operating_hours   TEXT      Operating schedule
  is_critical       BOOL      Critical infrastructure flag
  latitude          FLOAT     Map coordinate
  longitude         FLOAT     Map coordinate

### `sensors_dim`

  Column                  Type      Purpose
  ----------------------- --------- --------------------------
  sensor_id               TEXT PK   Sensor identifier
  facility_id             TEXT FK   Facility
  sensor_type             TEXT      Sensor category
  metric_measured         TEXT      Human-readable metric
  unit                    TEXT      Measurement unit
  normal_lower_bound      FLOAT     Optional lower threshold
  normal_upper_bound      FLOAT     Upper threshold
  sampling_interval_min   INT       Sampling interval
  status                  TEXT      ACTIVE/INACTIVE

### `sensor_readings_fact`

  Column          Type          Purpose
  --------------- ------------- --------------------------------------
  reading_id      TEXT PK       Reading identifier
  recorded_at     TIMESTAMPTZ   Reading time
  sensor_id       TEXT FK       Sensor
  facility_id     TEXT FK       Facility
  reading_value   FLOAT         Measurement
  is_anomaly      BOOL          ML classification
  anomaly_score   FLOAT         Application-normalized anomaly score

### `forecasts`

  Column                Type          Purpose
  --------------------- ------------- -------------------------
  sensor_id             TEXT          Sensor
  facility_id           TEXT          Facility
  forecast_horizon_at   TIMESTAMPTZ   Predicted timestamp
  predicted_value       FLOAT         Central forecast
  lower_bound           FLOAT         Lower uncertainty bound
  upper_bound           FLOAT         Upper uncertainty bound
  forecasted_at         TIMESTAMPTZ   Generation timestamp

### `anomaly_insights`

  Column                Type          Purpose
  --------------------- ------------- -------------------------
  reading_id            TEXT FK       Source reading
  sensor_id             TEXT          Sensor
  facility_id           TEXT          Facility
  recommendation_text   TEXT          Advisory recommendation
  severity              TEXT          LOW/MEDIUM/HIGH
  generated_at          TIMESTAMPTZ   Generation time

## 5. Indexing

Required indexes:

``` sql
(sensor_id, recorded_at)
(facility_id, recorded_at)
WHERE is_anomaly = TRUE
```

Additional indexes should be added only after observing actual query
patterns.

## 6. Data Flow

### Step 1 --- Data generation

Generate 105,120 readings with deterministic seeds and realistic
operational patterns.

### Step 2 --- Validation

Validate:

-   row count
-   foreign keys
-   timestamps
-   duplicate timestamps per sensor
-   null values
-   value ranges

### Step 3 --- ML scoring

For each active sensor:

1.  Load history.
2.  Sort by timestamp.
3.  Build contextual features.
4.  Train Isolation Forest.
5.  Produce anomaly classification.
6.  Normalize the model score per sensor.
7.  Write results.

### Step 4 --- Forecasting

For each target sensor:

1.  Load historical readings.
2.  Fit Prophet.
3.  Generate 48-hour horizon.
4.  Store prediction and uncertainty bounds.
5.  Record `forecasted_at`.

### Step 5 --- Recommendation generation

For qualifying anomalies:

1.  Collect context.
2.  Build structured prompt.
3.  Call Claude.
4.  Validate non-empty output.
5.  Store recommendation.
6.  Mark generation timestamp.

### Step 6 --- Dashboard

Dash reads:

-   recent readings
-   anomalies
-   forecasts
-   recommendations
-   dimensions

and renders them without performing model inference.

## 7. Caching

Use `dcc.Store` or equivalent page-level caching for data that is
already fetched.

Do not cache indefinitely:

-   current anomaly state
-   current sensor values
-   forecast freshness

unless an explicit refresh policy is implemented.

## 8. Real-Time Feed

Supabase realtime may be used for the anomaly feed.

For the prototype, real-time behaviour can be simulated by
inserting/scoring new readings at intervals.

The UI must not imply that the prototype is connected to physical live
sensors.

## 9. Authentication and Authorization

The intended architecture is:

``` text
Supabase Auth
     ↓
JWT
     ↓
FastAPI validation
     ↓
Role authorization
```

Database RLS should be configured where direct database access needs
protection.

Client-side visibility controls are UX controls, **not the sole security
boundary**.

## 10. Failure Isolation

The system should degrade gracefully:

``` text
Claude unavailable
→ anomaly remains visible
→ recommendation marked unavailable

Forecast unavailable
→ historical chart remains visible

ML unavailable
→ raw readings remain visible
→ anomaly fields marked unavailable

Database unavailable
→ explicit error state
```

## 11. Security Rules

-   Store API keys in environment variables/secrets.
-   Never expose Claude credentials in Dash client code.
-   Never treat client-side role state as authoritative authorization.
-   Validate incoming FastAPI payloads with Pydantic.
-   Use least-privilege database credentials where practical.

## 12. Deployment Boundary

The prototype can be split into:

-   Supabase-hosted database/auth
-   Python ML execution environment
-   FastAPI service
-   Dash application

The exact hosting provider is an implementation decision and is not
required by the PRD.
