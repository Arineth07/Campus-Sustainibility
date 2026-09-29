
# Campus Sustainability Dashboard — Data Schema

## 1. Star Schema Overview

The data model uses a **star-schema design** centered on `sensor_readings_fact`.

- `sensor_readings_fact` is the central fact table containing time-series sensor observations.
- Each fact row references exactly one `facilities_dim` row through `facility_id`.
- Each fact row references exactly one `sensors_dim` row through `sensor_id`.
- `sensors_dim` also references its owning facility through `facility_id`.
- `facility_id` is intentionally stored directly in the fact table even though it can be derived through `sensors_dim`. This denormalization avoids an additional join when aggregating millions of readings by facility or zone.
- The resulting hierarchy is:

```text
facilities_dim
      │
      ├──────────────┐
      │              │
      ▼              ▼
sensors_dim   sensor_readings_fact
      │              ▲
      └──────────────┘
```

The model is designed to support facility-level and zone-level aggregation, time-series analysis, anomaly detection, forecasting, and dashboard visualizations.

---

## 2. `facilities_dim`

`facilities_dim` defines the physical and operational context of the campus facilities.

### Structure

| facility_id | facility_name | facility_type | zone | capacity | floor_area_sqm | operating_hours | is_critical | latitude | longitude |
|---|---|---|---|---:|---:|---|---|---:|---:|
| FAC-01 | Main Academic Block A | ACADEMIC | Academic/Admin | 1200 | 8500 | 07:00–20:00 | No | 18.5210 | 73.8562 |
| FAC-02 | Central Library | LIBRARY | Academic/Admin | 800 | 6000 | 08:00–23:00 | No | 18.5214 | 73.8567 |
| FAC-03 | Administration Block | ADMIN | Academic/Admin | 300 | 3200 | 09:00–18:00 | No | 18.5208 | 73.8570 |
| FAC-04 | Central Data Center | DATA_CENTER | Academic/Admin | 15 | 400 | 24×7 | Yes | 18.5206 | 73.8569 |
| FAC-05 | Engineering Labs Block | LAB | Academic/Admin | 900 | 7200 | 08:00–19:00 | No | 18.5212 | 73.8558 |
| FAC-06 | Boys' Hostel Block 1 | HOSTEL | Residential | 600 | 9000 | 24×7 | No | 18.5195 | 73.8575 |
| FAC-07 | Girls' Hostel Block 1 | HOSTEL | Residential | 500 | 8000 | 24×7 | No | 18.5192 | 73.8580 |
| FAC-08 | Central Mess & Canteen | DINING | Dining/Utility | 1000 | 3500 | 06:00–23:00 | No | 18.5198 | 73.8578 |
| FAC-09 | Pump House & STP | UTILITY_WATER | Dining/Utility | 10 | 1200 | 24×7 | Yes | 18.5188 | 73.8555 |
| FAC-10 | Main Electrical Substation | UTILITY_POWER | Dining/Utility | 8 | 800 | 24×7 | Yes | 18.5202 | 73.8552 |
| FAC-11 | Main Gate & Parking | TRANSIT | Transit/Perimeter | 2000 | 5000 | 24×7 | No | 18.5220 | 73.8548 |
| FAC-12 | Sports Complex | SPORTS | Transit/Perimeter | 1500 | 20000 | 06:00–22:00 | No | 18.5185 | 73.8590 |

### Design Reasoning

The twelve facilities are distributed across four zones so that each zone exhibits a meaningfully different operational pattern:

- **Academic/Admin:** primarily daytime activity, with significantly reduced activity at night.
- **Residential:** stronger evening and nighttime activity, producing a pattern that contrasts with academic facilities.
- **Dining/Utility:** meal-time demand spikes combined with infrastructure that may operate continuously.
- **Transit/Perimeter:** activity driven by traffic, footfall, and environmental conditions.

This variation is intentional. It gives anomaly-detection and forecasting models different behavioral baselines instead of treating every facility as if it followed the same daily pattern.

### `is_critical`

`is_critical` identifies infrastructure where a reduction in normal activity can be as significant as an abnormal increase.

This is particularly relevant to 24×7 infrastructure such as the data center, water infrastructure, and electrical substation. These facilities therefore require lower-bound monitoring in addition to conventional upper-bound checks.

### Coordinates

`latitude` and `longitude` provide the geographic position of each facility and support campus-map visualizations, including the visualization of potential pollution hotspots, water-related incidents, and other spatial patterns.

---

## 3. `sensors_dim`

