# InfraWatch AI --- Product Requirements Document

**Version:** 1.1\
**Status:** Final Draft --- Corrected\
**Date:** September 2026\
**Target:** Engineering college campus prototype\
**Stack:** Plotly Dash · Supabase Postgres · FastAPI · Isolation Forest
· Prophet · Claude API\
**Dataset:** 105,120 synthetic readings · 28 sensors · 12 facilities ·
30 days

## 1. Executive Summary

InfraWatch AI is a web-based campus sustainability and operations
dashboard for monitoring energy, water, waste, air quality, occupancy,
and related operational signals.

The prototype addresses fragmented facility data, delayed anomaly
discovery, lack of short-term forecasting, and lack of actionable
decision support. It provides a unified operational view, contextual
anomaly detection, 48-hour forecasts for selected sensors, and
plain-language recommendations.

The primary product outcome is to help facility administrators identify
operational problems earlier and understand what action should be
investigated.

### Prototype scope

-   12 facilities
-   28 sensors
-   30 days of synthetic IoT-style data
-   105,120 sensor readings
-   Four operational zones
-   Three dashboard pages
-   Isolation Forest anomaly detection
-   Prophet forecasting for five selected sensors
-   Pre-computed Claude-generated recommendations
-   Campus map using facility coordinates

Synthetic anomalies are used for functional validation of the pipeline.
They are **not evidence of real-world model accuracy**.

## 2. Problem Statement

The prototype addresses:

-   No unified operational view across facilities
-   Anomalies discovered only after operational impact
-   Limited ability to anticipate near-term demand or overflow
-   Raw sensor data without decision-oriented interpretation
-   Different operational roles needing different information

## 3. Goals

### Product goals

1.  Provide a unified campus operational dashboard.
2.  Detect unusual sensor behaviour using contextual features.
3.  Provide short-term forecasts for selected high-value signals.
4.  Translate qualifying anomalies into understandable recommended
    actions.
5.  Provide facility and zone-level sustainability views.
6.  Make model outputs explainable through thresholds, scores, markers,
    and uncertainty bands.

### Non-goals

-   Production-grade IoT ingestion
-   Certified sustainability scoring
-   Fully autonomous facility control
-   Safety-critical automated decisions
-   Claiming real-world ML accuracy from synthetic data
-   Full mobile application

## 4. Users and Roles

  -----------------------------------------------------------------------
  Role              Primary need      Primary access    Decision horizon
  ----------------- ----------------- ----------------- -----------------
  Facility          Campus health,    Overview +        Immediate
  Administrator     anomalies,        facilities        
                    critical alerts                     

  Operations Team   Sensor detail,    Facility Deep     Short-term
                    anomalies,        Dive              
                    maintenance                         
                    investigation                       

  Sustainability    Zone KPIs,        Sustainability    Weekly/monthly
  Officer           trends,                             
                    sustainability                      
                    index, export                       
  -----------------------------------------------------------------------

Authentication and authorization are implementation concerns described
in the System Design document. The PRD requirement is simply that users
receive role-appropriate access.

## 5. User Stories

-   As a facility administrator, I want to see the campus status at a
    glance so I can identify facilities requiring attention.
-   As an operations team member, I want to inspect a facility's sensor
    history so I can investigate unusual behaviour.
-   As an operations team member, I want anomalies shown alongside
    normal thresholds so I can understand why a reading was flagged.
-   As a sustainability officer, I want to compare energy, water, and
    waste by zone so I can identify operational differences.
-   As a sustainability officer, I want to view 30-day trends so I can
    identify changes over time.
-   As a facility administrator, I want a plain-language recommendation
    associated with a qualifying anomaly so I know what should be
    investigated.
-   As an administrator, I want forecast uncertainty visible so I do not
    interpret a prediction as a guaranteed outcome.

