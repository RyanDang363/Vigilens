from __future__ import annotations

import json
import re
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.models import TrainingSource


def _json_loads(value: str, fallback):
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def normalize_title(title: str) -> str:
    base = re.sub(r"\.[^.]+$", "", title).strip()
    return base or "Untitled File"


def storage_path_for_source(source_id: str, original_name: str) -> Path:
    settings = get_settings()
    directory = Path(settings.training_storage_dir)
    directory.mkdir(parents=True, exist_ok=True)
    suffix = Path(original_name).suffix or ".bin"
    return directory / f"{source_id}{suffix}"


def infer_mime_type(filename: str, content_type: str | None) -> str:
    if content_type:
        return content_type
    suffix = Path(filename).suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }.get(suffix, "application/octet-stream")


def serialize_source(source: TrainingSource) -> dict:
    return {
        "id": source.id,
        "source_type": source.source_type,
        "title": source.title,
        "mime_type": source.mime_type,
        "owner_manager_id": source.owner_manager_id,
        "workspace_id": source.workspace_id,
        "raw_text": source.raw_text,
        "tags": _json_loads(source.tags_json, []),
        "version": source.version,
        "status": source.status,
        "active_version": bool(source.active_version),
        "created_at": source.created_at,
        "updated_at": source.updated_at,
        "last_indexed_at": source.last_indexed_at,
        "google_file_id": source.google_file_id or "",
        "source_url": source.source_url or "",
        "chunks": [],
        "rules": [],
    }


def summarize_source(source: TrainingSource) -> dict:
    return {
        "id": source.id,
        "source_type": source.source_type,
        "title": source.title,
        "mime_type": source.mime_type,
        "tags": _json_loads(source.tags_json, []),
        "workspace_id": source.workspace_id,
        "version": source.version,
        "status": source.status,
        "active_version": bool(source.active_version),
        "created_at": source.created_at,
        "last_indexed_at": source.last_indexed_at,
    }


def _source_key_for(source_type: str, title: str, workspace_id: str) -> str:
    base = normalize_title(title).lower().replace(" ", "_")
    return f"{workspace_id}:{source_type}:{base}"


def _next_version(db: Session, source_key: str) -> int:
    existing = (
        db.query(TrainingSource)
        .filter(TrainingSource.source_key == source_key)
        .order_by(TrainingSource.version.desc())
        .first()
    )
    return 1 if existing is None else existing.version + 1


def create_training_source(
    db: Session,
    *,
    source_type: str,
    title: str,
    mime_type: str,
    owner_manager_id: str,
    workspace_id: str,
    raw_text: str,
    storage_path: str = "",
) -> TrainingSource:
    source_key = _source_key_for(source_type, title, workspace_id)
    version = _next_version(db, source_key)

    (
        db.query(TrainingSource)
        .filter(
            TrainingSource.source_key == source_key,
            TrainingSource.active_version.is_(True),
        )
        .update({"active_version": False}, synchronize_session=False)
    )

    source = TrainingSource(
        id=str(uuid4()),
        source_key=source_key,
        source_type=source_type,
        title=normalize_title(title),
        mime_type=mime_type,
        owner_manager_id=owner_manager_id,
        workspace_id=workspace_id,
        raw_text=raw_text,
        tags_json="[]",
        version=version,
        status="uploaded",
        active_version=True,
        storage_path=storage_path,
    )
    db.add(source)
    db.flush()
    return source
