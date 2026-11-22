import json
import pandas as pd

# --- Load Gong Data ---

gong = pd.read_csv("data/gong_calls.csv")

# Convert each call's key points into a list.
gong["key_points"] = gong["key_points"].apply(json.loads)

# Create one row per key point.
gong = gong.explode("key_points")


# --- Red Flag Classification ---

# Match specific customer concerns to a consistent set of categories.
red_flag_map = {
    # Renewal and closing risks
    "renewal discussions on hold": "Closing risk",
    "before discussing renewal terms": "Closing risk",
    "signature unlikely": "Closing risk",
    "legal review may push": "Closing risk",

    # Competition
    "evaluating another payment provider": "Competitor risk",
    "request for proposal": "Competitor risk",

    # Pricing
    "benchmarking fees": "Pricing pressure",
    "pricing objection": "Pricing pressure",
    "revised offer": "Pricing pressure",
    "cost comparison": "Pricing pressure",
    "pricing review before signing": "Pricing pressure",
    "reduction in processing fees": "Pricing pressure",

    # Implementation
    "implementation delay": "Implementation delay",
    "go-live pushed": "Implementation delay",
    "no new date committed": "Implementation delay",

    # Technical and service issues
    "lower conversion": "Technical issue",
    "payout delays": "Technical issue",
    "not reconciling": "Technical issue",

    # Procurement and legal
    "procurement blocker": "Procurement / legal",
    "security questionnaire": "Procurement / legal",

    # Escalations
    "executive sponsor": "Executive escalation",
    "remediation plan": "Executive escalation",

    # Stakeholders
    "no technical owner": "Stakeholder change",
    "budget owner for pos has changed": "Stakeholder change",
    "procurement now leading": "Stakeholder change",
    "team reorganising": "Stakeholder change",

    # Follow-up
    "no follow-up meeting": "Missing next step",
}


# Assign one primary issue category to each key point.
def classify_red_flag(key_point):
    for phrase, category in red_flag_map.items():
        if phrase in key_point.lower():
            return category

    return None


gong["red_flag"] = gong["key_points"].apply(classify_red_flag)


# --- Keep Issues ---

# Keep only key points classified as issues.
red_flags = gong.dropna(subset=["red_flag"]).copy()

# Remove duplicate issue categories within the same call.
red_flags = red_flags.drop_duplicates(
    subset=["id", "red_flag"]
)


# --- Group Issues by Call ---

# Each call can have multiple distinct issues.
call_issues = (
    red_flags.groupby(
        ["id", "started", "associated_account", "associated_opp", "url"],
        dropna=False
    )["red_flag"]
    .agg(list)
    .reset_index()
)
