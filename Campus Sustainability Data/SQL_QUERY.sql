-- ============================================================
-- Campus Sustainability Dashboard — Supabase Implementation
-- ============================================================
-- Run this entire script in Supabase SQL Editor.
-- Order matters: dimensions first, fact table last.
-- ============================================================

-- Set session timezone to IST for all timestamp operations
SET timezone = 'Asia/Kolkata';


-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE facility_type_enum AS ENUM (
    'ACADEMIC',
    'LIBRARY',
    'ADMIN',
    'DATA_CENTER',
    'LAB',
    'HOSTEL',
    'DINING',
    'UTILITY_WATER',
    'UTILITY_POWER',
    'TRANSIT',
    'SPORTS'
);

CREATE TYPE facility_zone_enum AS ENUM (
    'Academic/Admin',
    'Residential',
    'Dining/Utility',
    'Transit/Perimeter'
);

CREATE TYPE sensor_type_enum AS ENUM (
    'SMART_METER',
    'AIR_CO2',
    'AIR_PM25',
    'OCCUPANCY',
    'WATER_FLOW',
    'WASTE_BIN',
    'VEHICLE_COUNT'
);

CREATE TYPE sensor_status_enum AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'MAINTENANCE',
    'FAULT'
);


-- ============================================================
-- TABLE: facilities_dim
-- ============================================================

CREATE TABLE facilities_dim (
    facility_id         TEXT            PRIMARY KEY,            -- e.g. 'FAC-01'
    facility_name       TEXT            NOT NULL,
    facility_type       facility_type_enum NOT NULL,
    zone                facility_zone_enum NOT NULL,
    capacity            INTEGER         NOT NULL CHECK (capacity > 0),
    floor_area_sqm      NUMERIC(10, 2)  NOT NULL CHECK (floor_area_sqm > 0),
    operating_hours     TEXT            NOT NULL,               -- human-readable e.g. '07:00–20:00'
    is_critical         BOOLEAN         NOT NULL DEFAULT FALSE,
    latitude            NUMERIC(9, 6)   NOT NULL,
    longitude           NUMERIC(9, 6)   NOT NULL,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  facilities_dim               IS 'Physical and operational context of each campus facility.';
COMMENT ON COLUMN facilities_dim.facility_id   IS 'Natural key matching the schema spec (FAC-01 … FAC-12).';
COMMENT ON COLUMN facilities_dim.is_critical   IS 'TRUE for 24×7 infrastructure where abnormally LOW readings also trigger alerts.';
COMMENT ON COLUMN facilities_dim.operating_hours IS 'Human-readable schedule. Machine-schedulable logic lives in the application layer.';


-- ============================================================
-- TABLE: sensors_dim
-- ============================================================

CREATE TABLE sensors_dim (
    sensor_id               TEXT                NOT NULL PRIMARY KEY,   -- e.g. 'SEN-001'
    facility_id             TEXT                NOT NULL
                                REFERENCES facilities_dim (facility_id)
                                ON DELETE RESTRICT,
    sensor_type             sensor_type_enum    NOT NULL,
    metric_measured         TEXT                NOT NULL,
    unit                    TEXT                NOT NULL,
    normal_lower_bound      NUMERIC(12, 4)      NULL,      -- NULL = no lower-bound alert
    normal_upper_bound      NUMERIC(12, 4)      NULL,      -- NULL = upper alert not applicable
    sampling_interval_min   SMALLINT            NOT NULL CHECK (sampling_interval_min > 0),
    status                  sensor_status_enum  NOT NULL DEFAULT 'ACTIVE',
    created_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),

    -- A lower bound only makes sense when an upper bound exists or the
    -- facility is critical. Enforced at the application layer; constraint
    -- here prevents inverted bounds when both are provided.
    CONSTRAINT chk_bounds_order CHECK (
        normal_lower_bound IS NULL
        OR normal_upper_bound IS NULL
        OR normal_lower_bound < normal_upper_bound
    )
);

COMMENT ON TABLE  sensors_dim                        IS 'Sensor registry: what each sensor measures, its expected range, and cadence.';
COMMENT ON COLUMN sensors_dim.normal_lower_bound     IS 'NULL for most sensors. Set only where an unexpectedly LOW reading indicates failure (critical infrastructure, main water supply).';
COMMENT ON COLUMN sensors_dim.normal_upper_bound     IS 'Coarse static threshold for rule-based alerts. Not the sole anomaly-detection mechanism.';
COMMENT ON COLUMN sensors_dim.sampling_interval_min  IS 'Minutes between readings: 5 (air quality), 15 (energy/water/occupancy), 30 (waste).';

