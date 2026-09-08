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
    rider_status: Optional[str] = Field(default=None)
    auto_dispatch: bool = Field(default=True)


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
    
    # Reverse geocode coordinates to street location
    geo_res = geo.reverse_geocode(payload.latitude, payload.longitude)
    address = geo_res.get("formatted_address", f"{payload.latitude}, {payload.longitude}")

    final_rider_status = payload.rider_status or ("NEED HELP" if detection["accident_detected"] else "PENDING_CHECK")
    final_status = "NO RESPONSE" if final_rider_status == "NO RESPONSE" else ("REPORTED" if detection["accident_detected"] else "RESOLVED")

    incident_id = db.create_incident(
        vehicle_type=payload.vehicle_type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        confidence=detection["confidence"],
        rider_status=final_rider_status,
        language=payload.language,
        message=payload.message,
        status=final_status,
        address=address,
    )

    incident_record = {
        "incident_id": incident_id,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "vehicle_type": payload.vehicle_type,
        "confidence": detection["confidence"],
        "rider_status": final_rider_status,
        "address": address,
        "status": final_status,
    }

    twilio_results = {}
    if payload.auto_dispatch and (detection["accident_detected"] or final_rider_status in ["NEED HELP", "NO RESPONSE"]):
        dest_phone = notify.EMERGENCY_DISPATCH_PHONE or "+917416960828"
        call_res = notify.trigger_emergency_call(incident_record, to_phone=dest_phone)
        sms_res = notify.send_emergency_sms(incident_record, to_phone=dest_phone)
        wa_res = notify.send_whatsapp_location(incident_record, to_phone=dest_phone, address=address)
        
        twilio_results = {
            "call": call_res,
            "sms": sms_res,
            "whatsapp": wa_res,
        }
        
        maps_link = wa_res.get('maps_link', f"https://maps.google.com/?q={payload.latitude},{payload.longitude}")
        db.add_incident_message(
            incident_id,
            "System",
            f"Automated Twilio Emergency Call & Location alert dispatched to {dest_phone}. Map: {maps_link}"
        )

    return {
        "incident_id": incident_id,
        "rider_status": final_rider_status,
        "status": final_status,
        "address": address,
        "detection": {
            "accident_detected": detection["accident_detected"],
            "confidence": detection["confidence"],
            "average_confidence": detection["average_confidence"],
            "severity": detection["severity"],
            "confirmations": detection["confirmations"],
            "confirmation_reason": detection["confirmation_reason"],
        },
        "twilio_dispatch": twilio_results,
    }


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