## 6. Functional Requirements

  -----------------------------------------------------------------------
  ID                      Requirement             Priority
  ----------------------- ----------------------- -----------------------
  FR-001                  Display campus-level    High
                          KPI summary             

  FR-002                  Display facilities on   High
                          an interactive map      

  FR-003                  Navigate from a         High
                          facility on the map to  
                          its deep-dive page      

  FR-004                  Select a sensor for a   High
                          facility                

  FR-005                  Display historical      High
                          sensor readings         

  FR-006                  Display detected        High
                          anomalies on            
                          time-series charts      

  FR-007                  Display static sensor   High
                          thresholds where        
                          configured              

  FR-008                  Display 48-hour         High
                          forecasts where         
                          available               

  FR-009                  Display forecast        High
                          uncertainty intervals   

  FR-010                  Display qualifying      High
                          recommendations         

  FR-011                  Display zone-level      Medium
                          energy, water, and      
                          waste comparisons       

  FR-012                  Display facility-level  Medium
                          operational             
                          sustainability index    

  FR-013                  Display 30-day modality Medium
                          trends                  

  FR-014                  Support                 Medium
                          role-appropriate access 

  FR-015                  Handle missing,         High
                          unavailable, or stale   
                          model outputs           
                          gracefully              
  -----------------------------------------------------------------------

## 7. Non-Functional Requirements

### Performance

-   Dashboard should load pre-computed results without running ML or LLM
    inference.
-   Common dashboard interactions should use cached page data where
    practical.
-   Model and LLM execution must not block dashboard rendering.

### Reliability

-   Failure of the LLM service must not prevent sensor data or anomaly
    results from being displayed.
-   Failure of forecasting must not prevent historical sensor data from
    being displayed.
-   Stale forecasts must be identifiable using `forecasted_at`.

### Security

-   Authentication is required for protected views.
-   Role-based access must be enforced at the appropriate
    backend/database layers.
-   API credentials must not be exposed in frontend code.
-   LLM recommendations must be treated as advisory output.

### Usability

-   Sensor and facility labels must use human-readable names.
-   Anomalies, thresholds, forecasts, and recommendations must be
    visually distinguishable.
-   Empty, loading, error, and stale states must have explicit UI
    behaviour.

## 8. Data Requirements

### Core entities

-   `facilities_dim`
-   `sensors_dim`
-   `sensor_readings_fact`
-   `forecasts`
-   `anomaly_insights`

### Data quality requirements

  -----------------------------------------------------------------------
  ID                                  Requirement
  ----------------------------------- -----------------------------------
  DQ-001                              Active sensor readings must have a
                                      non-null `reading_value`.

  DQ-002                              Sensor readings must reference
                                      valid facilities and sensors.

  DQ-003                              Duplicate sensor/timestamp
                                      observations must be rejected or
                                      explicitly handled.

  DQ-004                              Sensor values must be compatible
                                      with their declared units and basic
                                      physical constraints.

  DQ-005                              Inactive sensors must be excluded
                                      from dashboard and ML processing.

  DQ-006                              Timestamps must be stored
                                      consistently and interpreted in IST
                                      for dashboard presentation.
  -----------------------------------------------------------------------

## 9. Dashboard Requirements

### Page 1 --- Overview

Components:

1.  KPI cards
2.  Campus map
3.  Recent anomaly feed

KPIs:

-   Total anomalies today
-   Facilities at risk
-   Current campus power
-   Water supply status

The map uses facility coordinates and navigates to
`/facility/<facility_id>`.

### Page 2 --- Facility Deep Dive

Components:

-   Facility identification
-   Sensor selector
-   Historical time series
-   Anomaly markers
-   Static threshold lines
-   48-hour forecast where available
-   Confidence interval
-   Recommendation panel

The chart should communicate historical behaviour, detected anomalies,
and future forecast in one view.

### Page 3 --- Sustainability

Components:

-   Energy comparison by zone
-   Water comparison by zone
-   Waste comparison by zone
-   Facility-level operational sustainability index
-   30-day trends
-   Downloadable summary where implemented

### Operational Sustainability Index

The index is a **prototype-defined operational metric**, not a certified
sustainability standard.

Current formula:

`score = [(1 - energy_utilisation%) × 0.40 + (1 - water_utilisation%) × 0.30 + (1 - waste_fill%) × 0.30] × 100 - (anomaly_count × 2)`

