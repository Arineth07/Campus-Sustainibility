"""Campus Map Data Service.

Provides spatial and facility-level context for map visualization:
- Real geographic coordinates from facilities_dim
- Linked sensor states and latest readings
- Criticality flags and zone grouping
"""

from __future__ import annotations

from typing import Any, Dict, List
from services import supabase_service
from utils.formatting import format_number, format_ist


def get_map_facilities_data() -> List[Dict[str, Any]]:
    """
    Combines facility dimension data with live sensor status and latest telemetry
    for all 12 campus facilities.
    """
    facilities = supabase_service.fetch_facilities()
    sensors = supabase_service.fetch_sensors()
    
    # Map sensors to facility
    sensors_by_facility: Dict[str, List[Dict[str, Any]]] = {}
    for s in sensors:
        fac_id = s.get("facility_id", "")
        sensors_by_facility.setdefault(fac_id, []).append(s)

    # Collect all sensor IDs to batch fetch latest readings
    all_sensor_ids = [s["sensor_id"] for s in sensors]
    latest_readings = supabase_service.fetch_latest_readings_for_sensors(all_sensor_ids)

    out: List[Dict[str, Any]] = []
    for f in facilities:
        fac_id = f["facility_id"]
        fac_sensors = sensors_by_facility.get(fac_id, [])
        
        # Determine aggregate status & anomalies for this facility
        fac_anomalies = 0
        sensor_summaries = []
        has_fault = False
        
        for s in fac_sensors:
            sid = s["sensor_id"]
            reading = latest_readings.get(sid)
            s_val = reading["reading_value"] if reading else None
            s_unit = s.get("unit", "")
            s_metric = s.get("metric_measured", "")
            s_anom = reading.get("is_anomaly", False) if reading else False
            if s_anom:
                fac_anomalies += 1
            if str(s.get("status") or "").upper() == "FAULT":
                has_fault = True
                
            val_str = f"{format_number(s_val)} {s_unit}" if s_val is not None else "N/A"
            sensor_summaries.append(f"{s_metric} ({sid}): {val_str}")

        # Operational status tone
        if has_fault or (f.get("is_critical") and fac_anomalies > 0):
            tone = "critical"
            status_label = "Critical / Alert"
        elif fac_anomalies > 0:
            tone = "warning"
            status_label = "Warning (Anomalies)"
        else:
            tone = "nominal"
            status_label = "Nominal"

        out.append(
            {
                "facility_id": fac_id,
                "facility_name": f["facility_name"],
                "facility_type": f["facility_type"],
                "zone": f["zone"],
                "latitude": float(f["latitude"]),
                "longitude": float(f["longitude"]),
                "capacity": f.get("capacity"),
                "floor_area_sqm": f.get("floor_area_sqm"),
                "operating_hours": f.get("operating_hours"),
                "is_critical": f.get("is_critical", False),
                "status_tone": tone,
                "status_label": status_label,
                "anomaly_count": fac_anomalies,
                "sensors_count": len(fac_sensors),
                "sensors_summary": "<br>".join(sensor_summaries) if sensor_summaries else "No active sensors",
            }
        )

    return out
