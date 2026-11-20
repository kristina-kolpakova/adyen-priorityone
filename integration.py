import pandas as pd

from scoring import score_accounts, score_types

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

# Combine opportunity scores into account scores (see scoring.py).
df, account_scores = score_accounts(df)

# Score renewals and upsell/new opportunities separately.
type_scores, type_details = score_types(df)

# Account priority is the stronger of the two type scores.
priority_scores = type_scores[["RenewalScore", "UpsellNewScore"]].max(axis=1)


# --- Account Analysis ---

# Count opportunities by account and closing quarter.
df["OpportunityQuarter"] = df["CloseDate"].dt.to_period("Q")

quarter_counts = pd.crosstab(
    df["AccountName"],
    df["OpportunityQuarter"]
)



# --- Export for the UI ---

# Which type sets each account's priority (ties go to renewals).
scoring_types = (
    type_scores[["RenewalScore", "UpsellNewScore"]]
    .idxmax(axis=1)
    .map({"RenewalScore": "Renewal", "UpsellNewScore": "Upsell/New"})
)

# Group each opportunity the same way, to match it to the winning type.
type_groups = type_details["Type"].map(
    {"Renewal": "Renewal", "Upsell": "Upsell/New", "New": "Upsell/New"}
)

# Get each account's highest-scoring opportunity within its winning type.
top_opportunities = type_details[
    (type_details["OpportunityRank"] == 1)
    & (type_groups == type_details["AccountName"].map(scoring_types))
].set_index("AccountName")

# Combine account scores and opportunity details.
ui_accounts = pd.DataFrame({
    "account_score": priority_scores,
    "scoring_type": scoring_types,
    "renewal_score": type_scores["RenewalScore"],
    "upsell_new_score": type_scores["UpsellNewScore"],
    "top_opportunity": top_opportunities["Name"],
    "top_type": top_opportunities["Type"],
    "top_amount": top_opportunities["Amount"],
    "top_stage": top_opportunities["StageName"].astype(str),
    "top_close_date": top_opportunities["CloseDate"].dt.strftime("%Y-%m-%d"),
    "top_is_overdue": top_opportunities["IsOverdue"],
})

# Sort accounts by priority, highest first, and number them.
ui_accounts = ui_accounts.reset_index(names="account_name")
ui_accounts = ui_accounts.sort_values(
    ["account_score", "account_name"],
    ascending=[False, True]
)
ui_accounts.insert(1, "rank", range(1, len(ui_accounts) + 1))

# Export to JSON for the UI.
ui_accounts.to_json("data/scores.json", orient="records", indent=2)

# Export each open opportunity's score breakdown for the detail panel.
(
    type_details
    .assign(
        CloseDate=type_details["CloseDate"].dt.strftime("%Y-%m-%d"),
        StageName=type_details["StageName"].astype(str),
        OpportunityRank=type_details["OpportunityRank"].astype(int),
        Weight=type_details["AccountContribution"] / type_details["PriorityScore"],
    )
    .rename(columns={
        "AccountName": "account_name",
        "Name": "opportunity",
        "Type": "type",
        "Amount": "amount",
        "StageName": "stage",
        "CloseDate": "close_date",
        "IsOverdue": "is_overdue",
        "ValueScore": "value_score",
        "QuarterScore": "quarter_score",
        "StageScore": "stage_score",
        "PriorityScore": "priority_score",
        "OpportunityRank": "type_rank",
        "Weight": "weight",
        "AccountContribution": "contribution",
    })
    [[
        "account_name", "opportunity", "type", "amount", "stage",
        "close_date", "is_overdue", "value_score", "quarter_score",
        "stage_score", "priority_score", "type_rank", "weight", "contribution",
    ]]
    .sort_values(["account_name", "priority_score"], ascending=[True, False])
    .to_json("data/opportunity_scores.json", orient="records", indent=2)
)
