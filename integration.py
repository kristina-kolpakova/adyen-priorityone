import pandas as pd

from scoring import score_types

# Load Salesforce data.
df_opp = pd.read_csv("data/opportunities.csv")
df_acc = pd.read_csv("data/accounts.csv")

# Rename account columns for the merge.
df_acc = df_acc.rename(
    columns={"Id": "AccountId", "Name": "AccountName"}
)

# Keep only open opportunities.
df_opp = df_opp[df_opp["IsClosed"] == False].copy()

# Keep all open opportunities and add their Salesforce account information.
df = df_opp.merge(df_acc, how="left", on="AccountId")

# --- Value Score ---

# Divide opportunity amounts into four value tiers.
labels = ["low", "medium", "high", "critical"]

df["AmountBuckets"] = pd.qcut(
    df["Amount"],
    q=4,
    labels=labels
)

# Assign a score to each tier.
value_score_map = {
    "low": 10,
    "medium": 20,
    "high": 30,
    "critical": 40
}

# Convert value tiers to numeric scores; missing values get 0.
df["ValueScore"] = (
    df["AmountBuckets"]
    .map(value_score_map)
    .astype(float)
    .fillna(0)
    .astype(int)
)

# --- Quarter Score ---

# Set today's reference date for our analysis.
reference_date = pd.Timestamp.today().normalize()

# Convert the CloseDate column from text into datetime values.
df["CloseDate"] = pd.to_datetime(df["CloseDate"])

# Create a boolean column: True if the opportunity closes in the current calendar quarter.
df["InCurrentQuarter"] = (
    df["CloseDate"].dt.to_period("Q") == reference_date.to_period("Q")
)

# Assign 20 points to opportunities closing in the current quarter.
df["QuarterScore"] = df["InCurrentQuarter"].map({
    True: 20,
    False: 0
})

# --- Stage Score ---

# Define sales stage order from most to least advanced.
stage_order = ["Negotiation", "Proposal", "Discovery", "Qualification"]

df["StageName"] = pd.Categorical(
    df["StageName"],
    categories=stage_order,
    ordered=True
)

# Assign scores based on how advanced each opportunity is.
stage_score_map = {
    "Negotiation": 30,
    "Proposal": 20,
    "Discovery": 10,
    "Qualification": 0
}

df["StageScore"] = df["StageName"].map(stage_score_map).astype(int)

# --- Total Priority Score ---

# Calculate total opportunity priority from value, quarter, and stage.
df["PriorityScore"] = (
    df["ValueScore"]
    + df["QuarterScore"]
    + df["StageScore"]
)


# --- Account Priority Score ---

# Flag open opportunities with close dates in the past.
df["IsOverdue"] = df["CloseDate"] < reference_date

# Calculate how many quarters away each opportunity's close date is.
df["QuartersAway"] = (
    (df["CloseDate"].dt.year - reference_date.year) * 4
    + df["CloseDate"].dt.quarter
    - reference_date.quarter
)

# --- Problem Flags ---

# Days since Salesforce last recorded activity (missing activity stays empty).
df["DaysSinceActivity"] = (reference_date - pd.to_datetime(df["LastActivityDate"])).dt.days

# Days until each opportunity is expected to close (negative if overdue).
df["DaysToClose"] = (df["CloseDate"] - reference_date).dt.days

# No activity recorded in Salesforce in the last 30 days (or ever).
no_recent_activity = df["DaysSinceActivity"].isna() | (df["DaysSinceActivity"] > 30)

# Flag 1: the close date has passed, but the deal is still open.
df["FlagOverdue"] = df["IsOverdue"]

# Flag 2: closing within 30 days, with no recent activity.
df["FlagStaleNearClose"] = df["DaysToClose"].between(0, 30) & no_recent_activity

# Flag 3: forecast as Commit, with no recent activity.
df["FlagStaleCommit"] = (df["ForecastCategory"] == "Commit") & no_recent_activity

