"""Seed the database with mock employees and a sample report."""

from uuid import uuid4
from backend.database import engine, SessionLocal, Base
from backend.models import Employee, Report, Finding

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Clear existing
db.query(Finding).delete()
db.query(Report).delete()
db.query(Employee).delete()
db.commit()

# --- Employees ---
employees = [
    Employee(id="emp_1", name="Maria Garcia", role="Prep Cook", station="Station 1", start_date="2025-06-15"),
    Employee(id="emp_2", name="James Chen", role="Line Cook", station="Station 2", start_date="2025-09-01"),
    Employee(id="emp_3", name="Aisha Patel", role="Prep Cook", station="Station 3", start_date="2026-01-10"),
]
db.add_all(employees)
db.commit()

# --- Sample report for Maria ---
report_id = str(uuid4())
report = Report(
    id=report_id,
    employee_id="emp_1",
    clip_id="clip_001",
    session_id="session_001",
    jurisdiction="california",
    code_backed_count=2,
    guidance_count=1,
    efficiency_count=0,
    highest_severity="high",
)
db.add(report)

findings = [
    Finding(
        id=str(uuid4()),
        report_id=report_id,
        agent_source="health",
        concluded_type="cross_contamination",
        status="confirmed_violation",
        finding_class="code_backed_food_safety",
        severity="high",
        policy_code="California Retail Food Code",
        policy_section="113986",
        policy_short_rule="Protect food from cross-contamination using separation, storage, and preparation controls.",
        policy_url="https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113986.",
        evidence_confidence=0.88,
        reasoning="Observations ['raw_food_contact', 'rte_food_contact', 'no_sanitation_between_tasks'] indicate raw-to-RTE cross-contamination without visible sanitation between tasks.",
        training_recommendation="Sanitize the food-contact surface and wash hands before switching from raw to ready-to-eat items.",
        corrective_action_observed=False,
        timestamp_start="00:01:42",
        timestamp_end="00:01:55",
    ),
    Finding(
        id=str(uuid4()),
        report_id=report_id,
        agent_source="health",
        concluded_type="insufficient_handwashing",
        status="possible_violation",
        finding_class="code_backed_food_safety",
        severity="medium",
        policy_code="California Retail Food Code",
        policy_section="113953.3",
        policy_short_rule="Wash hands with cleanser and warm water for 10 to 15 seconds at required times.",
        policy_url="https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113953.3",
        evidence_confidence=0.72,
        reasoning="Observations ['hand_wash_short'] indicate handwashing was insufficient or skipped before food contact.",
        training_recommendation="Handwashing appeared shorter than expected. Take the full 20 seconds, especially before food contact.",
        corrective_action_observed=False,
        timestamp_start="00:03:10",
        timestamp_end="00:03:18",
    ),
    Finding(
        id=str(uuid4()),
        report_id=report_id,
        agent_source="health",
        concluded_type="unsafe_knife_placement",
        status="confirmed_violation",
        finding_class="workplace_safety_rule",
        severity="low",
        policy_code="OSHA Young Worker Safety in Restaurants - Food Preparation",
        policy_section="Knives and cuts",
        policy_short_rule="Handle, use, and store knives and other sharp utensils safely.",
        policy_url="https://www.osha.gov/etools/young-workers-restaurant-safety/food-prep",
        evidence_confidence=0.82,
        reasoning="Observations ['knife_near_table_edge'] indicate a knife was placed near the edge of the prep table.",
        training_recommendation="Place knives flat and away from the edge of the prep surface when not actively cutting.",
        corrective_action_observed=False,
        timestamp_start="00:05:22",
        timestamp_end="00:05:28",
    ),
]
db.add_all(findings)
db.commit()

# --- Sample report for James (clean) ---
report2_id = str(uuid4())
report2 = Report(
    id=report2_id,
    employee_id="emp_2",
    clip_id="clip_002",
    session_id="session_001",
    jurisdiction="california",
    code_backed_count=0,
    guidance_count=0,
    efficiency_count=1,
    highest_severity="medium",
)
db.add(report2)

db.add(Finding(
    id=str(uuid4()),
    report_id=report2_id,
    agent_source="efficiency",
    concluded_type="phone_usage",
    status="confirmed_issue",
    finding_class="efficiency",
    severity="medium",
    policy_code="Internal Policy",
    policy_section="N/A",
    policy_short_rule="Personal phone use during active prep is discouraged.",
    policy_url="",
    evidence_confidence=0.91,
    reasoning="Employee was observed actively using phone for approximately 20 seconds during prep.",
    training_recommendation="Keep phone stored away during active prep tasks. Use designated break times for personal device use.",
    corrective_action_observed=False,
    timestamp_start="00:02:05",
    timestamp_end="00:02:25",
))
db.commit()

db.close()
print("Database seeded successfully.")
print(f"  {len(employees)} employees")
print(f"  2 reports")
print(f"  {len(findings) + 1} findings")
