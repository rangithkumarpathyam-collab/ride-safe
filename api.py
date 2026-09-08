"""SafeRide incident API used by the native rider app."""

import os
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import accident_detection as ad
import database as db
import geocoding as geo
import notifications as notify

load_dotenv()

API_TOKEN = os.getenv("SAFERIDE_API_TOKEN", "").strip()

app = FastAPI(title="SafeRide Incident API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
)


class TelemetrySample(BaseModel):
    speed_before: float = Field(ge=0, le=300)
    speed_after: float = Field(ge=0, le=300)
    impact_force_g: float = Field(ge=0, le=30)
    tilt_angle_deg: float = Field(ge=0, le=180)


class IncidentRequest(BaseModel):
    vehicle_type: str = Field(default="Motorcycle", min_length=2, max_length=40)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    samples: List[TelemetrySample] = Field(min_length=1, max_length=30)
    language: str = Field(default="English", min_length=2, max_length=20)
    message: str = Field(
        default="Possible crash detected. Please send help to my location.",
        max_length=500,
    )
    trigger_call: bool = Field(default=True)
    emergency_phone: Optional[str] = Field(default=None, max_length=40)


class LocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed_kmh: float = Field(default=0, ge=0, le=300)
    recorded_at: Optional[str] = Field(default=None, max_length=40)


def require_api_access(authorization: Optional[str]) -> None:
    """Require a bearer token when one is configured for the server."""
    if not API_TOKEN:
        return
    expected = f"Bearer {API_TOKEN}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Authentication required")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "saferide-incident-api"}


@app.post("/api/v1/incidents")
def create_incident(payload: IncidentRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    require_api_access(authorization)
    db.init_db(seed_sample_data=False)

    detection = ad.detect_accident_window(
        [sample.model_dump() for sample in payload.samples],
        vehicle_type=payload.vehicle_type,
    )
    rider_status = "NEED HELP" if detection["accident_detected"] else "PENDING_CHECK"

    geo_info = geo.reverse_geocode(payload.latitude, payload.longitude)
    address = geo_info.get("formatted_address") or f"Zone ({payload.latitude}, {payload.longitude})"

    incident_id = db.create_incident(
        vehicle_type=payload.vehicle_type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        confidence=detection["confidence"],
        rider_status=rider_status,
        language=payload.language,
        message=payload.message,
        status="REPORTED",
    )

    emergency_call_result = None
    sms_result = None
    target_phone = payload.emergency_phone or notify.EMERGENCY_DISPATCH_PHONE

    # Trigger Twilio Voice Call and SMS if requested (default True for emergency dispatch)
    if payload.trigger_call:
        incident_data = {
            "incident_id": incident_id,
            "vehicle_type": payload.vehicle_type,
            "confidence": detection["confidence"],
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "rider_status": rider_status,
            "city": address,
        }
        emergency_call_result = notify.trigger_emergency_call(incident_data, to_phone=target_phone)
        sms_result = notify.send_emergency_sms(incident_data, to_phone=target_phone)
        notify.send_whatsapp_location(incident_data, to_phone=target_phone, address=address)

        call_status = "Dispatched" if emergency_call_result.get("success") else f"Notice ({emergency_call_result.get('error')})"
        db.add_incident_message(
            incident_id,
            "System",
            f"📞 Automated Emergency Call to {target_phone}: {call_status} (SID: {emergency_call_result.get('sid', 'N/A')})"
        )

    return {
        "incident_id": incident_id,
        "rider_status": rider_status,
        "address": address,
        "emergency_call": emergency_call_result,
        "sms": sms_result,
        "target_phone": target_phone,
        "detection": {
            "accident_detected": detection["accident_detected"],
            "confidence": detection["confidence"],
            "average_confidence": detection["average_confidence"],
            "severity": detection["severity"],
            "confirmations": detection["confirmations"],
            "confirmation_reason": detection["confirmation_reason"],
        },
    }


@app.post("/api/v1/incidents/{incident_id}/call")
def dispatch_incident_call(
    incident_id: str,
    to_phone: Optional[str] = None,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Explicitly trigger an automated Twilio voice call for an existing incident."""
    require_api_access(authorization)
    incident = db.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    geo_info = geo.reverse_geocode(incident["latitude"], incident["longitude"])
    address = geo_info.get("formatted_address") or f"Zone ({incident['latitude']}, {incident['longitude']})"
    target = to_phone or notify.EMERGENCY_DISPATCH_PHONE
    call_result = notify.trigger_emergency_call(dict(incident), to_phone=target)
    db.add_incident_message(
        incident_id,
        "System",
        f"📞 Emergency Call dispatched to {target}: {call_result.get('status', 'queued')} (SID: {call_result.get('sid', 'N/A')})"
    )
    return {"incident_id": incident_id, "call": call_result}


@app.put("/api/v1/incidents/{incident_id}/location")
def update_incident_location(
    incident_id: str,
    payload: LocationUpdate,
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """Store the latest GPS position for an active incident."""
    require_api_access(authorization)
    db.init_db(seed_sample_data=False)
    updated = db.update_incident(
        incident_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {
        "incident_id": incident_id,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "speed_kmh": payload.speed_kmh,
        "recorded_at": payload.recorded_at,
    }
