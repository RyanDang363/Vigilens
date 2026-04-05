"""FastAPI backend for the dashboard."""

import logging
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import FastAPI, Depends, File, Form, Header, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import engine, get_db, Base
from backend.config import describe_twelvelabs_config_for_logs, get_settings
from backend.models import BrowserActionLog, Employee, Finding, Report, TrainingSource
from backend.schemas import (
    EmployeeCreate,
    EmployeeOut,
    ReportCreate,
    ReportOut,
    ReportSummary,
    TrainingSourceOut,
    TrainingSourceSummary,
    TrainingUploadResponse,
)
from backend.services.training_service import (
    create_training_source,
    infer_mime_type,
    normalize_title,
    serialize_source,
    storage_path_for_source,
    summarize_source,
)
from backend.services.twelvelabs_service import (
    HEALTH_OBSERVATION_TYPES,
    EFFICIENCY_OBSERVATION_TYPES,
    run_detection_pipeline,
)

logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Workplace Safety Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _log_twelvelabs_startup() -> None:
    logger.info("Startup: %s", describe_twelvelabs_config_for_logs())


def require_manager(x_role: str = Header(default="manager")) -> str:
    if x_role != "manager":
        raise HTTPException(status_code=403, detail="Manager access required")
    return "manager_demo"


def current_workspace_id() -> str:
    return "workspace_demo"