-- Index: join from fact table → sensors_dim by facility
CREATE INDEX idx_sensors_dim_facility_id ON sensors_dim (facility_id);


-- ============================================================
-- TABLE: sensor_readings_fact
-- ============================================================

CREATE TABLE sensor_readings_fact (
    reading_id      TEXT            PRIMARY KEY DEFAULT ('RDG-' || gen_random_uuid()), -- alphanumeric ID e.g. 'RDG-SEN-001-0', auto-generated if omitted
    recorded_at     TIMESTAMPTZ     NOT NULL,               -- stored in IST (Asia/Kolkata)
    sensor_id       TEXT            NOT NULL
                        REFERENCES sensors_dim (sensor_id)
                        ON DELETE RESTRICT,
    facility_id     TEXT            NOT NULL
                        REFERENCES facilities_dim (facility_id)
                        ON DELETE RESTRICT,                 -- denormalised for query efficiency at scale
    reading_value   NUMERIC(14, 4)  NOT NULL,
    is_anomaly      BOOLEAN         NOT NULL DEFAULT FALSE,
    anomaly_score   NUMERIC(6, 4)   NULL                    -- NULL until ML layer processes the row
                        CHECK (anomaly_score IS NULL OR (anomaly_score >= 0 AND anomaly_score <= 1))
);

COMMENT ON TABLE  sensor_readings_fact             IS 'Central time-series fact table. One row per sensor observation.';
COMMENT ON COLUMN sensor_readings_fact.reading_id   IS 'Unique observation identifier, matching natural telemetry keys (e.g. RDG-SEN-001-0) or auto-generated UUID.';
COMMENT ON COLUMN sensor_readings_fact.facility_id IS 'Denormalised from sensors_dim for efficient facility-level aggregation without an extra join.';
COMMENT ON COLUMN sensor_readings_fact.recorded_at IS 'IST (Asia/Kolkata, UTC+5:30). All timestamps in this system use Indian Standard Time.';
COMMENT ON COLUMN sensor_readings_fact.anomaly_score IS '0–1 ML confidence score. NULL until the anomaly-detection job processes the row.';

-- Primary access pattern indexes (from schema spec)
CREATE INDEX idx_readings_sensor_time
    ON sensor_readings_fact (sensor_id, recorded_at DESC);

CREATE INDEX idx_readings_facility_time
    ON sensor_readings_fact (facility_id, recorded_at DESC);

-- Partial index for anomaly feed — only indexes flagged rows
CREATE INDEX idx_readings_anomaly
    ON sensor_readings_fact (facility_id, recorded_at DESC)
    WHERE is_anomaly = TRUE;


-- ============================================================
-- TRIGGER: keep updated_at current on dimension tables
-- ============================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_facilities_updated_at
    BEFORE UPDATE ON facilities_dim
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_sensors_updated_at
    BEFORE UPDATE ON sensors_dim
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- SEED: facilities_dim
-- ============================================================

INSERT INTO facilities_dim
    (facility_id, facility_name, facility_type, zone, capacity, floor_area_sqm, operating_hours, is_critical, latitude, longitude)
VALUES
    ('FAC-01', 'Main Academic Block A',      'ACADEMIC',       'Academic/Admin',     1200, 8500,  '07:00–20:00', FALSE, 18.521000, 73.856200),
    ('FAC-02', 'Central Library',            'LIBRARY',        'Academic/Admin',      800, 6000,  '08:00–23:00', FALSE, 18.521400, 73.856700),
    ('FAC-03', 'Administration Block',       'ADMIN',          'Academic/Admin',      300, 3200,  '09:00–18:00', FALSE, 18.520800, 73.857000),
    ('FAC-04', 'Central Data Center',        'DATA_CENTER',    'Academic/Admin',       15,  400,  '24×7',        TRUE,  18.520600, 73.856900),
    ('FAC-05', 'Engineering Labs Block',     'LAB',            'Academic/Admin',      900, 7200,  '08:00–19:00', FALSE, 18.521200, 73.855800),
    ('FAC-06', 'Boys'' Hostel Block 1',      'HOSTEL',         'Residential',         600, 9000,  '24×7',        FALSE, 18.519500, 73.857500),
    ('FAC-07', 'Girls'' Hostel Block 1',     'HOSTEL',         'Residential',         500, 8000,  '24×7',        FALSE, 18.519200, 73.858000),
    ('FAC-08', 'Central Mess & Canteen',     'DINING',         'Dining/Utility',     1000, 3500,  '06:00–23:00', FALSE, 18.519800, 73.857800),
    ('FAC-09', 'Pump House & STP',           'UTILITY_WATER',  'Dining/Utility',       10, 1200,  '24×7',        TRUE,  18.518800, 73.855500),
    ('FAC-10', 'Main Electrical Substation', 'UTILITY_POWER',  'Dining/Utility',        8,  800,  '24×7',        TRUE,  18.520200, 73.855200),
    ('FAC-11', 'Main Gate & Parking',        'TRANSIT',        'Transit/Perimeter',  2000, 5000,  '24×7',        FALSE, 18.522000, 73.854800),
    ('FAC-12', 'Sports Complex',             'SPORTS',         'Transit/Perimeter',  1500, 20000, '06:00–22:00', FALSE, 18.518500, 73.859000);