`sensors_dim` describes each sensor, the metric it measures, its expected operating range, and its sampling cadence.

### Structure

| sensor_id | facility_id | sensor_type | metric_measured | unit | normal_lower_bound | normal_upper_bound | sampling_interval_min | status |
|---|---|---|---|---|---:|---:|---:|---|
| SEN-001 | FAC-01 | SMART_METER | Active Power Demand | kW | — | 180 | 15 | ACTIVE |
| SEN-002 | FAC-01 | AIR_CO2 | CO₂ Concentration | ppm | — | 1000 | 5 | ACTIVE |
| SEN-003 | FAC-01 | OCCUPANCY | Occupancy Count | persons | — | 1200 | 15 | ACTIVE |
| SEN-004 | FAC-02 | SMART_METER | Active Power Demand | kW | — | 100 | 15 | ACTIVE |
| SEN-005 | FAC-02 | AIR_CO2 | CO₂ Concentration | ppm | — | 1000 | 5 | ACTIVE |
| SEN-006 | FAC-02 | OCCUPANCY | Occupancy Count | persons | — | 700 | 15 | ACTIVE |
| SEN-007 | FAC-03 | SMART_METER | Active Power Demand | kW | — | 75 | 15 | ACTIVE |
| SEN-008 | FAC-04 | SMART_METER | Active Power Demand | kW | 80 | 140 | 5 | ACTIVE |
| SEN-009 | FAC-05 | SMART_METER | Active Power Demand | kW | — | 240 | 15 | ACTIVE |
| SEN-010 | FAC-05 | AIR_CO2 | CO₂ Concentration | ppm | — | 1000 | 5 | ACTIVE |
| SEN-011 | FAC-06 | SMART_METER | Active Power Demand | kW | — | 110 | 15 | ACTIVE |
| SEN-012 | FAC-06 | WATER_FLOW | Water Flow Rate | L/min | — | 150 | 15 | ACTIVE |
| SEN-013 | FAC-06 | WASTE_BIN | Bin Fill Level | % | — | 85 | 30 | ACTIVE |
| SEN-014 | FAC-07 | SMART_METER | Active Power Demand | kW | — | 110 | 15 | ACTIVE |
| SEN-015 | FAC-07 | WATER_FLOW | Water Flow Rate | L/min | — | 150 | 15 | ACTIVE |
| SEN-016 | FAC-07 | WASTE_BIN | Bin Fill Level | % | — | 85 | 30 | ACTIVE |
| SEN-017 | FAC-08 | SMART_METER | Active Power Demand | kW | — | 160 | 15 | ACTIVE |
| SEN-018 | FAC-08 | WATER_FLOW | Water Flow Rate | L/min | — | 120 | 15 | ACTIVE |
| SEN-019 | FAC-08 | WASTE_BIN | Bin Fill Level | % | — | 85 | 30 | ACTIVE |
| SEN-020 | FAC-08 | AIR_CO2 | CO₂ Concentration | ppm | — | 1500 | 5 | ACTIVE |
| SEN-021 | FAC-09 | WATER_FLOW | Main Supply Flow | L/min | 50 | 750 | 15 | ACTIVE |
| SEN-022 | FAC-09 | SMART_METER | Active Power Demand | kW | — | 90 | 15 | ACTIVE |
| SEN-023 | FAC-10 | SMART_METER | Campus Feed Demand | kW | 250 | 1100 | 15 | ACTIVE |
| SEN-024 | FAC-11 | VEHICLE_COUNT | Vehicle Throughput | vehicles/hr | — | 400 | 15 | ACTIVE |
| SEN-025 | FAC-11 | AIR_PM25 | PM2.5 | µg/m³ | — | 90 | 15 | ACTIVE |
| SEN-026 | FAC-11 | OCCUPANCY | Footfall Count | persons | — | 500 | 15 | ACTIVE |
| SEN-027 | FAC-12 | OCCUPANCY | Occupancy Count | persons | — | 1500 | 15 | ACTIVE |
| SEN-028 | FAC-12 | SMART_METER | Floodlight Demand | kW | — | 75 | 15 | ACTIVE |

### Design Reasoning

The schema contains **28 sensors** covering five broad monitoring modalities:

1. **Energy**
2. **Water**
3. **Waste**
4. **Air quality**
5. **Traffic / Occupancy**

The `normal_upper_bound` represents a coarse operational baseline. It is useful for immediate rule-based alerts, but it is deliberately not treated as the complete anomaly-detection mechanism.

### `normal_lower_bound`

`normal_lower_bound` is optional.

