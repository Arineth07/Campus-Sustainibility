# Campus Sustainability — Comprehensive Sensor Registry & Operational Guide

This document catalogs all **28 IoT sensors** deployed across the **12 campus facilities**, highlighting mission-critical monitoring points, operational bounds, sampling cadences, and functional roles in energy, water, waste, indoor air quality (IAQ), and transit safety.

---

## 1. Executive Summary

| Modality | Sensor Count | Sensor Types | Sampling Cadence | Primary Objective |
| :--- | :---: | :--- | :---: | :--- |
| **Energy & Power** | 11 | `SMART_METER` | 5 and 15 min | Peak load clipping, substation monitoring, baseline tracking |
| **Water Flow** | 4 | `WATER_FLOW` | 15 min | Main supply monitoring, leak detection, residential consumption |
| **Waste Management** | 3 | `WASTE_BIN` | 30 min | Dynamic collection dispatch, overflow prevention |
| **Air Quality (CO₂ & PM2.5)** | 5 | `AIR_CO2`, `AIR_PM25` | 5 and 15 min | Indoor air freshness, cognitive performance, pollution alerts |
| **Occupancy & Footfall** | 4 | `OCCUPANCY` | 15 min | Space utilization, HVAC correlation, crowd safety |
| **Transit & Vehicles** | 1 | `VEHICLE_COUNT` | 15 min | Traffic congestion, gate throughput, carbon footprint |
| **Total** | **28** | **7 distinct types** | **5, 15, 30 min** | **Comprehensive Campus Sustainability Observability** |

---

## 2. Top-Priority: Mission-Critical Infrastructure Sensors

Three sensors monitor **24×7 critical infrastructure** (`is_critical = TRUE`). Unlike standard sensors, these feature **both lower and upper bounds**. An abnormally low reading indicates failure just as an upper spike does.

| Sensor ID | Host Facility | Monitored Metric | Safe Operating Range | Sampling Cadence | Critical Risk Monitored |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **SEN-023** | Main Electrical Substation (`FAC-10`) | Campus Feed Demand | 250 kW to 1100 kW | 15 min | Campus-wide blackout or transformer overload |
| **SEN-021** | Pump House & STP (`FAC-09`) | Main Supply Flow Rate | 50 L/min to 750 L/min | 15 min | Main pump dry-run failure or trunk pipe burst |
| **SEN-008** | Central Data Center (`FAC-04`) | Active Power Demand | 80 kW to 140 kW | 5 min | Server cluster crash or cooling thermal runaway |

### Operational Breakdown of Critical Sensors

#### 1. `SEN-023` — Campus Main Feed Power Demand
* **Location**: Main Electrical Substation (`FAC-10`, Dining/Utility Zone)
* **Metric & Unit**: Active Power Demand (`kW`)
* **Cadence**: Every 15 minutes
* **Safe Baseline**: 250.0 kW to 1,100.0 kW
* **Failure Modes**:
  * **Drop Below 250 kW**: Indicates grid feeder trip, partial campus blackout, or unscheduled shutdown.
  * **Surge Above 1,100 kW**: Threatens transformer overload, grid penalty tariffs, or dangerous electrical surges.

#### 2. `SEN-021` — Campus Main Water Supply Flow
* **Location**: Pump House & STP (`FAC-09`, Dining/Utility Zone)
* **Metric & Unit**: Main Supply Flow Rate (`L/min`)
* **Cadence**: Every 15 minutes
* **Safe Baseline**: 50.0 L/min to 750.0 L/min
* **Failure Modes**:
  * **Drop Below 50 L/min**: Points to pump cavitation, motor failure, intake dry-run, or main valve blockage.
  * **Surge Above 750 L/min**: Direct indicator of trunk-line rupture, storage tank overflow, or severe underground leak.

#### 3. `SEN-008` — Central Data Center Power Load
* **Location**: Central Data Center (`FAC-04`, Academic/Admin Zone)
* **Metric & Unit**: Active Power Demand (`kW`)
* **Cadence**: Every 5 minutes (high frequency)
* **Safe Baseline**: 80.0 kW to 140.0 kW
* **Failure Modes**:
  * **Drop Below 80 kW**: Signals server rack power loss, UPS trip, or chiller plant shutdown.
  * **Surge Above 140 kW**: Indicates chiller compressor failure leading to thermal runaway or hardware overload.

---

## 3. High-Priority: Health, Safety & Air Quality Sensors

These sensors ensure compliance with national air quality benchmarks (India NAAQS) and classroom ventilation standards.

### 1. `SEN-025` — Ambient PM2.5 Particulate Concentration
* **Location**: Main Gate & Parking (`FAC-11`, Transit/Perimeter Zone)
* **Metric & Unit**: PM2.5 Fine Particulates (`µg/m³`)
* **Cadence**: Every 15 minutes | **Safe Limit**: Up to 90.0 µg/m³
* **Role**: Tracks road dust and vehicular exhaust at the main perimeter. Directly informs campus health advisories for outdoor sports and asthmatic students.