-- ============================================================
-- SEED: sensors_dim
-- ============================================================

INSERT INTO sensors_dim
    (sensor_id, facility_id, sensor_type, metric_measured, unit, normal_lower_bound, normal_upper_bound, sampling_interval_min, status)
VALUES
    -- FAC-01 Academic Block A
    ('SEN-001', 'FAC-01', 'SMART_METER',   'Active Power Demand',  'kW',          NULL,  180,  15, 'ACTIVE'),
    ('SEN-002', 'FAC-01', 'AIR_CO2',       'CO₂ Concentration',    'ppm',         NULL, 1000,   5, 'ACTIVE'),
    ('SEN-003', 'FAC-01', 'OCCUPANCY',     'Occupancy Count',      'persons',     NULL, 1200,  15, 'ACTIVE'),

    -- FAC-02 Central Library
    ('SEN-004', 'FAC-02', 'SMART_METER',   'Active Power Demand',  'kW',          NULL,  100,  15, 'ACTIVE'),
    ('SEN-005', 'FAC-02', 'AIR_CO2',       'CO₂ Concentration',    'ppm',         NULL, 1000,   5, 'ACTIVE'),
    ('SEN-006', 'FAC-02', 'OCCUPANCY',     'Occupancy Count',      'persons',     NULL,  700,  15, 'ACTIVE'),

    -- FAC-03 Administration Block
    ('SEN-007', 'FAC-03', 'SMART_METER',   'Active Power Demand',  'kW',          NULL,   75,  15, 'ACTIVE'),

    -- FAC-04 Central Data Center (critical — has lower bound)
    ('SEN-008', 'FAC-04', 'SMART_METER',   'Active Power Demand',  'kW',            80,  140,   5, 'ACTIVE'),

    -- FAC-05 Engineering Labs
    ('SEN-009', 'FAC-05', 'SMART_METER',   'Active Power Demand',  'kW',          NULL,  240,  15, 'ACTIVE'),
    ('SEN-010', 'FAC-05', 'AIR_CO2',       'CO₂ Concentration',    'ppm',         NULL, 1000,   5, 'ACTIVE'),

    -- FAC-06 Boys Hostel
    ('SEN-011', 'FAC-06', 'SMART_METER',   'Active Power Demand',  'kW',          NULL,  110,  15, 'ACTIVE'),
    ('SEN-012', 'FAC-06', 'WATER_FLOW',    'Water Flow Rate',      'L/min',       NULL,  150,  15, 'ACTIVE'),
    ('SEN-013', 'FAC-06', 'WASTE_BIN',     'Bin Fill Level',       '%',           NULL,   85,  30, 'ACTIVE'),

    -- FAC-07 Girls Hostel
    ('SEN-014', 'FAC-07', 'SMART_METER',   'Active Power Demand',  'kW',          NULL,  110,  15, 'ACTIVE'),
    ('SEN-015', 'FAC-07', 'WATER_FLOW',    'Water Flow Rate',      'L/min',       NULL,  150,  15, 'ACTIVE'),
    ('SEN-016', 'FAC-07', 'WASTE_BIN',     'Bin Fill Level',       '%',           NULL,   85,  30, 'ACTIVE'),

    -- FAC-08 Central Mess & Canteen
    ('SEN-017', 'FAC-08', 'SMART_METER',   'Active Power Demand',  'kW',          NULL,  160,  15, 'ACTIVE'),
    ('SEN-018', 'FAC-08', 'WATER_FLOW',    'Water Flow Rate',      'L/min',       NULL,  120,  15, 'ACTIVE'),
    ('SEN-019', 'FAC-08', 'WASTE_BIN',     'Bin Fill Level',       '%',           NULL,   85,  30, 'ACTIVE'),
    ('SEN-020', 'FAC-08', 'AIR_CO2',       'CO₂ Concentration',    'ppm',         NULL, 1500,   5, 'ACTIVE'),

    -- FAC-09 Pump House & STP (critical — has lower bound)
    ('SEN-021', 'FAC-09', 'WATER_FLOW',    'Main Supply Flow',     'L/min',         50,  750,  15, 'ACTIVE'),
    ('SEN-022', 'FAC-09', 'SMART_METER',   'Active Power Demand',  'kW',          NULL,   90,  15, 'ACTIVE'),

    -- FAC-10 Main Electrical Substation (critical — has lower bound)
    ('SEN-023', 'FAC-10', 'SMART_METER',   'Campus Feed Demand',   'kW',           250, 1100,  15, 'ACTIVE'),

    -- FAC-11 Main Gate & Parking
    ('SEN-024', 'FAC-11', 'VEHICLE_COUNT', 'Vehicle Throughput',   'vehicles/hr', NULL,  400,  15, 'ACTIVE'),
    ('SEN-025', 'FAC-11', 'AIR_PM25',      'PM2.5',                'µg/m³',       NULL,   90,  15, 'ACTIVE'),
    ('SEN-026', 'FAC-11', 'OCCUPANCY',     'Footfall Count',       'persons',     NULL,  500,  15, 'ACTIVE'),

    -- FAC-12 Sports Complex
    ('SEN-027', 'FAC-12', 'OCCUPANCY',     'Occupancy Count',      'persons',     NULL, 1500,  15, 'ACTIVE'),
    ('SEN-028', 'FAC-12', 'SMART_METER',   'Floodlight Demand',    'kW',          NULL,   75,  15, 'ACTIVE');


