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