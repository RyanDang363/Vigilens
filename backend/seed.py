"""Seed the database with mock employees and sample reports."""

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
    Employee(id="emp_4", name="Derek Thompson", role="Dishwasher", station="Dish Pit", start_date="2025-11-20"),
    Employee(id="emp_5", name="Sofia Reyes", role="Line Cook", station="Station 4", start_date="2025-07-05"),
    Employee(id="emp_6", name="Marcus Williams", role="Grill Cook", station="Grill Station", start_date="2025-04-12"),
    Employee(id="emp_7", name="Yuki Tanaka", role="Pastry Chef", station="Pastry Station", start_date="2026-02-01"),
    Employee(id="emp_8", name="Omar Hassan", role="Prep Cook", station="Station 5", start_date="2025-08-18"),
]
db.add_all(employees)
db.commit()

# ────────────────────────────────────────────
# Helper to create findings quickly
# ────────────────────────────────────────────

def make_finding(**kwargs):
    defaults = {
        "id": str(uuid4()),
        "agent_source": "health",
        "corrective_action_observed": False,
    }
    defaults.update(kwargs)
    return Finding(**defaults)


# ═══════════════════════════════════════════
# Report 1 — Maria Garcia (3 findings)
# ═══════════════════════════════════════════
r1_id = str(uuid4())
db.add(Report(
    id=r1_id, employee_id="emp_1", clip_id="clip_001", session_id="session_001",
    jurisdiction="california", code_backed_count=2, guidance_count=1,
    efficiency_count=0, highest_severity="high",
))
db.add_all([
    make_finding(
        report_id=r1_id,
        concluded_type="cross_contamination",
        finding_class="code_backed_food_safety",
        severity="high",
        policy_code="California Retail Food Code",
        policy_section="113986",
        policy_short_rule="Protect food from cross-contamination using separation, storage, and preparation controls.",
        policy_url="https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113986.",
        reasoning="Observation ['cross_contamination'] indicate raw-to-RTE cross-contamination without visible sanitation between tasks.",
        training_recommendation="Sanitize the food-contact surface and wash hands before switching from raw to ready-to-eat items.",
        timestamp_start="00:01:42", timestamp_end="00:01:55",
    ),
    make_finding(
        report_id=r1_id,
        concluded_type="insufficient_handwashing",
        finding_class="code_backed_food_safety",
        severity="medium",
        policy_code="California Retail Food Code",
        policy_section="113953.3",
        policy_short_rule="Wash hands with cleanser and warm water for 10 to 15 seconds at required times.",
        policy_url="https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113953.3",
        reasoning="Observation ['hand_wash_short'] indicate handwashing was insufficient before food contact.",
        training_recommendation="Wash hands thoroughly for at least 20 seconds before handling food, after touching your face, and when switching tasks.",
        timestamp_start="00:03:10", timestamp_end="00:03:18",
    ),
    make_finding(
        report_id=r1_id,
        concluded_type="unsafe_knife_placement",
        finding_class="workplace_safety_rule",
        severity="low",
        policy_code="OSHA Young Worker Safety in Restaurants - Food Preparation",
        policy_section="Knives and cuts",
        policy_short_rule="Handle, use, and store knives and other sharp utensils safely.",
        policy_url="https://www.osha.gov/etools/young-workers-restaurant-safety/food-prep",
        reasoning="Observation ['knife_near_table_edge'] indicate a knife was placed near the edge of the prep table.",
        training_recommendation="Place knives flat and away from the edge of the prep surface when not actively cutting.",
        timestamp_start="00:05:22", timestamp_end="00:05:28",
    ),
])

# ═══════════════════════════════════════════
# Report 2 — James Chen (1 efficiency finding)
# ═══════════════════════════════════════════
r2_id = str(uuid4())
db.add(Report(
    id=r2_id, employee_id="emp_2", clip_id="clip_002", session_id="session_001",
    jurisdiction="california", code_backed_count=0, guidance_count=0,
    efficiency_count=1, highest_severity="medium",
))
db.add(make_finding(
    report_id=r2_id,
    agent_source="efficiency",
    concluded_type="phone_usage",
    finding_class="efficiency",
    severity="medium",
    policy_code="Internal Policy",
    policy_section="N/A",
    policy_short_rule="Personal phone use during active prep is discouraged.",
    policy_url="",
    reasoning="Employee was observed actively using phone for approximately 20 seconds during prep.",
    training_recommendation="Keep personal phone use off the station during active prep so task flow stays uninterrupted.",
    timestamp_start="00:02:05", timestamp_end="00:02:25",
))

