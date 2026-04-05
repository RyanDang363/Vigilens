from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from backend.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, default="")
    role = Column(String, default="")
    station = Column(String, default="")
    start_date = Column(String, default="")

    reports = relationship("Report", back_populates="employee")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True)
    employee_id = Column(String, ForeignKey("employees.id"), nullable=False)
    clip_id = Column(String, default="")
    session_id = Column(String, default="")
    jurisdiction = Column(String, default="federal")
    created_at = Column(DateTime, server_default=func.now())
    code_backed_count = Column(Integer, default=0)
    guidance_count = Column(Integer, default=0)
    efficiency_count = Column(Integer, default=0)
    highest_severity = Column(String, default="low")

    employee = relationship("Employee", back_populates="reports")
    findings = relationship("Finding", back_populates="report")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    agent_source = Column(String, default="health")  # "health" or "efficiency"
    concluded_type = Column(String, nullable=False)
    finding_class = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    policy_code = Column(String, default="")
    policy_section = Column(String, default="")
    policy_short_rule = Column(String, default="")
    policy_url = Column(String, default="")
    reasoning = Column(String, default="")
    training_recommendation = Column(String, default="")
    corrective_action_observed = Column(Boolean, default=False)
    timestamp_start = Column(String, default="")
    timestamp_end = Column(String, default="")
    clip_url = Column(String, default="")

    report = relationship("Report", back_populates="findings")


class BrowserActionLog(Base):
    __tablename__ = "browser_action_logs"

    id = Column(String, primary_key=True)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    action_type = Column(String, nullable=False)  # send_email | log_sheet | get_training_docs | research_violations
    status = Column(String, default="in_progress")  # in_progress | complete | failed
    success = Column(Boolean, default=False)
    full_output = Column(Text, default="")
    recording_url = Column(String, default="")
    created_at = Column(DateTime, server_default=func.now())

    report = relationship("Report", backref="action_logs")


class GoogleAccount(Base):
    __tablename__ = "google_accounts"

    id = Column(String, primary_key=True)  # manager_id
    email = Column(String, default="")
    access_token = Column(String, default="")
    refresh_token = Column(String, default="")
    token_uri = Column(String, default="https://oauth2.googleapis.com/token")
    scopes = Column(String, default="")
    sheet_id = Column(String, default="")
    sheet_url = Column(String, default="")


class TrainingSource(Base):
    __tablename__ = "training_sources"

    id = Column(String, primary_key=True)
    source_key = Column(String, nullable=False, index=True)
    source_type = Column(String, nullable=False)  # upload | google_doc
    title = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    owner_manager_id = Column(String, nullable=False, index=True)
    workspace_id = Column(String, nullable=False, index=True)
    raw_text = Column(Text, default="")
    tags_json = Column(Text, default="[]")
    version = Column(Integer, default=1)
    status = Column(String, default="uploaded")
    active_version = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_indexed_at = Column(DateTime, nullable=True)
    storage_path = Column(String, default="")
    google_file_id = Column(String, default="")
    source_url = Column(String, default="")
