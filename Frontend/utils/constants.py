"""Dashboard constants. Sensor IDs match the implemented sensors_dim seed."""

from __future__ import annotations

IST_TZ = "Asia/Kolkata"

# Campus-level meters ? do not sum all SMART_METER / WATER_FLOW sensors.
CAMPUS_FEED_SENSOR_ID = "SEN-023"
MAIN_WATER_SENSOR_ID = "SEN-021"

PAGE_SIZE = 1000
MAX_READING_ROWS = 12000
ANOMALY_TABLE_LIMIT = 75

METRIC_CATALOG = {
    "power": {
        "label": "Campus power demand",
        "unit": "kW",
        "sensor_type": "SMART_METER",
        "sensor_ids": (CAMPUS_FEED_SENSOR_ID,),
        "use_campus_feed_only": True,
    },
    "water": {
        "label": "Main water flow",
        "unit": "L/min",
        "sensor_type": "WATER_FLOW",
        "sensor_ids": (MAIN_WATER_SENSOR_ID,),
        "use_campus_feed_only": True,
    },
    "waste": {
        "label": "Waste fill",
        "unit": "%",
        "sensor_type": "WASTE_BIN",
        "sensor_ids": None,
        "use_campus_feed_only": False,
    },
    "co2": {
        "label": "CO\u2082 concentration",
        "unit": "ppm",
        "sensor_type": "AIR_CO2",
        "sensor_ids": None,
        "use_campus_feed_only": False,
    },
    "pm25": {
        "label": "PM2.5",
        "unit": "\u00b5g/m\u00b3",
        "sensor_type": "AIR_PM25",
        "sensor_ids": None,
        "use_campus_feed_only": False,
    },
    "occupancy": {
        "label": "Occupancy",
        "unit": "persons",
        "sensor_type": "OCCUPANCY",
        "sensor_ids": None,
        "use_campus_feed_only": False,
    },
    "vehicles": {
        "label": "Vehicle throughput",
        "unit": "vehicles/hr",
        "sensor_type": "VEHICLE_COUNT",
        "sensor_ids": None,
        "use_campus_feed_only": False,
    },
}

TIME_RANGE_HOURS = {
    "24h": 24,
    "7d": 24 * 7,
    "30d": 24 * 30,
    "full": None,
}

NAV_ITEMS = [
    {"label": "Overview", "path": "/"},
    {"label": "Energy", "path": "/energy"},
    {"label": "Water", "path": "/water"},
    {"label": "Waste Operations", "path": "/waste"},
    {"label": "Campus Map", "path": "/map"},
    {"label": "Sensors", "path": "/sensors"},
    {"label": "Environment", "path": "/environment"},
    {"label": "Alerts", "path": "/alerts"},
    {"label": "Data Explorer", "path": "/explorer"},
]