# ═══════════════════════════════════════════
# Report 3 — Derek Thompson (2 findings — wet floor & improper chemical storage)
# ═══════════════════════════════════════════
r3_id = str(uuid4())
db.add(Report(
    id=r3_id, employee_id="emp_4", clip_id="clip_003", session_id="session_002",
    jurisdiction="federal", code_backed_count=1, guidance_count=1,
    efficiency_count=0, highest_severity="high",
))
db.add_all([
    make_finding(
        report_id=r3_id,
        concluded_type="wet_floor_no_sign",
        finding_class="workplace_safety_rule",
        severity="high",
        policy_code="OSHA General Duty Clause",
        policy_section="5(a)(1)",
        policy_short_rule="Employers must keep workplaces free from recognized hazards causing or likely to cause death or serious harm.",
        policy_url="https://www.osha.gov/laws/oshact/section5-duties",
        reasoning="A wet floor hazard was observed without visible signage near the dish pit area.",
        training_recommendation="Always place a wet floor sign immediately when mopping or when water splashes onto the floor. Dry the area as soon as possible.",
        timestamp_start="00:00:45", timestamp_end="00:01:10",
    ),
    make_finding(
        report_id=r3_id,
        concluded_type="improper_chemical_storage",
        finding_class="code_backed_food_safety",
        severity="medium",
        policy_code="FDA Food Code 2022",
        policy_section="7-201.11",
        policy_short_rule="Poisonous or toxic materials shall be stored so they cannot contaminate food, equipment, or single-service articles.",
        policy_url="",
        reasoning="Cleaning chemicals were stored near or above food prep surfaces.",
        training_recommendation="Store all cleaning chemicals in a designated area below and away from food, utensils, and prep surfaces.",
        timestamp_start="00:03:30", timestamp_end="00:03:42",
    ),
])

# ═══════════════════════════════════════════
# Report 4 — Sofia Reyes (4 findings — busy shift, multiple issues)
# ═══════════════════════════════════════════
r4_id = str(uuid4())
db.add(Report(
    id=r4_id, employee_id="emp_5", clip_id="clip_004", session_id="session_003",
    jurisdiction="california", code_backed_count=3, guidance_count=1,
    efficiency_count=0, highest_severity="critical",
))
db.add_all([
    make_finding(
        report_id=r4_id,
        concluded_type="contaminated_food_reuse",
        finding_class="code_backed_food_safety",
        severity="critical",
        policy_code="California Retail Food Code",
        policy_section="113980",
        policy_short_rule="Food that has been contaminated shall not be served, sold, or offered for human consumption.",
        policy_url="https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113980",
        reasoning="Observation ['food_dropped'] indicate food fell to the floor and was placed back on the prep surface without discarding.",
        training_recommendation="Food that has contacted the floor or a contaminated surface must be discarded. It should never be served to customers.",
        timestamp_start="00:04:12", timestamp_end="00:04:25",
    ),
    make_finding(
        report_id=r4_id,
        concluded_type="bare_hand_rte_contact",
        finding_class="code_backed_food_safety",
        severity="medium",
        policy_code="California Retail Food Code",
        policy_section="113961",
        policy_short_rule="Food employees shall minimize bare hand contact with non-prepackaged ready-to-eat food.",
        policy_url="https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113961",
        reasoning="Observation ['bare_hand_rte'] indicate the employee handled ready-to-eat food without gloves or utensils.",
        training_recommendation="Use utensils, deli tissue, or gloves when handling ready-to-eat food. Bare-hand contact should be avoided.",
        timestamp_start="00:06:50", timestamp_end="00:07:02",
    ),
    make_finding(
        report_id=r4_id,
        concluded_type="glove_misuse",
        finding_class="code_backed_food_safety",
        severity="medium",
        policy_code="FDA Food Code 2022",
        policy_section="3-304.15",
        policy_short_rule="Single-use gloves shall be used for only one task and discarded when damaged, soiled, or when switching tasks.",
        policy_url="",
        reasoning="Observation ['glove_not_changed'] indicate the same pair of gloves was worn across raw meat handling and plating tasks.",
        training_recommendation="Change gloves when switching tasks, after contamination, or when they become damaged. One pair per task.",
        timestamp_start="00:08:15", timestamp_end="00:08:30",
    ),
    make_finding(
        report_id=r4_id,
        concluded_type="unsafe_knife_handling",
        finding_class="workplace_safety_rule",
        severity="medium",
        policy_code="OSHA Young Worker Safety in Restaurants - Food Preparation",
        policy_section="Knives and cuts",
        policy_short_rule="Handle, use, and store knives and other sharp utensils safely.",
        policy_url="https://www.osha.gov/etools/young-workers-restaurant-safety/food-prep",
        reasoning="Observation ['knife_pointed_at_person'] indicate the employee gestured with a knife blade directed toward a coworker.",
        training_recommendation="Never point or direct a knife toward another person. Carry knives at your side with the blade pointed down.",
        timestamp_start="00:10:05", timestamp_end="00:10:12",
    ),
])

