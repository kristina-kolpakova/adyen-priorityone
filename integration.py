import pandas as pd

from scoring import score_types
from gong import call_issues

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

# Divide opportunity amounts into eight value tiers, 1 (smallest) to 8 (largest).
labels = [1, 2, 3, 4, 5, 6, 7, 8]

df["AmountBuckets"] = pd.qcut(
    df["Amount"],
    q=8,
    labels=labels
)

# Assign 5 points per tier: 5 for the smallest deals, 40 for the largest.
value_score_map = {
    1: 5,
    2: 10,
    3: 15,
    4: 20,
    5: 25,
    6: 30,
    7: 35,
    8: 40
}

# Convert value tiers to numeric scores; missing values get 0.
df["ValueScore"] = (
    df["AmountBuckets"]
    .map(value_score_map)
    .astype(float)
    .fillna(0)
    .astype(int)
)

# --- Timing Score ---

# Score as of the date the mock data was pulled, so results don't change day to day.
reference_date = pd.Timestamp("2026-11-25")

# Convert the CloseDate column from text into datetime values.
df["CloseDate"] = pd.to_datetime(df["CloseDate"])

# Days until each opportunity is expected to close (negative if overdue).
df["DaysToClose"] = (df["CloseDate"] - reference_date).dt.days

# More points the sooner a deal closes (max 30).
df["TimingScore"] = 0
df.loc[df["DaysToClose"] <= 90, "TimingScore"] = 5
df.loc[df["DaysToClose"] <= 60, "TimingScore"] = 10
df.loc[df["DaysToClose"] <= 30, "TimingScore"] = 20
df.loc[df["DaysToClose"] <= 14, "TimingScore"] = 25
df.loc[df["DaysToClose"] <= 7, "TimingScore"] = 30

# Recently overdue deals (up to 30 days) need action now; deals overdue longer
# are more likely a stale Salesforce record, so they get less urgency.
df.loc[df["DaysToClose"] < 0, "TimingScore"] = 30
df.loc[df["DaysToClose"] < -30, "TimingScore"] = 10

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

# Opportunity priority out of 100: value (max 40) + timing (max 30) + stage (max 30).
df["PriorityScore"] = (
    df["ValueScore"]
    + df["TimingScore"]
    + df["StageScore"]
)


# --- Account Priority Score ---

# Flag open opportunities with close dates in the past.
df["IsOverdue"] = df["CloseDate"] < reference_date

# --- Problem Flags ---

# Days since Salesforce last recorded activity (missing activity stays empty).
df["DaysSinceActivity"] = (reference_date - pd.to_datetime(df["LastActivityDate"])).dt.days

# No activity recorded in Salesforce in the last 30 days (or ever).
no_recent_activity = df["DaysSinceActivity"].isna() | (df["DaysSinceActivity"] > 30)

# Flag 1: the close date has passed, but the deal is still open.
df["FlagOverdue"] = df["IsOverdue"]

# Flag 2: closing within 30 days, with no recent activity.
df["FlagStaleNearClose"] = df["DaysToClose"].between(0, 30) & no_recent_activity

# Flag 3: forecast as Commit, with no recent activity.
df["FlagStaleCommit"] = (df["ForecastCategory"] == "Commit") & no_recent_activity

# Flag 4: overdue by more than 30 days; the record may be stale and needs review.
df["FlagLongOverdue"] = df["DaysToClose"] < -30

# An opportunity is problematic if any flag is raised.
df["IsProblem"] = df[
    ["FlagOverdue", "FlagStaleNearClose", "FlagStaleCommit", "FlagLongOverdue"]
].any(axis=1)


# --- Gong Issues ---

# Gong issues are a separate signal: they are shown next to the Salesforce
# flags but don't change any score.
gong_calls = call_issues.copy()

# Call dates in UTC, without the time, so they compare with the reference date.
gong_calls["CallDate"] = (
    pd.to_datetime(gong_calls["started"], utc=True)
    .dt.tz_localize(None)
    .dt.normalize()
)

