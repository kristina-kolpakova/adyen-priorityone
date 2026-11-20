import pandas as pd

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

# Rank opportunities within each account, highest score first.
df["OpportunityRank"] = (
    df.groupby("AccountName")["PriorityScore"]
    .rank(method="first", ascending=False)
)

# Initialize each opportunity's contribution to its account score.
df["AccountContribution"] = 0.0

# Count the highest-scoring opportunity at 100%.
df.loc[df["OpportunityRank"] == 1, "AccountContribution"] = df["PriorityScore"]

# Calculate how many quarters away each opportunity's close date is.
df["QuartersAway"] = (
    (df["CloseDate"].dt.year - reference_date.year) * 4
    + df["CloseDate"].dt.quarter
    - reference_date.quarter
)

# Count additional current-quarter and overdue opportunities at 50%.
df.loc[
    (df["OpportunityRank"] > 1) & (df["QuartersAway"] <= 0),
    "AccountContribution"
] = df["PriorityScore"] * 0.5

# Count additional next-quarter opportunities at 25%.
df.loc[
    (df["OpportunityRank"] > 1) & (df["QuartersAway"] == 1),
    "AccountContribution"
] = df["PriorityScore"] * 0.25

# Count additional later-quarter opportunities at 10%.
df.loc[
    (df["OpportunityRank"] > 1) & (df["QuartersAway"] >= 2),
    "AccountContribution"
] = df["PriorityScore"] * 0.10


# --- Account Analysis ---

# Count opportunities by account and closing quarter.
df["OpportunityQuarter"] = df["CloseDate"].dt.to_period("Q")

quarter_counts = pd.crosstab(
    df["AccountName"],
    df["OpportunityQuarter"]
)

# Sum opportunity contributions to calculate each account's priority.
account_scores = df.groupby("AccountName")["AccountContribution"].sum()