"""
SafeRide AI - Module 1: Accident Detection Logic (accident_detection.py)
------------------------------------------------------------------------
Deterministic, rule-based logic that calculates an accident confidence score (%)
using a weighted combination of:
  1. Speed drop score (sudden deceleration)
  2. Impact force score (G-force accelerometer reading)
  3. Tilt abnormality score (gyroscope lean angle / rollover)

Outputs:
  - possible_accident (bool)
  - confidence_score (0.0 to 100.0)
  - severity category and sub-scores
"""

from typing import Dict, Any, List, Sequence


# Default weights for the multi-sensor heuristic fusion
WEIGHT_SPEED_DROP = 0.35
WEIGHT_IMPACT_FORCE = 0.40
WEIGHT_TILT_ABNORMALITY = 0.25

# Baseline threshold for triggering an accident alert
ACCIDENT_CONFIDENCE_THRESHOLD = 60.0  # in percent (0 - 100)


def validate_telemetry(
    speed_before: float,
    speed_after: float,
    impact_force_g: float,
    tilt_angle_deg: float,
) -> None:
    """Reject impossible phone sensor values before scoring them."""
    values = {
        "speed_before": speed_before,
        "speed_after": speed_after,
        "impact_force_g": impact_force_g,
        "tilt_angle_deg": tilt_angle_deg,
    }
    if any(not isinstance(value, (int, float)) for value in values.values()):
        raise ValueError("Telemetry values must be numeric.")
    if speed_before < 0 or speed_after < 0:
        raise ValueError("Speed values cannot be negative.")
    if impact_force_g < 0:
        raise ValueError("Impact force cannot be negative.")
    if not 0 <= tilt_angle_deg <= 180:
        raise ValueError("Tilt angle must be between 0 and 180 degrees.")


def calculate_speed_drop_score(speed_before: float, speed_after: float) -> float:
    """
    Calculates a normalized score (0 to 100) based on sudden speed loss.
    
    A sudden drop from cruising speed to near 0 within a fraction of a second
    indicates a collision or abrupt obstacle impact.
    """
    if speed_before <= 5.0:
        # Stationary or negligible movement
        return 0.0

    delta_speed = max(0.0, speed_before - speed_after)
    drop_ratio = delta_speed / speed_before

    # Base score combines absolute speed drop and relative drop ratio
    # 40 km/h sudden drop is treated as maximum threshold for 100 points
    abs_score = min(100.0, (delta_speed / 45.0) * 100.0)
    ratio_score = drop_ratio * 100.0

    # Weighting: 60% absolute drop severity, 40% ratio of speed lost
    score = (abs_score * 0.60) + (ratio_score * 0.40)
    return round(min(100.0, max(0.0, score)), 2)


def calculate_impact_score(impact_force_g: float) -> float:
    """
    Calculates a normalized score (0 to 100) based on peak G-force.
    
    Normal riding / bumps / potholes: 1.0G - 2.8G (Score ~ 0)
    Curb strikes / harsh braking: 2.8G - 3.5G (Score ~ 0-25)
    High-impact collision start: > 3.0G - 5.5G (Score ~ 25-75)
    Severe crash collision: > 5.5G - 8.5G+ (Score ~ 75-100)
    """
    if impact_force_g <= 2.8:
        return 0.0
    
    # 2.8G to 7.5G mapped linearly to 0 -> 100
    score = ((impact_force_g - 2.8) / (7.5 - 2.8)) * 100.0
    return round(min(100.0, max(0.0, score)), 2)


def calculate_tilt_score(tilt_angle_deg: float, vehicle_type: str = "Motorcycle") -> float:
    """
    Calculates a normalized score (0 to 100) based on abnormal tilt/roll angle.
    
    For two-wheelers (Motorcycle/Scooter/Bicycle):
      - 0° - 25°: Normal upright / standard cornering lean
      - 25° - 45°: Aggressive lean
      - 45° - 90°: Bike fallen on ground or sliding sideways
    
    For four-wheelers (Car/Auto-rickshaw):
      - Rollover begins beyond 30°
    """
    is_four_wheeler = vehicle_type.lower() in ["car", "auto", "auto-rickshaw", "van", "truck"]
    
    if is_four_wheeler:
        # Rollover threshold is lower for cars
        if tilt_angle_deg <= 28.0:
            return 0.0
        score = ((tilt_angle_deg - 28.0) / (65.0 - 28.0)) * 100.0
    else:
        # Two-wheelers: normal riding lean is up to 35-40 degrees
        if tilt_angle_deg <= 48.0:
            return 0.0
        score = ((tilt_angle_deg - 48.0) / (85.0 - 48.0)) * 100.0

    return round(min(100.0, max(0.0, score)), 2)


def determine_severity(confidence: float) -> str:
    """Returns human-readable severity label from confidence score."""
    if confidence < 35.0:
        return "Normal"
    elif confidence < 60.0:
        return "Low Risk / Near Miss"
    elif confidence < 75.0:
        return "Moderate Accident"
    elif confidence < 90.0:
        return "Severe Accident"
    else:
        return "Critical Impact"