### 2. `SEN-002`, `SEN-005`, `SEN-010`, `SEN-020` — Indoor CO₂ Concentrations
* **Locations**:
  * Academic Block A (`SEN-002`): Up to 1,000 ppm
  * Central Library (`SEN-005`): Up to 1,000 ppm
  * Engineering Labs (`SEN-010`): Up to 1,000 ppm
  * Central Mess & Canteen (`SEN-020`): Up to 1,500 ppm
* **Cadence**: Every 5 minutes
* **Role**: Atmospheric baseline is ~400 ppm. Levels exceeding 1,000 ppm induce drowsiness, cognitive decline, and fatigue. In the Central Mess, higher tolerance (1,500 ppm) accounts for commercial cooking emissions.

---

## 4. Complete Directory of All 28 Campus Sensors

| Sensor ID | Facility Name | Zone | Metric Measured | Unit | Safe Range | Cadence | Operational Purpose & Work Description |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **SEN-001** | Main Academic Block A | Academic/Admin | Active Power Demand | kW | 0 to 180.0 | 15 min | Classroom lighting, projectors, and central HVAC; identifies off-hours energy waste. |
| **SEN-002** | Main Academic Block A | Academic/Admin | CO₂ Concentration | ppm | 350 to 1000.0 | 5 min | Fast-response IAQ monitor in lecture halls; prompts fresh air damper actuation. |
| **SEN-003** | Main Academic Block A | Academic/Admin | Occupancy Count | persons | 0 to 1200 | 15 min | Turnstile count; correlates classroom energy consumption against actual student presence. |
| **SEN-004** | Central Library | Academic/Admin | Active Power Demand | kW | 0 to 100.0 | 15 min | Extended-hour climate control and lighting telemetry (08:00 to 23:00). |
| **SEN-005** | Central Library | Academic/Admin | CO₂ Concentration | ppm | 350 to 1000.0 | 5 min | Ensures reading halls maintain optimal ventilation during long study sessions. |
| **SEN-006** | Central Library | Academic/Admin | Occupancy Count | persons | 0 to 700 | 15 min | Real-time seat availability indicator; prevents exam-time crowding. |
| **SEN-007** | Administration Block | Academic/Admin | Active Power Demand | kW | 0 to 75.0 | 15 min | Tracks office operating demand; detects computers and AC units left running overnight. |
| **SEN-008** | Central Data Center | Academic/Admin | Active Power Demand | kW | **80.0 to 140.0** | 5 min | **Critical 24×7**: Continuous compute rack and chiller power; catches outages and thermal spikes. |
| **SEN-009** | Engineering Labs Block | Academic/Admin | Active Power Demand | kW | 0 to 240.0 | 15 min | Monitors heavy machinery, wind tunnels, CNC equipment, and lab instrumentation. |
| **SEN-010** | Engineering Labs Block | Academic/Admin | CO₂ Concentration | ppm | 350 to 1000.0 | 5 min | Detects buildup of combustion gases and inadequate fume-hood exhaust ventilation. |
| **SEN-011** | Boys' Hostel Block 1 | Residential | Active Power Demand | kW | 0 to 110.0 | 15 min | Residential power tracking; monitors evening spikes and unauthorized high-wattage heaters. |
| **SEN-012** | Boys' Hostel Block 1 | Residential | Water Flow Rate | L/min | 0 to 150.0 | 15 min | Residential water telemetry; catches midnight pipeline leaks and running toilet valves. |
| **SEN-013** | Boys' Hostel Block 1 | Residential | Bin Fill Level | % | 0 to 85.0% | 30 min | Ultrasonic smart bin sensor; dispatches janitorial pickup before overflow occurs. |
| **SEN-014** | Girls' Hostel Block 1 | Residential | Active Power Demand | kW | 0 to 110.0 | 15 min | Residential power tracking; monitors wing lighting, room circuits, and evening patterns. |
| **SEN-015** | Girls' Hostel Block 1 | Residential | Water Flow Rate | L/min | 0 to 150.0 | 15 min | Telemetry for morning shower peaks; identifies concealed pipe leakages in bathroom risers. |
| **SEN-016** | Girls' Hostel Block 1 | Residential | Bin Fill Level | % | 0 to 85.0% | 30 min | Sanitary waste management telemetry for scheduled clearing and hygiene compliance. |
| **SEN-017** | Central Mess & Canteen | Dining/Utility | Active Power Demand | kW | 0 to 160.0 | 15 min | Commercial refrigeration, induction kitchens, dishwashers, and food warmers. |
| **SEN-018** | Central Mess & Canteen | Dining/Utility | Water Flow Rate | L/min | 0 to 120.0 | 15 min | Kitchen water monitor; flags open taps, pot-washing waste, and off-hour leaks. |
| **SEN-019** | Central Mess & Canteen | Dining/Utility | Bin Fill Level | % | 0 to 85.0% | 30 min | High-volume organic wet waste monitoring; prevents food spoilage and bin spillover. |
| **SEN-020** | Central Mess & Canteen | Dining/Utility | CO₂ Concentration | ppm | 350 to 1500.0 | 5 min | Dining hall air freshness; ensures kitchen exhaust hoods remove cooking combustion. |
| **SEN-021** | Pump House & STP | Dining/Utility | Main Supply Flow | L/min | **50.0 to 750.0** | 15 min | **Critical 24×7**: Central treated and fresh water distribution; flags pump trips and trunk bursts. |
| **SEN-022** | Pump House & STP | Dining/Utility | Active Power Demand | kW | 0 to 90.0 | 15 min | High-pressure centrifugal pumps, STP aerator blowers, and filtration motors. |
| **SEN-023** | Main Electrical Substation | Dining/Utility | Campus Feed Demand | kW | **250.0 to 1100.0** | 15 min | **Critical 24×7**: Primary campus electrical intake; detects grid outages and transformer limits. |
| **SEN-024** | Main Gate & Parking | Transit/Perimeter | Vehicle Throughput | vehicles/hr | 0 to 400 | 15 min | Automated boom barrier optical counter; logs vehicular ingress and egress during peak hours. |
| **SEN-025** | Main Gate & Parking | Transit/Perimeter | PM2.5 Concentration | µg/m³ | 0 to 90.0 | 15 min | Perimeter particulate sensor; tracks traffic pollution against national health thresholds. |
| **SEN-026** | Main Gate & Parking | Transit/Perimeter | Footfall Count | persons | 0 to 500 | 15 min | Turnstile count; logs pedestrian rush-hour flow and campus entrance congestion. |
| **SEN-027** | Sports Complex | Transit/Perimeter | Occupancy Count | persons | 0 to 1500 | 15 min | Gymnasium and indoor arena turnstile count; monitors event crowd safety. |
| **SEN-028** | Sports Complex | Transit/Perimeter | Floodlight Demand | kW | 0 to 75.0 | 15 min | High-intensity stadium and court lighting; flags accidental daytime activation. |