# ═══════════════════════════════════════════
# Report 5 — Marcus Williams (3 findings — grill station hazards)
# ═══════════════════════════════════════════
r5_id = str(uuid4())
db.add(Report(
    id=r5_id, employee_id="emp_6", clip_id="clip_005", session_id="session_003",
    jurisdiction="federal", code_backed_count=1, guidance_count=1,
    efficiency_count=1, highest_severity="high",
))
db.add_all([
    make_finding(
        report_id=r5_id,
        concluded_type="temperature_danger_zone",
        finding_class="code_backed_food_safety",
        severity="high",
        policy_code="FDA Food Code 2022",
        policy_section="3-501.16",
        policy_short_rule="Time/temperature control for safety food shall be maintained at 135 F or above (hot) or 41 F or below (cold).",
        policy_url="",
        reasoning="Cooked proteins were left on the counter at room temperature for an extended period exceeding safe limits.",
        training_recommendation="Keep hot food at 135 F or above. If food will not be served within 2 hours, return it to heat or refrigerate immediately.",
        timestamp_start="00:12:00", timestamp_end="00:12:35",
    ),
    make_finding(
        report_id=r5_id,
        concluded_type="no_hair_restraint",
        finding_class="workplace_safety_rule",
        severity="low",
        policy_code="FDA Food Code 2022",
        policy_section="2-402.11",
        policy_short_rule="Food employees shall wear hair restraints to prevent hair from contacting exposed food.",
        policy_url="",
        reasoning="The employee was not wearing a hat, hairnet, or other hair restraint while working the grill station.",
        training_recommendation="Always wear an approved hair restraint (hat, hairnet, or visor) while in the kitchen. This prevents hair from contaminating food.",
        timestamp_start="00:00:10", timestamp_end="00:00:20",
    ),
    make_finding(
        report_id=r5_id,
        agent_source="efficiency",
        concluded_type="excessive_idle_time",
        finding_class="efficiency",
        severity="low",
        policy_code="Internal Policy",
        policy_section="N/A",
        policy_short_rule="Employees should remain productive during scheduled shift hours.",
        policy_url="",
        reasoning="Employee appeared idle at the grill station for approximately 3 minutes during peak service with pending tickets.",
        training_recommendation="If work is available, re-engage the next prep step promptly so the station does not stall.",
        timestamp_start="00:15:00", timestamp_end="00:18:05",
    ),
])

# ═══════════════════════════════════════════
# Report 6 — Yuki Tanaka (1 finding — clean record, minor issue)
# ═══════════════════════════════════════════
r6_id = str(uuid4())
db.add(Report(
    id=r6_id, employee_id="emp_7", clip_id="clip_006", session_id="session_004",
    jurisdiction="california", code_backed_count=0, guidance_count=0,
    efficiency_count=1, highest_severity="low",
))
db.add(make_finding(
    report_id=r6_id,
    agent_source="efficiency",
    concluded_type="workstation_clutter",
    finding_class="efficiency",
    severity="low",
    policy_code="Internal Policy",
    policy_section="N/A",
    policy_short_rule="Keep workstations organized and free of unnecessary clutter for safety and efficiency.",
    policy_url="",
    reasoning="The pastry station had excessive clutter with tools and ingredients spread across the surface, reducing usable workspace.",
    training_recommendation="Practice mise en place -- organize your tools and ingredients before starting. Return items to their place after use.",
    timestamp_start="00:01:00", timestamp_end="00:01:15",
))

