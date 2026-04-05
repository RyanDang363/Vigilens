from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from backend.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
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
    status = Column(String, nullable=False)
    finding_class = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    policy_code = Column(String, default="")
    policy_section = Column(String, default="")
    policy_short_rule = Column(String, default="")
    policy_url = Column(String, default="")
    evidence_confidence = Column(Float, default=0.0)
    reasoning = Column(String, default="")
    training_recommendation = Column(String, default="")
    corrective_action_observed = Column(Boolean, default=False)
    timestamp_start = Column(String, default="")
    timestamp_end = Column(String, default="")
    clip_url = Column(String, default="")

    report = relationship("Report", back_populates="findings")