def _get_training_source_or_404(db: Session, source_id: str) -> TrainingSource:
    source = db.query(TrainingSource).filter(TrainingSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Training source not found")
    return source


def _training_storage_dir() -> Path:
    directory = Path(get_settings().training_storage_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _training_trash_dir() -> Path:
    directory = _training_storage_dir() / ".trash"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _filesystem_source_id(filename: str) -> str:
    return f"fs::{filename}"


def _filesystem_source_payload(path: Path) -> dict:
    created_at = datetime.fromtimestamp(path.stat().st_mtime)
    return {
        "id": _filesystem_source_id(path.name),
        "source_type": "upload",
        "title": normalize_title(path.name),
        "mime_type": infer_mime_type(path.name, None),
        "owner_manager_id": "manager_demo",
        "workspace_id": current_workspace_id(),
        "raw_text": "",
        "tags": [],
        "version": 1,
        "status": "uploaded",
        "active_version": True,
        "created_at": created_at,
        "updated_at": created_at,
        "last_indexed_at": None,
        "google_file_id": "",
        "source_url": "",
        "chunks": [],
        "rules": [],
    }


def _resolve_training_file(source_id: str, db: Session) -> tuple[dict, Path]:
    if source_id.startswith("fs::"):
        filename = source_id.removeprefix("fs::")
        path = _training_storage_dir() / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="Stored file is missing")
        return _filesystem_source_payload(path), path

    source = _get_training_source_or_404(db, source_id)
    if not source.storage_path:
        raise HTTPException(status_code=404, detail="No stored file found for this source")
    path = Path(source.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")
    return serialize_source(source), path


def _move_to_trash(path: Path) -> Path:
    target = _training_trash_dir() / path.name
    if target.exists():
        target = _training_trash_dir() / f"{uuid4()}-{path.name}"
    shutil.move(str(path), str(target))
    return target


def _restore_from_trash(path: Path) -> Path:
    target = _training_storage_dir() / path.name
    if target.exists():
        target = _training_storage_dir() / f"{uuid4()}-{path.name}"
    shutil.move(str(path), str(target))
    return target


# --- Training Library ---

@app.get("/api/training", response_model=list[TrainingSourceSummary])
def list_training_sources(
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    all_sources = (
        db.query(TrainingSource)
        .filter(TrainingSource.owner_manager_id == manager_id)
        .order_by(TrainingSource.created_at.desc())
        .all()
    )
    sources = [
        source
        for source in all_sources
        if not source.storage_path or Path(source.storage_path).parent != _training_trash_dir()
    ]
    items = [summarize_source(source) for source in sources]
    referenced_names = {
        Path(source.storage_path).name
        for source in sources
        if source.storage_path
    }

    for path in _training_storage_dir().iterdir():
        if not path.is_file() or path.name in referenced_names:
            continue
        payload = _filesystem_source_payload(path)
        items.append(
            {
                "id": payload["id"],
                "source_type": payload["source_type"],
                "title": payload["title"],
                "mime_type": payload["mime_type"],
                "tags": payload["tags"],
                "workspace_id": payload["workspace_id"],
                "version": payload["version"],
                "status": payload["status"],
                "active_version": payload["active_version"],
                "created_at": payload["created_at"],
                "last_indexed_at": payload["last_indexed_at"],
            }
        )

    items.sort(key=lambda item: item["created_at"] or datetime.min, reverse=True)
    return items


@app.get("/api/training/trash", response_model=list[TrainingSourceSummary])
def list_trashed_training_sources(
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    sources = (
        db.query(TrainingSource)
        .filter(TrainingSource.owner_manager_id == manager_id)
        .order_by(TrainingSource.created_at.desc())
        .all()
    )

    items: list[dict] = []
    for source in sources:
        if not source.storage_path:
            continue
        path = Path(source.storage_path)
        if path.parent != _training_trash_dir():
            continue
        items.append(summarize_source(source))

    referenced_names = {
        Path(source.storage_path).name
        for source in sources
        if source.storage_path
    }

    for path in _training_trash_dir().iterdir():
        if not path.is_file() or path.name in referenced_names:
            continue
        payload = _filesystem_source_payload(path)
        items.append(
            {
                "id": payload["id"],
                "source_type": payload["source_type"],
                "title": payload["title"],
                "mime_type": payload["mime_type"],
                "tags": payload["tags"],
                "workspace_id": payload["workspace_id"],
                "version": payload["version"],
                "status": payload["status"],
                "active_version": payload["active_version"],
                "created_at": payload["created_at"],
                "last_indexed_at": payload["last_indexed_at"],
            }
        )

    items.sort(key=lambda item: item["created_at"] or datetime.min, reverse=True)
    return items


@app.get("/api/training/{source_id}", response_model=TrainingSourceOut)
def get_training_source(
    source_id: str,
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    payload, _ = _resolve_training_file(source_id, db)
    if payload["owner_manager_id"] != manager_id:
        raise HTTPException(status_code=403, detail="Manager access required")
    return payload


@app.get("/api/training/{source_id}/file")
def get_training_source_file(
    source_id: str,
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    payload, path = _resolve_training_file(source_id, db)
    if payload["owner_manager_id"] != manager_id:
        raise HTTPException(status_code=403, detail="Manager access required")

    return FileResponse(
        path,
        media_type=payload["mime_type"],
        filename=path.name,
        content_disposition_type="inline",
    )


@app.post("/api/training/{source_id}/trash")
def trash_training_source(
    source_id: str,
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    if source_id.startswith("fs::"):
        filename = source_id.removeprefix("fs::")
        path = _training_storage_dir() / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="Stored file is missing")
        trashed = _move_to_trash(path)
        return {"id": _filesystem_source_id(trashed.name), "message": "File moved to trash."}

    source = _get_training_source_or_404(db, source_id)
    if source.owner_manager_id != manager_id:
        raise HTTPException(status_code=403, detail="Manager access required")
    if not source.storage_path:
        raise HTTPException(status_code=404, detail="No stored file found for this source")
    path = Path(source.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file is missing")

    trashed = _move_to_trash(path)
    source.storage_path = str(trashed)
    db.commit()
    return {"id": source.id, "message": "File moved to trash."}


@app.post("/api/training/{source_id}/restore")
def restore_training_source(
    source_id: str,
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    if source_id.startswith("fs::"):
        filename = source_id.removeprefix("fs::")
        path = _training_trash_dir() / filename
        if not path.exists():
            raise HTTPException(status_code=404, detail="Trashed file is missing")
        restored = _restore_from_trash(path)
        return {"id": _filesystem_source_id(restored.name), "message": "File restored."}

    source = _get_training_source_or_404(db, source_id)
    if source.owner_manager_id != manager_id:
        raise HTTPException(status_code=403, detail="Manager access required")
    if not source.storage_path:
        raise HTTPException(status_code=404, detail="No stored file found for this source")
    path = Path(source.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Trashed file is missing")

    restored = _restore_from_trash(path)
    source.storage_path = str(restored)
    db.commit()
    return {"id": source.id, "message": "File restored."}


@app.post("/api/training/upload", response_model=TrainingUploadResponse)
def upload_training_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    filename = file.filename or "upload.bin"
    mime_type = infer_mime_type(filename, file.content_type)
    source_id = str(uuid4())
    storage_path = storage_path_for_source(source_id, filename)

    with storage_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)

    source = create_training_source(
        db,
        source_type="upload",
        title=filename,
        mime_type=mime_type,
        owner_manager_id=manager_id,
        workspace_id=current_workspace_id(),
        raw_text="",
        storage_path=str(storage_path),
    )
    source.id = source_id
    db.commit()
    db.refresh(source)

    return TrainingUploadResponse(
        source=serialize_source(source),
        message="File uploaded successfully.",
    )

# --- Employees ---

@app.get("/api/employees", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    result = []
    for emp in employees:
        findings_count = (
            db.query(Finding)
            .join(Report)
            .filter(Report.employee_id == emp.id)
            .count()
        )
        reports_count = db.query(Report).filter(Report.employee_id == emp.id).count()

        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        highest = "low"
        for report in emp.reports:
            if severity_order.get(report.highest_severity, 0) > severity_order.get(highest, 0):
                highest = report.highest_severity

        result.append(EmployeeOut(
            id=emp.id,
            name=emp.name,
            role=emp.role,
            station=emp.station,
            start_date=emp.start_date,
            total_findings=findings_count,
            total_reports=reports_count,
            highest_severity=highest,
        ))
    return result


@app.get("/api/employees/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: str, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    findings_count = (
        db.query(Finding).join(Report).filter(Report.employee_id == emp.id).count()
    )
    reports_count = db.query(Report).filter(Report.employee_id == emp.id).count()

    severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    highest = "low"
    for report in emp.reports:
        if severity_order.get(report.highest_severity, 0) > severity_order.get(highest, 0):
            highest = report.highest_severity

    return EmployeeOut(
        id=emp.id,
        name=emp.name,
        role=emp.role,
        station=emp.station,
        start_date=emp.start_date,
        total_findings=findings_count,
        total_reports=reports_count,
        highest_severity=highest,
    )


@app.post("/api/employees", response_model=EmployeeOut)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    existing = db.query(Employee).filter(Employee.id == data.id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Employee already exists")
    emp = Employee(**data.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return EmployeeOut(
        id=emp.id,
        name=emp.name,
        role=emp.role,
        station=emp.station,
        start_date=emp.start_date,
        total_findings=0,
        total_reports=0,
        highest_severity="low",
    )


def _delete_employee_cascade(db: Session, employee_id: str) -> None:
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    reports = db.query(Report).filter(Report.employee_id == employee_id).all()
    for r in reports:
        db.query(Finding).filter(Finding.report_id == r.id).delete()
    db.query(Report).filter(Report.employee_id == employee_id).delete()
    db.delete(emp)
    db.commit()


@app.delete("/api/employees/{employee_id}", status_code=204)
def delete_employee(employee_id: str, db: Session = Depends(get_db)):
    _delete_employee_cascade(db, employee_id)
    return Response(status_code=204)


@app.post("/api/employees/{employee_id}/delete", status_code=204)
def delete_employee_post(employee_id: str, db: Session = Depends(get_db)):
    """Same as DELETE; POST avoids 405 from proxies or clients that omit the path id."""
    _delete_employee_cascade(db, employee_id)
    return Response(status_code=204)


# --- Reports ---

@app.get("/api/employees/{employee_id}/reports", response_model=list[ReportSummary])
def list_reports_for_employee(employee_id: str, db: Session = Depends(get_db)):
    reports = (
        db.query(Report)
        .filter(Report.employee_id == employee_id)
        .order_by(Report.created_at.desc())
        .all()
    )
    result = []
    for r in reports:
        total = db.query(Finding).filter(Finding.report_id == r.id).count()
        result.append(ReportSummary(
            id=r.id,
            clip_id=r.clip_id,
            created_at=r.created_at,
            highest_severity=r.highest_severity,
            code_backed_count=r.code_backed_count,
            guidance_count=r.guidance_count,
            efficiency_count=r.efficiency_count,
            total_findings=total,
        ))
    return result


@app.get("/api/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.post("/api/reports", response_model=ReportOut)
def create_report(data: ReportCreate, db: Session = Depends(get_db)):
    # Verify employee exists
    emp = db.query(Employee).filter(Employee.id == data.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    report_id = str(uuid4())
    report = Report(
        id=report_id,
        employee_id=data.employee_id,
        clip_id=data.clip_id,
        session_id=data.session_id,
        jurisdiction=data.jurisdiction,
        code_backed_count=data.code_backed_count,
        guidance_count=data.guidance_count,
        efficiency_count=data.efficiency_count,
        highest_severity=data.highest_severity,
    )
    db.add(report)

    for f in data.findings:
        finding = Finding(
            id=str(uuid4()),
            report_id=report_id,
            **f.model_dump(),
        )
        db.add(finding)

    db.commit()
    db.refresh(report)
    return report


# --- Browser Action Logs ---

@app.post("/api/action-logs")
def create_or_update_action_log(
    payload: dict,
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    """Create or update a browser action log."""
    status = payload.get("status", "complete")

    # Check if an in_progress log exists for this report + action
    existing = (
        db.query(BrowserActionLog)
        .filter(
            BrowserActionLog.report_id == payload["report_id"],
            BrowserActionLog.action_type == payload["action_type"],
            BrowserActionLog.status == "in_progress",
        )
        .first()
    )

    if existing:
        existing.status = "complete" if payload.get("success") else "failed"
        existing.success = payload.get("success", False)
        existing.full_output = payload.get("full_output", "")
        existing.recording_url = payload.get("recording_url", "")
        db.commit()
        return {"id": existing.id}

    log = BrowserActionLog(
        id=str(uuid4()),
        report_id=payload["report_id"],
        action_type=payload["action_type"],
        status=status,
        success=payload.get("success", False),
        full_output=payload.get("full_output", ""),
        recording_url=payload.get("recording_url", ""),
    )
    db.add(log)
    db.commit()
    return {"id": log.id}


# --- All Findings (for offense-grouped view) ---

@app.get("/api/findings")
def list_all_findings(db: Session = Depends(get_db)):
    """Return every finding with its parent employee info attached."""
    rows = (
        db.query(Finding, Employee.name.label("employee_name"), Employee.id.label("emp_id"), Employee.role)
        .join(Report, Finding.report_id == Report.id)
        .join(Employee, Report.employee_id == Employee.id)
        .all()
    )
    results = []
    for finding, emp_name, emp_id, emp_role in rows:
        d = {c.name: getattr(finding, c.name) for c in finding.__table__.columns}
        d["employee_name"] = emp_name
        d["employee_id"] = emp_id
        d["employee_role"] = emp_role
        results.append(d)
    return results


# --- Video Analysis Pipeline ---

ORCHESTRATOR_URL = "http://localhost:8004"
HEALTH_TYPES = set(HEALTH_OBSERVATION_TYPES)
EFFICIENCY_TYPES = set(EFFICIENCY_OBSERVATION_TYPES)


def _secs_to_hms(s: float) -> str:
    m, sec = divmod(int(s), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


@app.post("/api/analyze")
async def analyze_video(
    video: UploadFile = File(...),
    employee_id: str = Form(...),
    jurisdiction: str = Form("federal"),
    db: Session = Depends(get_db),
):
    """Upload a video, run TwelveLabs detection, and send to the agent pipeline."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Save upload to a temp file
    suffix = Path(video.filename or "video.mp4").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(video.file, tmp)
        tmp_path = tmp.name

    try:
        result = run_detection_pipeline(tmp_path)
    except Exception as e:
        logger.exception("TwelveLabs pipeline failed")
        raise HTTPException(status_code=502, detail=f"Video analysis failed: {e}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    health_events = []
    efficiency_events = []

    for i, det in enumerate(result.detections):
        obs = {
            "observation_id": f"obs_{i}",
            "observation_type": det.type,
            "timestamp_start": _secs_to_hms(det.timestamp_start),
            "timestamp_end": _secs_to_hms(det.timestamp_end),
            "description": det.description,
        }
        event = {
            "event_id": f"evt_{i}",
            "observations": [obs],
        }
        if det.type in HEALTH_TYPES:
            health_events.append(event)
        elif det.type in EFFICIENCY_TYPES:
            efficiency_events.append(event)
        else:
            logger.warning("Unknown observation type from Pegasus: %s", det.type)
            health_events.append(event)

    orchestrator_payload = {
        "clip_id": result.asset_id,
        "employee_id": emp.id,
        "employee_name": emp.name,
        "jurisdiction": jurisdiction,
        "health_events": health_events,
        "efficiency_events": efficiency_events,
        "actions": [],
    }

    # Forward to orchestrator agent
    orchestrator_response = None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{ORCHESTRATOR_URL}/api/analyze",
                json=orchestrator_payload,
                timeout=10.0,
            )
            if resp.status_code == 200:
                orchestrator_response = resp.json()
            else:
                logger.warning(
                    "Orchestrator returned %d: %s", resp.status_code, resp.text
                )
    except Exception as e:
        logger.warning("Could not reach orchestrator: %s", e)

    return {
        "status": "submitted",
        "asset_id": result.asset_id,
        "total_detections": len(result.detections),
        "health_events": len(health_events),
        "efficiency_events": len(efficiency_events),
        "detections": [
            {
                "type": d.type,
                "timestamp_start": d.timestamp_start,
                "timestamp_end": d.timestamp_end,
                "description": d.description,
            }
            for d in result.detections
        ],
        "orchestrator": orchestrator_response,
    }


# --- Google OAuth + Sheets ---

from fastapi.responses import RedirectResponse
from backend.services.google_sheets import (
    get_oauth_login_url,
    handle_oauth_callback,
    create_safewatch_sheet,
    append_findings_to_sheet,
    get_account,
)


@app.get("/api/google/status")
def google_status(
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    """Check if the manager has connected their Google account."""
    account = get_account(manager_id, db)
    if not account:
        return {"connected": False}
    return {
        "connected": True,
        "email": account.email,
        "sheet_id": account.sheet_id,
        "sheet_url": account.sheet_url,
    }


@app.get("/api/google/login")
def google_login(manager_id: str = Depends(require_manager)):
    """Redirect the manager to Google's OAuth consent page."""
    url = get_oauth_login_url(manager_id)
    return {"auth_url": url}


@app.get("/api/google/callback")
def google_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    """Google redirects here after consent. Exchange code for tokens."""
    account = handle_oauth_callback(code, state, db)

    # Auto-create the sheet if one doesn't exist
    if not account.sheet_id:
        create_safewatch_sheet(account, db)

    # Redirect back to the frontend settings page
    return RedirectResponse(url="http://localhost:5173/settings?google=connected")


@app.post("/api/google/create-sheet")
def create_sheet(
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    """Create (or recreate) a SafeWatch spreadsheet on the manager's Google account."""
    account = get_account(manager_id, db)
    if not account:
        raise HTTPException(status_code=400, detail="Google account not connected")

    result = create_safewatch_sheet(account, db)
    return result


@app.post("/api/google/log-findings")
def log_findings_to_sheet(
    report_id: str,
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    """Append all findings from a report to the manager's Google Sheet."""
    account = get_account(manager_id, db)
    if not account:
        raise HTTPException(status_code=400, detail="Google account not connected")
    if not account.sheet_id:
        raise HTTPException(status_code=400, detail="No sheet created yet")

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    employee = db.query(Employee).filter(Employee.id == report.employee_id).first()
    findings_dicts = [
        {c.name: getattr(f, c.name) for c in f.__table__.columns}
        for f in report.findings
    ]

    count = append_findings_to_sheet(
        account,
        employee.name if employee else report.employee_id,
        findings_dicts,
    )
    return {
        "rows_appended": count,
        "sheet_url": account.sheet_url,
    }


@app.post("/api/google/log-findings-direct")
def log_findings_direct(
    payload: dict,
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    """Append findings directly (from browser agent) without needing a report_id."""
    account = get_account(manager_id, db)
    if not account:
        raise HTTPException(status_code=400, detail="Google account not connected")
    if not account.sheet_id:
        raise HTTPException(status_code=400, detail="No sheet created yet")

    count = append_findings_to_sheet(
        account,
        payload.get("employee_name", "Unknown"),
        payload.get("findings", []),
    )
    return {
        "rows_appended": count,
        "sheet_url": account.sheet_url,
    }