# ═══════════════════════════════════════════
# Report 7 — Omar Hassan (5 findings — new employee, lots of issues)
# ═══════════════════════════════════════════
r7_id = str(uuid4())
db.add(Report(
    id=r7_id, employee_id="emp_8", clip_id="clip_007", session_id="session_004",
    jurisdiction="california", code_backed_count=3, guidance_count=1,
    efficiency_count=1, highest_severity="critical",
))
db.add_all([
    make_finding(
        report_id=r7_id,
        concluded_type="cross_contamination",
        finding_class="code_backed_food_safety",
        severity="high",
        policy_code="California Retail Food Code",
        policy_section="113986",
        policy_short_rule="Protect food from cross-contamination using separation, storage, and preparation controls.",
        policy_url="https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113986.",
        reasoning="Observation ['cross_contamination'] indicate the employee cut raw chicken and then immediately began slicing tomatoes on the same board without sanitizing.",
        training_recommendation="Sanitize the food-contact surface and wash hands before switching from raw to ready-to-eat items.",
        timestamp_start="00:02:15", timestamp_end="00:02:40",
    ),
    make_finding(
        report_id=r7_id,
        concluded_type="insufficient_handwashing",
        finding_class="code_backed_food_safety",
        severity="medium",
        policy_code="California Retail Food Code",
        policy_section="113953.3",
        policy_short_rule="Wash hands with cleanser and warm water for 10 to 15 seconds at required times.",
        policy_url="https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113953.3",
        reasoning="Observation ['hand_to_face'] indicate employee touched face and resumed food handling without washing hands.",
        training_recommendation="Wash hands thoroughly for at least 20 seconds before handling food, after touching your face, and when switching tasks.",
        timestamp_start="00:04:50", timestamp_end="00:05:05",
    ),
    make_finding(
        report_id=r7_id,
        concluded_type="contaminated_utensil_reuse",
        finding_class="code_backed_food_safety",
        severity="high",
        policy_code="California Retail Food Code",
        policy_section="113984",
        policy_short_rule="Utensils and food-contact surfaces must be cleaned and sanitized between uses.",
        policy_url="",
        reasoning="Observation ['utensil_dropped'] indicate a spatula fell to the floor and was picked up and used again without washing.",
        training_recommendation="A dropped or contaminated utensil must be washed and sanitized before reuse. Never reuse without cleaning.",
        timestamp_start="00:07:20", timestamp_end="00:07:35",
    ),
    make_finding(
        report_id=r7_id,
        concluded_type="eating_in_prep_area",
        finding_class="workplace_safety_rule",
        severity="medium",
        policy_code="FDA Food Code 2022",
        policy_section="2-401.11",
        policy_short_rule="Food employees may not eat, drink, or use tobacco in food preparation, service, or dishwashing areas.",
        policy_url="",
        reasoning="Employee was observed eating a snack at the prep station while ingredients were exposed nearby.",
        training_recommendation="Eating and drinking are only permitted in designated break areas. Never consume food at your prep station.",
        timestamp_start="00:09:00", timestamp_end="00:09:20",
    ),
    make_finding(
        report_id=r7_id,
        agent_source="efficiency",
        concluded_type="improper_tool_usage",
        finding_class="efficiency",
        severity="low",
        policy_code="Internal Policy",
        policy_section="N/A",
        policy_short_rule="Use designated tools for their intended purpose to maintain quality and safety.",
        policy_url="",
        reasoning="Employee used a bread knife to chop vegetables instead of the appropriate chef's knife, resulting in uneven cuts and slower prep.",
        training_recommendation="Use the correct knife for each task. Ask a senior cook if unsure which tool to use.",
        timestamp_start="00:11:30", timestamp_end="00:11:50",
    ),
])

# ═══════════════════════════════════════════
# Report 8 — Second report for Maria Garcia (showing improvement, 1 minor finding with corrective action)
# ═══════════════════════════════════════════
r8_id = str(uuid4())
db.add(Report(
    id=r8_id, employee_id="emp_1", clip_id="clip_008", session_id="session_005",
    jurisdiction="california", code_backed_count=1, guidance_count=0,
    efficiency_count=0, highest_severity="low",
))
db.add(make_finding(
    report_id=r8_id,
    concluded_type="insufficient_handwashing",
    finding_class="code_backed_food_safety",
    severity="low",
    policy_code="California Retail Food Code",
    policy_section="113953.3",
    policy_short_rule="Wash hands with cleanser and warm water for 10 to 15 seconds at required times.",
    policy_url="https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113953.3",
    reasoning="Observation ['hand_wash_short'] indicate handwashing may have been brief, but employee self-corrected and rewashed.",
    training_recommendation="Wash hands thoroughly for at least 20 seconds before handling food, after touching your face, and when switching tasks. Good corrective action was observed -- focus on preventing the initial lapse next time.",
    corrective_action_observed=True,
    timestamp_start="00:02:00", timestamp_end="00:02:12",
))

db.commit()
db.close()

total_employees = 8
total_reports = 8
print("Database seeded successfully.")
print(f"  {total_employees} employees")
print(f"  {total_reports} reports")
print(f"  Offense types: cross_contamination, insufficient_handwashing, unsafe_knife_placement,")
print(f"    phone_usage, wet_floor_no_sign, improper_chemical_storage, contaminated_food_reuse,")
print(f"    bare_hand_rte_contact, glove_misuse, unsafe_knife_handling, temperature_danger_zone,")
print(f"    no_hair_restraint, excessive_idle_time, workstation_clutter, contaminated_utensil_reuse,")
print(f"    eating_in_prep_area, improper_tool_usage")
