"""FastAPI backend for the dashboard."""

from uuid import uuid4

from fastapi import (
    FastAPI,
    Depends,
    File,
    Header,
    HTTPException,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import engine, get_db, Base
from backend.models import Employee, Finding, Report, TrainingSource
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
    serialize_source,
    storage_path_for_source,
    summarize_source,
)

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
    )


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


# --- Training ---

@app.get("/api/training", response_model=list[TrainingSourceSummary])
def list_training_sources(
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    workspace_id = current_workspace_id()
    sources = (
        db.query(TrainingSource)
        .filter(
            TrainingSource.owner_manager_id == manager_id,
            TrainingSource.workspace_id == workspace_id,
        )
        .order_by(TrainingSource.created_at.desc())
        .all()
    )
    return [summarize_source(source) for source in sources]


@app.get("/api/training/{source_id}", response_model=TrainingSourceOut)
def get_training_source(
    source_id: str,
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    workspace_id = current_workspace_id()
    source = _get_training_source_or_404(db, source_id)
    if source.owner_manager_id != manager_id or source.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Training source is outside your workspace.")
    return serialize_source(source)


@app.get("/api/training/{source_id}/file")
def get_training_source_file(
    source_id: str,
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    workspace_id = current_workspace_id()
    source = _get_training_source_or_404(db, source_id)
    if source.owner_manager_id != manager_id or source.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Training source is outside your workspace.")
    if source.source_type != "upload" or not source.storage_path:
        raise HTTPException(status_code=404, detail="Original file preview is only available for uploaded sources.")

    from pathlib import Path

    file_path = Path(source.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Stored training file could not be found.")

    filename = f"{source.title}{file_path.suffix}"
    return FileResponse(
        path=file_path,
        media_type=source.mime_type,
        filename=filename,
        content_disposition_type="inline",
    )


@app.post("/api/training/upload", response_model=TrainingUploadResponse)
async def upload_training_source(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    manager_id: str = Depends(require_manager),
):
    workspace_id = current_workspace_id()
    mime_type = infer_mime_type(file.filename or "upload.bin", file.content_type)
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
    }
    if mime_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PDF, DOCX, TXT, or Markdown.")

    temp_id = str(uuid4())
    path = storage_path_for_source(temp_id, file.filename or "upload.bin")
    contents = await file.read()
    path.write_bytes(contents)

    source = create_training_source(
        db,
        source_type="upload",
        title=file.filename or "Uploaded training file",
        mime_type=mime_type,
        owner_manager_id=manager_id,
        workspace_id=workspace_id,
        raw_text="",
        storage_path=str(path),
    )
    db.commit()
    db.refresh(source)
    return {
        "source": serialize_source(source),
        "message": "File uploaded successfully.",
    }