# An opportunity is problematic if any flag is raised.
df["IsProblem"] = df[["FlagOverdue", "FlagStaleNearClose", "FlagStaleCommit"]].any(axis=1)


# --- Account Scores ---

# Each account's best renewal score and best upsell/new score (see scoring.py).
type_scores = score_types(df)

# Account priority is its highest-scoring open opportunity, i.e. the higher
# of the two type scores.
priority_scores = df.groupby("AccountName")["PriorityScore"].max()


# --- Account Analysis ---

# Count opportunities by account and closing quarter.
df["OpportunityQuarter"] = df["CloseDate"].dt.to_period("Q")

quarter_counts = pd.crosstab(
    df["AccountName"],
    df["OpportunityQuarter"]
)



# --- Export for the UI ---

# Get each account's highest-scoring opportunity; among equal scores,
# a deal with a problem comes first, then the larger deal.
top_opportunities = (
    df.sort_values(["PriorityScore", "IsProblem", "Amount"], ascending=False)
    .drop_duplicates("AccountName")
    .set_index("AccountName")
)

# Combine account scores and opportunity details.
ui_accounts = pd.DataFrame({
    "account_score": priority_scores,
    "renewal_score": type_scores["RenewalScore"],
    "upsell_new_score": type_scores["UpsellNewScore"],
    "top_opportunity": top_opportunities["Name"],
    "top_type": top_opportunities["Type"],
    "top_amount": top_opportunities["Amount"],
    "top_stage": top_opportunities["StageName"].astype(str),
    "top_close_date": top_opportunities["CloseDate"].dt.strftime("%Y-%m-%d"),
    "top_is_problem": top_opportunities["IsProblem"],
    "top_is_overdue": top_opportunities["IsOverdue"],
    "top_stale_near_close": top_opportunities["FlagStaleNearClose"],
    "top_stale_commit": top_opportunities["FlagStaleCommit"],
    "top_days_since_activity": top_opportunities["DaysSinceActivity"],
})

# Sort accounts by priority; among equal scores, problems first, then amount.
ui_accounts = ui_accounts.reset_index(names="account_name")
ui_accounts = ui_accounts.sort_values(
    ["account_score", "top_is_problem", "top_amount", "account_name"],
    ascending=[False, False, False, True]
)
ui_accounts.insert(1, "rank", range(1, len(ui_accounts) + 1))

# Export to JSON for the UI.
ui_accounts.to_json("data/scores.json", orient="records", indent=2)

# Export each open opportunity's score breakdown and problem flags for the detail panel.
(
    df
    .assign(
        CloseDate=df["CloseDate"].dt.strftime("%Y-%m-%d"),
        StageName=df["StageName"].astype(str),
    )
    .rename(columns={
        "AccountName": "account_name",
        "Name": "opportunity",
        "Type": "type",
        "Amount": "amount",
        "StageName": "stage",
        "CloseDate": "close_date",
        "DaysToClose": "days_to_close",
        "ValueScore": "value_score",
        "QuarterScore": "quarter_score",
        "StageScore": "stage_score",
        "PriorityScore": "priority_score",
        "IsProblem": "is_problem",
        "IsOverdue": "is_overdue",
        "FlagStaleNearClose": "stale_near_close",
        "FlagStaleCommit": "stale_commit",
        "DaysSinceActivity": "days_since_activity",
    })
    [[
        "account_name", "opportunity", "type", "amount", "stage",
        "close_date", "days_to_close", "value_score", "quarter_score",
        "stage_score", "priority_score", "is_problem", "is_overdue",
        "stale_near_close", "stale_commit", "days_since_activity",
    ]]
    .sort_values(
        ["account_name", "priority_score", "is_problem", "amount"],
        ascending=[True, False, False, False]
    )
    .to_json("data/opportunity_scores.json", orient="records", indent=2)
)
