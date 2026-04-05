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
from twelvelabs.core.api_error import ApiError
from twelvelabs.types import ResponseFormat, VideoContext_AssetId

from backend.config import get_settings

logger = logging.getLogger(__name__)

HEALTH_OBSERVATION_TYPES = [
    "food_dropped",
    "utensil_dropped",
    "hand_wash_short",
    "hand_wash_skipped",
    "knife_pointed_at_person",
    "knife_near_table_edge",
    "cross_contamination",
    "hand_to_face",
    "bare_hand_rte",
    "glove_not_changed",
]

EFFICIENCY_OBSERVATION_TYPES = [
    "phone_usage",
    "extended_chatting",
    "slow_task_execution",
    "idle_at_station",
    "off_task_behavior",
]

ALL_OBSERVATION_TYPES = HEALTH_OBSERVATION_TYPES + EFFICIENCY_OBSERVATION_TYPES

ANALYZE_PROMPT = (
    "You are a workplace safety inspector reviewing kitchen footage of a single employee. "
    "Watch the entire video and identify ALL safety, hygiene, and efficiency issues.\n\n"
    "The observation type must be one of:\n"
    "  food_dropped — food falls on the floor or a contaminated surface\n"
    "  utensil_dropped — a utensil falls on the floor and is reused without washing\n"
    "  hand_wash_short — hands washed for less than 20 seconds\n"
    "  hand_wash_skipped — no hand wash between tasks that require it\n"
    "  knife_pointed_at_person — knife blade directed toward another person\n"
    "  knife_near_table_edge — knife placed near the edge of a prep table\n"
    "  cross_contamination — raw food contact followed by ready-to-eat food contact without sanitation\n"
    "  hand_to_face — touching face, hair, or body then handling food without washing hands\n"
    "  bare_hand_rte — bare-hand contact with ready-to-eat food (no gloves or utensils)\n"
    "  glove_not_changed — gloves not changed between tasks or after contamination\n"
    "  phone_usage — using a personal phone during active prep or service\n"
    "  extended_chatting — social conversation that pauses work flow\n"
    "  slow_task_execution — noticeably slow cutting, chopping, or prep pace\n"
    "  idle_at_station — standing idle at an active station with work available\n"
    "  off_task_behavior — any non-work activity during active prep time\n\n"
    "For each observation, timestamp_start is when it begins and timestamp_end is when it ends. "
    "They must be different — provide the full duration, not just a single moment. "
    "If no issues are found, return an empty list."
)

RESPONSE_SCHEMA = {
    "$defs": {
        "Observation": {
            "type": "object",
            "properties": {
                "timestamp_start": {"type": "number"},
                "timestamp_end": {"type": "number"},
                "type": {"type": "string", "enum": ALL_OBSERVATION_TYPES},
                "description": {"type": "string"},
            },
            "required": ["timestamp_start", "timestamp_end", "type", "description"],
        }
    },
    "type": "object",
    "properties": {
        "observations": {
            "type": "array",
            "items": {"$ref": "#/$defs/Observation"},
        }
    },
    "required": ["observations"],
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
        for item in parsed.get("observations", []):
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

    logger.info("Parsed %d observations from Pegasus response.", len(detections))
    return raw, detections


def _explain_twelvelabs_api_error(e: ApiError) -> str:
    code = e.status_code
    body = e.body
    base = f"TwelveLabs HTTP {code}"
    if code == 403:
        return (
            f"{base} Forbidden: API key rejected or not allowed for this operation. "
            "Check: (1) key is valid in the TwelveLabs dashboard; (2) no typo in backend/.env; "
            "(3) your shell/IDE is not exporting TWELVELABS_API_KEY with a wrong or empty value "
            "(that overrides .env). "
            f"SDK detail: {e}"
        )
    if code == 401:
        return f"{base} Unauthorized (invalid or missing x-api-key). SDK detail: {e}"
    return f"{base}. SDK detail: {e}"


def run_detection_pipeline(file_path: str) -> DetectionResult:
    """
    Full pipeline: upload video -> analyze with Pegasus -> return detections.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {file_path}")

    try:
        client = _get_client()
        asset_id = upload_asset(client, file_path)
        raw_response, detections = analyze_video(client, asset_id)
    except ApiError as e:
        logger.error("TwelveLabs API error: %s", e)
        raise RuntimeError(_explain_twelvelabs_api_error(e)) from e

    logger.info("Detection pipeline complete: %d infractions found.", len(detections))

    return DetectionResult(
        asset_id=asset_id,
        raw_response=raw_response,
        detections=detections,
    )