# Keep calls from the last 90 days; older issues may already be resolved.
recent_calls = gong_calls[gong_calls["CallDate"] >= reference_date - pd.Timedelta(days=90)]

# One row per issue, most recent call first.
recent_issues = (
    recent_calls.explode("red_flag")
    .sort_values("CallDate", ascending=False)
)

# Each deal's distinct issues from recent calls linked to it.
opportunity_gong_issues = (
    recent_issues
    .drop_duplicates(subset=["associated_opp", "red_flag"])
    .groupby("associated_opp")["red_flag"]
    .agg(list)
)

df["GongIssues"] = df["Id"].map(opportunity_gong_issues)

# Each account's distinct issues from recent calls not linked to any deal.
unlinked_issues = recent_issues[recent_issues["associated_opp"].isna()]

account_call_issues = (
    unlinked_issues
    .drop_duplicates(subset=["associated_account", "red_flag"])
    .merge(df_acc, left_on="associated_account", right_on="AccountId")
    .groupby("AccountName")["red_flag"]
    .agg(list)
)


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
    "top_long_overdue": top_opportunities["FlagLongOverdue"],
    "top_days_to_close": top_opportunities["DaysToClose"],
    "top_stale_near_close": top_opportunities["FlagStaleNearClose"],
    "top_stale_commit": top_opportunities["FlagStaleCommit"],
    "top_days_since_activity": top_opportunities["DaysSinceActivity"],
    "top_gong_issues": top_opportunities["GongIssues"],
    # Only accounts with open deals are ranked, so ignore calls from other accounts.
    "account_call_issues": account_call_issues.reindex(priority_scores.index),
})

# Rank on the same Gong issues the dashboard shows: any issue from the last 90 days.

# An issue linked to a deal applies only to that deal.
deal_risk_ids = recent_issues["associated_opp"].dropna()

# Use issues from calls without a linked deal as account-level risks.
account_risk_ids = unlinked_issues["associated_account"]

# Give one point for account-level risk. Use two if the top deal has risk.
gong_bonus = top_opportunities["AccountId"].isin(account_risk_ids).astype(int)
gong_bonus.loc[top_opportunities["Id"].isin(deal_risk_ids)] = 2

# Add the Gong points to the Salesforce score, and export both parts.
ui_accounts["salesforce_score"] = ui_accounts["account_score"]
ui_accounts["gong_bonus"] = gong_bonus
ui_accounts["account_score"] = ui_accounts["salesforce_score"] + ui_accounts["gong_bonus"]

# Move the account name into a column for sorting and JSON export.
ui_accounts = ui_accounts.reset_index(names="account_name")

# Sort by final score. Break ties by Salesforce problem flag, then deal amount.
# Use account name for any remaining ties.
ui_accounts = ui_accounts.sort_values(
    ["account_score", "top_is_problem", "top_amount", "account_name"],
    ascending=[False, False, False, True],
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
        "TimingScore": "timing_score",
        "StageScore": "stage_score",
        "PriorityScore": "priority_score",
        "IsProblem": "is_problem",
        "IsOverdue": "is_overdue",
        "FlagStaleNearClose": "stale_near_close",
        "FlagStaleCommit": "stale_commit",
        "FlagLongOverdue": "long_overdue",
        "DaysSinceActivity": "days_since_activity",
        "GongIssues": "gong_issues",
    })
    [[
        "account_name", "opportunity", "type", "amount", "stage",
        "close_date", "days_to_close", "value_score", "timing_score",
        "stage_score", "priority_score", "is_problem", "is_overdue",
        "stale_near_close", "stale_commit", "long_overdue", "days_since_activity",
        "gong_issues",
    ]]
    .sort_values(
        ["account_name", "priority_score", "is_problem", "amount"],
        ascending=[True, False, False, False]
    )
    .to_json("data/opportunity_scores.json", orient="records", indent=2)
)