def detect_accident(
    speed_before: float,
    speed_after: float,
    impact_force_g: float,
    tilt_angle_deg: float,
    vehicle_type: str = "Motorcycle",
    threshold: float = ACCIDENT_CONFIDENCE_THRESHOLD
) -> Dict[str, Any]:
    """
    Main evaluation pipeline for Module 1.
    
    Combines speed drop, impact force, and tilt abnormality into a weighted
    confidence score (0-100%).
    
    Returns:
      dict with:
        - accident_detected: bool
        - confidence: float
        - severity: str
        - scores: dict of component scores
        - telemetry_inputs: dict of raw inputs
    """
    validate_telemetry(speed_before, speed_after, impact_force_g, tilt_angle_deg)

    speed_score = calculate_speed_drop_score(speed_before, speed_after)
    impact_score = calculate_impact_score(impact_force_g)
    tilt_score = calculate_tilt_score(tilt_angle_deg, vehicle_type)

    weighted_confidence = (
        (speed_score * WEIGHT_SPEED_DROP) +
        (impact_score * WEIGHT_IMPACT_FORCE) +
        (tilt_score * WEIGHT_TILT_ABNORMALITY)
    )
    confidence = round(min(100.0, max(0.0, weighted_confidence)), 2)
    accident_detected = confidence >= threshold

    return {
        "accident_detected": accident_detected,
        "confidence": confidence,
        "severity": determine_severity(confidence),
        "scores": {
            "speed_drop_score": speed_score,
            "impact_score": impact_score,
            "tilt_score": tilt_score,
        },
        "weights": {
            "speed_drop_weight": WEIGHT_SPEED_DROP,
            "impact_force_weight": WEIGHT_IMPACT_FORCE,
            "tilt_abnormality_weight": WEIGHT_TILT_ABNORMALITY
        },
        "telemetry_inputs": {
            "speed_before_kmh": speed_before,
            "speed_after_kmh": speed_after,
            "delta_speed_kmh": round(max(0.0, speed_before - speed_after), 2),
            "impact_force_g": impact_force_g,
            "tilt_angle_deg": tilt_angle_deg,
            "vehicle_type": vehicle_type
        }
    }


def detect_accident_window(
    samples: Sequence[Dict[str, float]],
    vehicle_type: str = "Motorcycle",
    threshold: float = ACCIDENT_CONFIDENCE_THRESHOLD,
    min_confirmations: int = 2,
) -> Dict[str, Any]:
    """Confirm an accident from a short, ordered phone-sensor window.

    A single spike is treated as a warning. The incident is confirmed when at
    least ``min_confirmations`` samples cross the confidence threshold, or when
    one sample is a critical, high-force impact.
    """
    if not samples:
        raise ValueError("At least one telemetry sample is required.")
    if min_confirmations < 1:
        raise ValueError("min_confirmations must be at least 1.")

    sample_results: List[Dict[str, Any]] = []
    for sample in samples:
        required = ("speed_before", "speed_after", "impact_force_g", "tilt_angle_deg")
        missing = [field for field in required if field not in sample]
        if missing:
            raise ValueError(f"Telemetry sample is missing: {', '.join(missing)}")
        sample_results.append(
            detect_accident(
                speed_before=sample["speed_before"],
                speed_after=sample["speed_after"],
                impact_force_g=sample["impact_force_g"],
                tilt_angle_deg=sample["tilt_angle_deg"],
                vehicle_type=vehicle_type,
                threshold=threshold,
            )
        )

    peak_result = max(sample_results, key=lambda result: result["confidence"])
    confirmations = sum(result["accident_detected"] for result in sample_results)
    critical_impact = (
        peak_result["severity"] == "Critical Impact"
        and peak_result["telemetry_inputs"]["impact_force_g"] >= 5.5
    )
    confirmed = confirmations >= min_confirmations or critical_impact
    average_confidence = round(
        sum(result["confidence"] for result in sample_results) / len(sample_results),
        2,
    )

    return {
        "accident_detected": confirmed,
        "confidence": peak_result["confidence"],
        "average_confidence": average_confidence,
        "severity": peak_result["severity"],
        "confirmations": confirmations,
        "sample_count": len(sample_results),
        "confirmation_reason": (
            "critical impact" if critical_impact else "repeated sensor evidence"
        ),
        "peak_result": peak_result,
        "sample_results": sample_results,
    }


# Realistic simulation presets for testing and dashboard demo
SIMULATION_PRESETS = {
    "Normal City Riding": {
        "speed_before": 38.0,
        "speed_after": 32.0,
        "impact_force_g": 1.2,
        "tilt_angle_deg": 12.0,
        "vehicle_type": "Motorcycle",
        "expected": "Normal"
    },
    "Hard Braking (Near Miss)": {
        "speed_before": 55.0,
        "speed_after": 10.0,
        "impact_force_g": 2.1,
        "tilt_angle_deg": 18.0,
        "vehicle_type": "Motorcycle",
        "expected": "Low Risk / Near Miss"
    },
    "Low-Speed Bike Slide / Skid": {
        "speed_before": 30.0,
        "speed_after": 0.0,
        "impact_force_g": 3.4,
        "tilt_angle_deg": 78.0,
        "vehicle_type": "Scooter",
        "expected": "Moderate Accident"
    },
    "High-Speed Collision & Fall": {
        "speed_before": 68.0,
        "speed_after": 4.0,
        "impact_force_g": 6.8,
        "tilt_angle_deg": 85.0,
        "vehicle_type": "Motorcycle",
        "expected": "Critical Impact"
    }
}


if __name__ == "__main__":
    print("=== SafeRide AI - Accident Detection Test ===")
    for name, params in SIMULATION_PRESETS.items():
        result = detect_accident(
            speed_before=params["speed_before"],
            speed_after=params["speed_after"],
            impact_force_g=params["impact_force_g"],
            tilt_angle_deg=params["tilt_angle_deg"],
            vehicle_type=params["vehicle_type"]
        )
        print(f"\nScenario: {name}")
        print(f"  Confidence: {result['confidence']}% | Detected: {result['accident_detected']} | Severity: {result['severity']}")
        print(f"  Component Scores: SpeedDrop={result['scores']['speed_drop_score']}, Impact={result['scores']['impact_score']}, Tilt={result['scores']['tilt_score']}")
