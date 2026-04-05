"""FastAPI backend for the dashboard."""

from uuid import uuid4

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.database import engine, get_db, Base
from backend.models import Employee, Report, Finding
from backend.schemas import (
    EmployeeCreate,
    EmployeeOut,
    FindingOut,
    ReportCreate,
    ReportOut,
    ReportSummary,
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
