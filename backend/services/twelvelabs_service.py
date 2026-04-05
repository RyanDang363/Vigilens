"""
TwelveLabs Detection Layer (Simplified)

Pipeline:
  1. Upload video as Asset
  2. Call Pegasus 1.2 Analyze to identify all infractions in one pass
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from twelvelabs import TwelveLabs
from twelvelabs.types import ResponseFormat, VideoContext_AssetId

from config import get_settings

logger = logging.getLogger(__name__)

INFRACTION_TYPES = [
    "DROPPED_FOOD",
    "DROPPED_UTENSIL",
    "SLOW_CUTTING",
    "ON_PHONE",
    "EXCESSIVE_CHATTING",
    "INSUFFICIENT_HANDWASH",
    "UNSAFE_KNIFE_HANDLING",
    "UNSAFE_KNIFE_PLACEMENT",
    "CROSS_CONTAMINATION",
    "TOUCHING_FACE_OR_BODY",
]

ANALYZE_PROMPT = (
    "You are a workplace safety inspector reviewing kitchen footage of a single employee. "
    "Watch the entire video and identify ALL safety, hygiene, and efficiency infractions. "
    "The infraction type must be one of: " + ", ".join(INFRACTION_TYPES) + ". "
    "For each infraction, timestamp_start is when the infraction begins and timestamp_end is when it ends. "
    "They must be different -- provide the full duration of each infraction, not just a single moment. "
    "If no infractions are found, return an empty list."
)

RESPONSE_SCHEMA = {
    "$defs": {
        "Infraction": {
            "type": "object",
            "properties": {
                "timestamp_start": {"type": "number"},
                "timestamp_end": {"type": "number"},
                "type": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["timestamp_start", "timestamp_end", "type", "description"],
        }
    },
    "type": "object",
    "properties": {
        "infractions": {
            "type": "array",
            "items": {"$ref": "#/$defs/Infraction"},
        }
    },
    "required": ["infractions"],
}


@dataclass
class Detection:
    """A single infraction detected by Pegasus."""
    type: str
    timestamp_start: float
    timestamp_end: float
    description: str


@dataclass
class DetectionResult:
    """Full result of the detection pipeline for one video."""
    asset_id: str
    raw_response: str
    detections: list[Detection] = field(default_factory=list)


def _get_client() -> TwelveLabs:
    settings = get_settings()
    if not settings.twelvelabs_api_key:
        raise ValueError("TWELVELABS_API_KEY is not set in .env")
    return TwelveLabs(api_key=settings.twelvelabs_api_key)


def upload_asset(client: TwelveLabs, file_path: str) -> str:
    """Upload a video file to TwelveLabs as an Asset. Returns the asset ID."""
    logger.info("Uploading video asset: %s", file_path)
    asset = client.assets.create(
        method="direct",
        file=open(file_path, "rb"),
    )
    logger.info("Created asset: id=%s", asset.id)
    return asset.id


def analyze_video(client: TwelveLabs, asset_id: str) -> tuple[str, list[Detection]]:
    """
    Call Pegasus to analyze the full video and return all infractions.
    Uses response_format to get guaranteed structured JSON.
    Returns (raw_response_text, list_of_detections).
    """
    import json

    video = VideoContext_AssetId(asset_id=asset_id)
    logger.info("Analyzing video with Pegasus...")

    result = client.analyze(
        video=video,
        prompt=ANALYZE_PROMPT,
        response_format=ResponseFormat(
            type="json_schema",
            json_schema=RESPONSE_SCHEMA,
        ),
    )
    raw = result.data
    logger.info("Got response from Pegasus (%d chars)", len(raw))

    detections: list[Detection] = []
    try:
        parsed = json.loads(raw)
        for item in parsed.get("infractions", []):
            detections.append(
                Detection(
                    type=item["type"],
                    timestamp_start=float(item["timestamp_start"]),
                    timestamp_end=float(item["timestamp_end"]),
                    description=item["description"],
                )
            )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Failed to parse Pegasus response: %s", e)
        logger.warning("Raw response: %s", raw)

    logger.info("Parsed %d infractions from Pegasus response.", len(detections))
    return raw, detections


def run_detection_pipeline(file_path: str) -> DetectionResult:
    """
    Full pipeline: upload video -> analyze with Pegasus -> return detections.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {file_path}")

    client = _get_client()
    asset_id = upload_asset(client, file_path)
    raw_response, detections = analyze_video(client, asset_id)

    logger.info("Detection pipeline complete: %d infractions found.", len(detections))

    return DetectionResult(
        asset_id=asset_id,
        raw_response=raw_response,
        detections=detections,
    )
