"""
Policy Resolver — maps observation bundles to concluded finding types and policy references.

The vision pipeline sends evidence-level observations (e.g. "raw_food_contact",
"no_sanitation_between_tasks"). This module pattern-matches those observations to
conclude a finding type (e.g. "cross_contamination") and looks up the applicable
policy citation.

CITATIONS VERIFIED AGAINST:
- FDA Food Code 2022 (official PDF): https://www.fda.gov/media/164194/download
- California Retail Food Code (Legislature site): https://leginfo.legislature.ca.gov/
- OSHA Restaurant Food Prep: https://www.osha.gov/etools/young-workers-restaurant-safety/food-prep
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Observation combo -> concluded finding type
# Keys are frozensets of observation types that together indicate a finding.
# Checked largest-first so more specific combos match before general ones.
# ---------------------------------------------------------------------------

OBSERVATION_PATTERNS: list[tuple[frozenset[str], str]] = [
    # Cross-contamination: raw contact + RTE contact + no sanitation
    (
        frozenset({"raw_food_contact", "rte_food_contact", "no_sanitation_between_tasks"}),
        "cross_contamination",
    ),
    # Hand-to-face then food contact without washing
    (
        frozenset({"hand_to_face", "rte_food_contact", "hand_wash_skipped"}),
        "insufficient_handwashing",
    ),
    # Dropped utensil reused without washing
    (
        frozenset({"utensil_dropped", "item_reused_without_wash"}),
        "contaminated_utensil_reuse",
    ),
    # Dropped food reused without washing
    (
        frozenset({"food_dropped", "item_reused_without_wash"}),
        "contaminated_food_reuse",
    ),
    # Glove not changed after contamination trigger
    (
        frozenset({"glove_not_changed"}),
        "glove_misuse",
    ),
    # Bare-hand contact with ready-to-eat food
    (
        frozenset({"bare_hand_rte"}),
        "bare_hand_rte_contact",
    ),
    # Handwashing too short
    (
        frozenset({"hand_wash_short"}),
        "insufficient_handwashing",
    ),
    # Handwashing skipped entirely
    (
        frozenset({"hand_wash_skipped"}),
        "insufficient_handwashing",
    ),
    # Knife pointed at person
    (
        frozenset({"knife_pointed_at_person"}),
        "unsafe_knife_handling",
    ),
    # Knife near table edge
    (
        frozenset({"knife_near_table_edge"}),
        "unsafe_knife_placement",
    ),
    # Direct Pegasus outputs (single-observation patterns)
    (
        frozenset({"cross_contamination"}),
        "cross_contamination",
    ),
    (
        frozenset({"hand_to_face"}),
        "insufficient_handwashing",
    ),
    (
        frozenset({"food_dropped"}),
        "contaminated_food_reuse",
    ),
    (
        frozenset({"utensil_dropped"}),
        "contaminated_utensil_reuse",
    ),
]

# Positive-evidence patterns that indicate NO violation (cleared)
CLEARED_PATTERNS: list[frozenset[str]] = [
    frozenset({"utensil_dropped", "item_discarded"}),
    frozenset({"food_dropped", "item_discarded"}),
]

# Observation types that are incidents but not findings on their own
# (empty now — Pegasus flags these directly when they constitute a real issue)
INCIDENT_ONLY: set[str] = set()


# ---------------------------------------------------------------------------
# Verified policy database
#
# Citations verified against official FDA Food Code 2022 PDF, California
# Legislature CalCode sections, and OSHA restaurant safety pages.
#
# Design rule for California:
#   - If a direct CalCode equivalent exists, use it.
#   - If NO clean CalCode equivalent exists for the generic event type
#     (e.g. glove_misuse), use the FDA model-code citation honestly
#     rather than inventing a California citation.
# ---------------------------------------------------------------------------

POLICY_DB: dict[str, dict[str, dict]] = {
    "cross_contamination": {
        "federal": {
            "finding_class": "code_backed_food_safety",
            "reference": {
                "source_tier": "fda",
                "code": "FDA Food Code 2022",
                "section": "3-302.11",
                "short_rule": (
                    "Protect food from cross contamination by separating raw animal "
                    "foods from ready-to-eat foods and from fruits and vegetables "
                    "before washing."
                ),
                "official_url": "https://www.fda.gov/media/164194/download",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate raw-to-RTE cross-contamination "
                "without visible sanitation between tasks."
            ),
            "assumptions": [],
        },
        "california": {
            "finding_class": "code_backed_food_safety",
            "reference": {
                "source_tier": "calcode",
                "code": "California Retail Food Code",
                "section": "113986",
                "short_rule": (
                    "Protect food from cross-contamination using separation, "
                    "storage, and preparation controls."
                ),
                "official_url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113986.",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate raw-to-RTE cross-contamination "
                "without visible sanitation between tasks."
            ),
            "assumptions": ["surface was used for ready-to-eat food"],
        },
    },
    "insufficient_handwashing": {
        "federal": {
            "finding_class": "code_backed_food_safety",
            "reference": {
                "source_tier": "fda",
                "code": "FDA Food Code 2022",
                "section": "2-301.12; 2-301.14",
                "short_rule": (
                    "Wash hands for at least 20 seconds and at required times, "
                    "including task changes, after body contact, raw-to-ready-to-eat "
                    "switches, and before donning gloves."
                ),
                "official_url": "https://www.fda.gov/media/164194/download",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate handwashing was insufficient "
                "or skipped before food contact."
            ),
            "assumptions": [],
        },
        "california": {
            "finding_class": "code_backed_food_safety",
            "reference": {
                "source_tier": "calcode",
                "code": "California Retail Food Code",
                "section": "113953.3",
                "short_rule": (
                    "Wash hands with cleanser and warm water for 10 to 15 seconds "
                    "at required times, including task changes, raw-to-ready-to-eat "
                    "switches, before gloves, and before serving food."
                ),
                "official_url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113953.3",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate handwashing was insufficient "
                "or skipped before food contact."
            ),
            "assumptions": [],
        },
    },
    "glove_misuse": {
        # NOTE: For California, no clean direct CalCode equivalent to FDA 3-304.15
        # for generic glove misuse. We use the FDA model-code citation honestly
        # for both jurisdictions rather than inventing a California citation.
        "federal": {
            "finding_class": "code_backed_food_safety",
            "reference": {
                "source_tier": "fda",
                "code": "FDA Food Code 2022",
                "section": "3-304.15",
                "short_rule": (
                    "If used, single-use gloves shall be used for only one task "
                    "and discarded when damaged, soiled, or when interruptions occur."
                ),
                "official_url": "https://www.fda.gov/media/164194/download",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate gloves were not changed between "
                "tasks or after a contamination event."
            ),
            "assumptions": [],
        },
        "california": {
            "finding_class": "code_backed_food_safety",
            "reference": {
                "source_tier": "fda",
                "code": "FDA Food Code 2022 (model code — no direct CalCode equivalent for generic glove misuse)",
                "section": "3-304.15",
                "short_rule": (
                    "If used, single-use gloves shall be used for only one task "
                    "and discarded when damaged, soiled, or when interruptions occur."
                ),
                "official_url": "https://www.fda.gov/media/164194/download",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate gloves were not changed between "
                "tasks or after a contamination event."
            ),
            "assumptions": [],
        },
    },
    "bare_hand_rte_contact": {
        # This event MUST branch on jurisdiction — FDA and California differ.
        "federal": {
            "finding_class": "code_backed_food_safety",
            "reference": {
                "source_tier": "fda",
                "code": "FDA Food Code 2022",
                "section": "3-301.11",
                "short_rule": (
                    "Food employees may not touch exposed ready-to-eat food with "
                    "bare hands, subject to limited cooking and approved-alternative "
                    "exceptions."
                ),
                "official_url": "https://www.fda.gov/media/164194/download",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate bare-hand contact with "
                "ready-to-eat food. FDA Food Code generally prohibits this "
                "except in limited circumstances."
            ),
            "assumptions": [],
        },
        "california": {
            "finding_class": "code_backed_food_safety",
            "reference": {
                "source_tier": "calcode",
                "code": "California Retail Food Code",
                "section": "113961",
                "short_rule": (
                    "Food employees shall minimize bare hand contact with "
                    "nonprepackaged ready-to-eat food and use nonlatex utensils, "
                    "but may assemble or place ready-to-eat food without utensils "
                    "in an approved prep area if hands are cleaned under 113953.3."
                ),
                "official_url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113961.",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate bare-hand contact with "
                "ready-to-eat food. California permits this in approved prep areas "
                "if hands are washed per CalCode, but proper handwashing must be "
                "confirmed."
            ),
            "assumptions": ["prep area approval status not verified by video"],
        },
    },
    "contaminated_utensil_reuse": {
        "federal": {
            "finding_class": "code_backed_food_safety",
            "reference": {
                "source_tier": "fda",
                "code": "FDA Food Code 2022",
                "section": "3-304.11",
                "short_rule": (
                    "Food may contact only equipment and utensils that are cleaned "
                    "and sanitized as required."
                ),
                "official_url": "https://www.fda.gov/media/164194/download",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate a dropped or contaminated "
                "utensil was reused without proper washing or sanitation."
            ),
            "assumptions": [],
        },
        "california": {
            "finding_class": "code_backed_food_safety",
            "reference": {
                "source_tier": "calcode",
                "code": "California Retail Food Code",
                "section": "114117(a)(5)",
                "short_rule": (
                    "Equipment food-contact surfaces and utensils shall be cleaned "
                    "and sanitized at any time during operation when contamination "
                    "may have occurred."
                ),
                "official_url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=114117.",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate a dropped or contaminated "
                "utensil was reused without proper washing or sanitation."
            ),
            "assumptions": [],
        },
    },
    "contaminated_food_reuse": {
        "federal": {
            "finding_class": "code_backed_food_safety",
            "reference": {
                "source_tier": "fda",
                "code": "FDA Food Code 2022",
                "section": "3-302.11",
                "short_rule": (
                    "Food that has contacted a contaminated surface shall not be "
                    "served."
                ),
                "official_url": "https://www.fda.gov/media/164194/download",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate food that contacted the floor "
                "or a contaminated surface was reused without discarding."
            ),
            "assumptions": [],
        },
        "california": {
            "finding_class": "code_backed_food_safety",
            "reference": {
                "source_tier": "calcode",
                "code": "California Retail Food Code",
                "section": "113986",
                "short_rule": "Contaminated food shall not be served to consumers.",
                "official_url": "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=113986.",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate food that contacted the floor "
                "or a contaminated surface was reused without discarding."
            ),
            "assumptions": [],
        },
    },
    "unsafe_knife_handling": {
        # Workplace safety guidance, not a food-code citation.
        # Same source for both jurisdictions — OSHA is federal.
        "federal": {
            "finding_class": "workplace_safety_rule",
            "reference": {
                "source_tier": "osha",
                "code": "OSHA Young Worker Safety in Restaurants - Food Preparation",
                "section": "Knives and cuts",
                "short_rule": (
                    "Handle, use, and store knives safely; cut away from the body; "
                    "keep fingers and thumbs out of the cutting line."
                ),
                "official_url": "https://www.osha.gov/etools/young-workers-restaurant-safety/food-prep",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate a knife was directed toward "
                "another person, creating an injury risk."
            ),
            "assumptions": [],
        },
        "california": {
            "finding_class": "workplace_safety_rule",
            "reference": {
                "source_tier": "osha",
                "code": "OSHA Young Worker Safety in Restaurants - Food Preparation",
                "section": "Knives and cuts",
                "short_rule": (
                    "Handle, use, and store knives safely; cut away from the body; "
                    "keep fingers and thumbs out of the cutting line."
                ),
                "official_url": "https://www.osha.gov/etools/young-workers-restaurant-safety/food-prep",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate a knife was directed toward "
                "another person, creating an injury risk."
            ),
            "assumptions": [],
        },
    },
    "unsafe_knife_placement": {
        "federal": {
            "finding_class": "workplace_safety_rule",
            "reference": {
                "source_tier": "osha",
                "code": "OSHA Young Worker Safety in Restaurants - Food Preparation",
                "section": "Knives and cuts",
                "short_rule": (
                    "Handle, use, and store knives and other sharp utensils safely."
                ),
                "official_url": "https://www.osha.gov/etools/young-workers-restaurant-safety/food-prep",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate a knife was placed near the "
                "edge of the prep table, creating a fall/injury risk."
            ),
            "assumptions": [],
        },
        "california": {
            "finding_class": "workplace_safety_rule",
            "reference": {
                "source_tier": "osha",
                "code": "OSHA Young Worker Safety in Restaurants - Food Preparation",
                "section": "Knives and cuts",
                "short_rule": (
                    "Handle, use, and store knives and other sharp utensils safely."
                ),
                "official_url": "https://www.osha.gov/etools/young-workers-restaurant-safety/food-prep",
            },
            "reasoning_template": (
                "{observation_label} {obs_types} indicate a knife was placed near the "
                "edge of the prep table, creating a fall/injury risk."
            ),
            "assumptions": [],
        },
    },
}

# Fallback for unrecognized finding types
UNKNOWN_POLICY: dict = {
    "finding_class": "house_rule",
    "reference": {
        "source_tier": "house_rule",
        "code": "Internal Policy",
        "section": "N/A",
        "short_rule": "Observation did not match a known policy rule",
        "official_url": "",
    },
    "reasoning_template": "{observation_label} {obs_types} did not match a known policy pattern.",
    "assumptions": ["manual review recommended"],
}


def resolve_policy(
    obs_types: list[str], jurisdiction: str
) -> tuple[str | None, dict]:
    """Given a list of observation types and jurisdiction, conclude the finding type
    and return the matching policy entry.

    Returns:
        (concluded_type, policy_dict) where concluded_type is None if the observations
        indicate a cleared/non-violation pattern.
    """
    obs_set = set(obs_types)

    # Check cleared patterns first (e.g. drop + discard = no finding)
    for cleared in CLEARED_PATTERNS:
        if cleared.issubset(obs_set):
            return None, {}

    # Check if observations are incident-only with no escalating signal
    if obs_set.issubset(INCIDENT_ONLY):
        return None, {}

    # Match against patterns (checked in order; first match wins)
    for pattern, concluded_type in OBSERVATION_PATTERNS:
        if pattern.issubset(obs_set):
            jurisdiction_key = jurisdiction if jurisdiction in ("federal", "california") else "federal"
            policy = POLICY_DB.get(concluded_type, {}).get(jurisdiction_key, UNKNOWN_POLICY)
            return concluded_type, policy

    return "unclassified", UNKNOWN_POLICY