For most sensors it is `NULL` because a low reading can be perfectly normal depending on the facility and time of day. For example, low activity in a hostel during certain periods is not automatically an incident.

A lower bound is provided for infrastructure where an unexpected reduction can itself indicate a failure or outage, particularly:

- Critical 24×7 infrastructure.
- Main water supply.
- Campus electrical feed.

This allows the system to detect both **abnormally high** and **abnormally low** behavior where appropriate.

### Sampling Cadence

The sensors deliberately use different sampling intervals:

- Air-quality sensors: **5 minutes**
- Energy sensors: generally **15 minutes**
- Water sensors: generally **15 minutes**
- Occupancy/traffic sensors: generally **15 minutes**
- Waste sensors: **30 minutes**

This reflects a more realistic data-engineering scenario than forcing every sensor to produce readings at the same frequency. It also affects ingestion scheduling, storage volume, aggregation logic, and forecasting granularity.

---

## 4. `sensor_readings_fact`

`sensor_readings_fact` is the central time-series fact table. Each row represents one observation produced by a sensor at a particular point in time.

### Structure

| Column | Description |
|---|---|
| `reading_id` | Unique alphanumeric identifier for the sensor reading (e.g. `RDG-SEN-001-0`). Stored as `TEXT`. |
| `recorded_at` | Time at which the reading was recorded. Stored in IST (Asia/Kolkata). |
| `sensor_id` | Foreign key identifying the sensor that produced the reading. |
| `facility_id` | Foreign key identifying the facility associated with the reading. |
| `reading_value` | Numeric value measured by the sensor. |
| `is_anomaly` | Boolean indicator showing whether the reading has been classified as anomalous. |
| `anomaly_score` | Model-generated anomaly score representing the strength/confidence of the detected anomaly. |

### Example Schema

```text
sensor_readings_fact
├── reading_id
├── recorded_at
├── sensor_id        → sensors_dim.sensor_id
├── facility_id      → facilities_dim.facility_id
├── reading_value
├── is_anomaly
└── anomaly_score
```

### Why `facility_id` Is Stored in the Fact Table

A sensor already belongs to a facility through `sensors_dim.facility_id`, so the facility can technically be derived by joining through the sensor dimension.

However, `facility_id` is intentionally duplicated in `sensor_readings_fact`.

The reason is query efficiency at scale. The fact table is expected to grow to millions of time-series records. Keeping `facility_id` directly available allows common operations such as:

- Aggregating readings by facility.
- Aggregating readings by zone through the facility dimension.
- Filtering readings for a specific facility.
- Building facility-level dashboards.
- Querying anomaly feeds by facility.

without requiring every query to first resolve the sensor-to-facility relationship.

This is a deliberate **controlled denormalization** for analytical workloads.

---

## 5. Anomaly Detection Model

The static thresholds in `sensors_dim` and the ML-based anomaly detector serve different purposes.

### Static Thresholds

`normal_upper_bound` and, where applicable, `normal_lower_bound` provide a simple baseline for immediate rule-based alerts.

For example:

```text
reading_value > normal_upper_bound
        ↓
potential threshold violation
```

This is fast, deterministic, and easy to explain, but it does not understand context.

### Context-Aware Detection

A reading can be anomalous even when it remains inside its static threshold.

The ML layer can incorporate factors such as:

- Time of day.
- Day of week.
- Historical behavior.
- Seasonal patterns.
- Correlated sensor readings.
- Facility operating schedules.
- Relationships between different resource measurements.

Possible approaches include:

- Seasonal/time-of-day models.
- Isolation Forest.
- Prophet residual analysis.
- Other time-series anomaly-detection techniques.

The purpose of this second layer is to identify **contextual anomalies**, rather than simply values that cross a fixed threshold.

### `is_anomaly` and `anomaly_score`

`is_anomaly` stores the final classification used by the application.

`anomaly_score` stores the corresponding model score so that the dashboard can communicate not only that something was flagged, but also how strongly the model considers the observation anomalous.

---

## 6. Analytical Indexing

For a large `sensor_readings_fact` table, the following indexes are appropriate for the primary access patterns:

```text
(sensor_id, recorded_at)
(facility_id, recorded_at)
```

A partial index should also be maintained for the anomaly feed:

```text
WHERE is_anomaly
```

These indexes support the most important queries:

- Retrieving a sensor's historical readings.
- Retrieving a facility's time-series data.
- Loading recent or historical anomalies efficiently.
- Building dashboard and monitoring views without scanning the complete fact table.
