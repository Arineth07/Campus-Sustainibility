# InfraWatch AI --- Implementation & Delivery Plan

**Version:** 1.1\
**Status:** Corrected\
**Date:** September 2026

## 1. Current State

Phase 1 is complete according to the project PRD:

-   Supabase schema created
-   Synthetic dataset generated
-   105,120 readings populated
-   12 facilities
-   28 sensors
-   30 days of data

The next development objective is to turn the database into a working
end-to-end prototype.

## 2. Recommended Build Order

``` text
Phase 1 — Database/Data
        ↓
Phase 2 — ML Pipeline
        ↓
Phase 3 — Dashboard
        ↓
Phase 4 — FastAPI + Auth
        ↓
Phase 5 — LLM Insights
        ↓
Phase 6 — Integration + Testing
        ↓
Phase 7 — Demo Hardening
```

ML and frontend can proceed in parallel after Phase 1.

FastAPI should not block the initial dashboard prototype because the
dashboard can initially read the already-existing Supabase data.

## 3. Phase 2 --- ML Pipeline

### Deliverables

-   Data loader
-   Validation layer
-   Feature engineering
-   Per-sensor Isolation Forest
-   Score normalization
-   Supabase writeback
-   Prophet forecasting
-   Forecast writeback
-   Basic ML evaluation report

### Suggested project structure

``` text
ml/
├── config.py
├── data_loader.py
├── validation.py
├── features.py
├── anomaly_detection.py
├── forecasting.py
├── writeback.py
├── evaluate.py
└── run_pipeline.py
```

### Exit criteria

-   All active sensors processed.
-   `is_anomaly` populated.
-   `anomaly_score` populated.
-   Scores are finite and within 0--1.
-   Known seeded anomalies can be inspected.
-   Forecast table populated for five target sensors.

## 4. Phase 3 --- Dashboard

### Deliverables

``` text
dashboard/
├── app.py
├── pages/
│   ├── overview.py
│   ├── facility.py
│   └── sustainability.py
├── components/
│   ├── kpi_cards.py
│   ├── campus_map.py
│   ├── anomaly_feed.py
│   ├── sensor_chart.py
│   └── recommendation_panel.py
├── data/
│   └── supabase_client.py
└── assets/
    └── styles.css
```

### Build order

1.  Supabase connection
2.  Overview page
3.  KPI cards
4.  Campus map
5.  Facility route
6.  Sensor selector
7.  Time-series chart
8.  Anomaly markers
9.  Threshold lines
10. Forecast overlay
11. Sustainability page
12. Recommendation panel
13. Empty/error states

### Exit criteria

-   All three pages load.
-   Map navigation works.
-   Sensor selection works.
-   Historical charts work.
-   Anomalies appear correctly.
-   Forecasts appear for target sensors.
-   No ML or LLM inference happens inside Dash callbacks.

## 5. Phase 4 --- FastAPI + Authentication

### Endpoints

``` text
POST /anomalies/score
POST /forecasts
POST /insights
```

### Responsibilities

-   JWT validation
-   Role authorization
-   Pydantic validation
-   ML result write validation
-   LLM insight orchestration
-   Logging

### Exit criteria

-   Invalid requests are rejected.
-   Protected endpoints require authentication.
-   Valid ML output can be written.
-   Roles are enforced server-side.
-   Secrets are never exposed to the browser.

## 6. Phase 5 --- LLM Insights

### Flow

``` text
Anomaly
   ↓
Context assembly
   ↓
FastAPI /insights
   ↓
Claude API
   ↓
Recommendation validation
   ↓
anomaly_insights
   ↓
Dash
```

### Recommendation generation rules

Generate for:

-   MEDIUM anomalies
-   HIGH anomalies

Do not generate for LOW anomalies unless explicitly enabled.

### Exit criteria

-   Recommendation text is stored.
-   Recommendation references the correct reading.
-   LLM failure leaves the anomaly visible.
-   Recommendations are clearly advisory.

## 7. Phase 6 --- Integration

Test the complete narrative:

``` text
Campus
  ↓
Facility
  ↓
Sensor
  ↓
Historical anomaly
  ↓
Anomaly score
  ↓
Threshold/context comparison
  ↓
Forecast
  ↓
Recommendation
```

### Integration tests

-   Database → ML
-   ML → database
-   Database → Dash
-   ML → FastAPI
-   FastAPI → Claude
-   Claude → database
-   Database → recommendation panel
-   Authentication → protected access

## 8. Phase 7 --- Demo Hardening

The demo should have a deterministic story.

Prepare:

1.  A known facility with an anomaly.
2.  A known anomaly timestamp.
3.  A target forecast sensor.
4.  A stored recommendation.
5.  A facility map point.
6.  A clear before/after or normal/anomalous comparison.

Do not depend on an external LLM call during the actual presentation if
a stored recommendation can demonstrate the feature reliably.

## 9. Definition of Done

The prototype is complete when:

-   [ ] Database schema is validated.
-   [ ] Dataset passes data-quality checks.
-   [ ] 28 active sensors can be processed.
-   [ ] Isolation Forest results are stored.
-   [ ] Forecasts exist for five sensors.
-   [ ] Overview page works.
-   [ ] Facility Deep Dive works.
-   [ ] Sustainability page works.
-   [ ] Map navigation works.
-   [ ] Recommendations work for qualifying anomalies.
-   [ ] Authentication/roles work for the intended prototype.
-   [ ] Error and empty states are implemented.
-   [ ] No API keys are exposed.
-   [ ] End-to-end demo works without manual database edits.

## 10. Team Workstreams

  Track         Deliverable                  Dependency
  ------------- ---------------------------- ---------------
  ML            Isolation Forest + Prophet   Database
  Frontend      Dash pages + charts + map    Database
  Backend       FastAPI + Auth               Supabase Auth
  AI            Claude recommendations       ML outputs
  Integration   End-to-end testing           All tracks

## 11. Testing Matrix

  Layer         Test
  ------------- -----------------------------------------------
  Data          Counts, nulls, duplicates, foreign keys
  Database      Query correctness and indexes
  ML            Score range, seeded anomaly detection
  Forecast      Future timestamps, bounds, freshness
  API           Authentication, validation, failure responses
  LLM           Output existence, context correctness
  Frontend      Navigation, charts, filters, states
  Integration   Complete anomaly-to-recommendation flow

## 12. Operational Checklist

Before demo:

-   Verify Supabase connection.
-   Verify dataset count.
-   Verify ML output count.
-   Verify forecast rows.
-   Verify recommendation rows.
-   Verify map rendering.
-   Verify all three pages.
-   Verify environment variables.
-   Verify no development-only credentials are visible.
-   Run the complete demo once from a clean application start.