Clamp to 0--100.

The weights and penalty are documented assumptions and must not be
presented as scientifically validated sustainability coefficients.

## 10. AI/ML Product Requirements

### Anomaly detection

-   Score active sensor readings using contextual features.
-   Use one model per sensor in the prototype.
-   Store `is_anomaly` and `anomaly_score`.
-   Use application-defined severity thresholds.
-   Do not describe the normalized score as a probability of anomaly.

### Forecasting

-   Produce 48-hour forecasts for five selected sensors.
-   Store central prediction and lower/upper uncertainty bounds.
-   Display forecasts as indicative decision-support outputs.

### Recommendations

-   Generate recommendations only for qualifying anomalies.
-   Include sensor, facility, reading, normal range, time, operating
    context, criticality, and anomaly information in the prompt.
-   Keep recommendations concise and action-oriented.
-   Store generated recommendations before dashboard display.
-   Do not allow LLM output to overwrite the underlying measurement or
    ML result.

## 11. Acceptance Criteria

### Overview

-   Campus KPIs load successfully.
-   All active facilities appear on the map.
-   Clicking a facility opens the correct deep-dive page.
-   Recent anomalies are sorted by timestamp.
-   Missing recommendations do not break the anomaly feed.

### Facility Deep Dive

-   Sensor selector contains only sensors belonging to the selected
    facility.
-   Historical readings render for the selected sensor.
-   Anomaly markers correspond to `is_anomaly = TRUE`.
-   Threshold lines appear only when thresholds exist.
-   Forecast is shown only when forecast rows are available.
-   Forecast uncertainty is visibly distinct from the central
    prediction.

### Recommendations

-   Recommendations are displayed only when stored.
-   Recommendation generation failure does not hide the anomaly.
-   Recommendation text is clearly identified as guidance/advisory
    output.

### Sustainability

-   Zone aggregates use the selected time window.
-   Facility index is clamped to the defined range.
-   The UI identifies the index as a prototype-defined metric.

## 12. Error and Empty States

The product must define behaviour for:

-   No readings in selected period
-   Sensor inactive
-   Forecast unavailable
-   Forecast stale
-   ML results unavailable
-   LLM recommendation unavailable
-   Database/API failure
-   Invalid facility ID
-   Invalid sensor selection

Example:

> Forecast unavailable for this sensor.

rather than presenting an empty chart without explanation.

## 13. Success Criteria

The prototype is successful when:

1.  The full dataset is loaded and validated.
2.  All active sensors can be queried.
3.  ML scoring completes and results are stored.
4.  Forecasts exist for the selected five sensors.
5.  All three dashboard pages render.
6.  Map-to-facility navigation works.
7.  Qualifying anomalies can be followed through to recommendations.
8.  Role/access behaviour works for the intended prototype.
9.  Failure states do not collapse the dashboard.
10. The complete demo narrative works without manual database editing.

## 14. Scope Expansion

The architecture is intended to be adaptable to hospitals, PSUs,
municipal campuses, and company campuses. Adaptation should be treated
as future scope rather than part of the current prototype.

## 15. Evaluation Mapping

  ------------------------------------------------------------------------
  Criterion                                   Weight Product evidence
  --------------------- ---------------------------- ---------------------
  Sustainability &                               20% Five monitoring
  Operations Relevance                               modalities,
                                                     facility/zone
                                                     aggregation,
                                                     operational index

  Data Engineering &                             20% Star schema, indexed
  Visualization                                      time-series data,
                                                     map, integrated chart

  AI/ML                                          20% Contextual Isolation
                                                     Forest and 48-hour
                                                     Prophet forecasts

  Actionability                                  15% Plain-language
                                                     recommendations

  Usability                                      10% Role-oriented
                                                     three-page dashboard

  Explainability                                 10% Thresholds, anomaly
                                                     scores, uncertainty
                                                     bands, assumptions

  Demo Quality                                    5% Fast pre-computed
                                                     dashboard and
                                                     end-to-end narrative
  ------------------------------------------------------------------------