---

## 5. Facility-to-Sensor Mapping Matrix

| Facility ID | Facility Name | Campus Zone | Operational Schedule | Deployed Sensors |
| :--- | :--- | :--- | :---: | :--- |
| **FAC-01** | Main Academic Block A | Academic/Admin | 07:00 to 20:00 | `SEN-001` (Power), `SEN-002` (CO₂), `SEN-003` (Occupancy) |
| **FAC-02** | Central Library | Academic/Admin | 08:00 to 23:00 | `SEN-004` (Power), `SEN-005` (CO₂), `SEN-006` (Occupancy) |
| **FAC-03** | Administration Block | Academic/Admin | 09:00 to 18:00 | `SEN-007` (Power) |
| **FAC-04** | Central Data Center *(Critical)* | Academic/Admin | 24×7 | `SEN-008` (Power — Critical 24×7) |
| **FAC-05** | Engineering Labs Block | Academic/Admin | 08:00 to 19:00 | `SEN-009` (Power), `SEN-010` (CO₂) |
| **FAC-06** | Boys' Hostel Block 1 | Residential | 24×7 | `SEN-011` (Power), `SEN-012` (Water), `SEN-013` (Waste) |
| **FAC-07** | Girls' Hostel Block 1 | Residential | 24×7 | `SEN-014` (Power), `SEN-015` (Water), `SEN-016` (Waste) |
| **FAC-08** | Central Mess & Canteen | Dining/Utility | 06:00 to 23:00 | `SEN-017` (Power), `SEN-018` (Water), `SEN-019` (Waste), `SEN-020` (CO₂) |
| **FAC-09** | Pump House & STP *(Critical)* | Dining/Utility | 24×7 | `SEN-021` (Water Flow — Critical), `SEN-022` (Power) |
| **FAC-10** | Main Substation *(Critical)* | Dining/Utility | 24×7 | `SEN-023` (Campus Feed Demand — Critical) |
| **FAC-11** | Main Gate & Parking | Transit/Perimeter | 24×7 | `SEN-024` (Vehicles), `SEN-025` (PM2.5), `SEN-026` (Footfall) |
| **FAC-12** | Sports Complex | Transit/Perimeter | 06:00 to 22:00 | `SEN-027` (Occupancy), `SEN-028` (Floodlights) |

---

## 6. How the Dashboard Interprets These Readings

1. **Rule-Based Instant Alerts (Static Bounds)**:
   * Evaluated instantly upon ingestion.
   * Any reading exceeding the **Upper Bound** triggers an amber threshold alert.
   * Any reading falling below the **Lower Bound** on critical infrastructure triggers an urgent red alert.
2. **Context-Aware ML Detection (`anomaly_score`)**:
   * Scores from **0.00 to 0.35**: Normal nominal operation.
   * Scores from **0.55 to 1.00**: Flagged as anomalous (`is_anomaly = TRUE`).
   * Detects off-schedule consumption that falls inside static bounds (e.g. 45 kW classroom AC running at 03:00 AM, or hostel water spikes during lecture hours).