-- ============================================================
-- USEFUL VIEWS
-- ============================================================

-- Full sensor context (the join you'll run constantly)
CREATE OR REPLACE VIEW v_sensor_full AS
SELECT
    s.sensor_id,
    s.sensor_type,
    s.metric_measured,
    s.unit,
    s.normal_lower_bound,
    s.normal_upper_bound,
    s.sampling_interval_min,
    s.status,
    f.facility_id,
    f.facility_name,
    f.facility_type,
    f.zone,
    f.is_critical,
    f.latitude,
    f.longitude
FROM sensors_dim     s
JOIN facilities_dim  f ON f.facility_id = s.facility_id;

-- Recent anomalies (last 24 h) — drives the alert feed
CREATE OR REPLACE VIEW v_recent_anomalies AS
SELECT
    r.reading_id,
    r.recorded_at,
    r.reading_value,
    r.anomaly_score,
    s.sensor_id,
    s.sensor_type,
    s.metric_measured,
    s.unit,
    f.facility_id,
    f.facility_name,
    f.zone,
    f.is_critical
FROM sensor_readings_fact r
JOIN sensors_dim          s ON s.sensor_id    = r.sensor_id
JOIN facilities_dim       f ON f.facility_id  = r.facility_id
WHERE r.is_anomaly = TRUE
  AND r.recorded_at  >= NOW() - INTERVAL '24 hours'
ORDER BY r.recorded_at DESC;

-- Per-facility hourly energy summary
CREATE OR REPLACE VIEW v_hourly_energy AS
SELECT
    date_trunc('hour', r.recorded_at)  AS hour,
    r.facility_id,
    f.facility_name,
    f.zone,
    AVG(r.reading_value)             AS avg_kw,
    MAX(r.reading_value)             AS peak_kw,
    COUNT(*)                         AS reading_count
FROM sensor_readings_fact r
JOIN facilities_dim       f ON f.facility_id = r.facility_id
JOIN sensors_dim          s ON s.sensor_id   = r.sensor_id
WHERE s.sensor_type = 'SMART_METER'
GROUP BY 1, 2, 3, 4;


-- ============================================================
-- ROW LEVEL SECURITY (Supabase standard)
-- ============================================================
-- Dimension tables are read-only for authenticated users.
-- Fact table inserts come from your ingestion service role only.

ALTER TABLE facilities_dim          ENABLE ROW LEVEL SECURITY;
ALTER TABLE sensors_dim             ENABLE ROW LEVEL SECURITY;
ALTER TABLE sensor_readings_fact    ENABLE ROW LEVEL SECURITY;

-- Authenticated users and public dashboard visitors (anon) can SELECT
CREATE POLICY "public and authenticated read facilities"
    ON facilities_dim FOR SELECT
    TO anon, authenticated
    USING (TRUE);

CREATE POLICY "public and authenticated read sensors"
    ON sensors_dim FOR SELECT
    TO anon, authenticated
    USING (TRUE);

CREATE POLICY "public and authenticated read readings"
    ON sensor_readings_fact FOR SELECT
    TO anon, authenticated
    USING (TRUE);

-- Only the service role can INSERT/UPDATE/DELETE
-- (Supabase service_role bypasses RLS by default — no extra policy needed)