import hashlib
import json

import pandas as pd

from scoring import score_types
from gong import call_issues, gong as gong_key_points, red_flag_map

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

# Flag 5: forecast as Commit while still in Discovery or Qualification; the AM
# should check what supports the forecast or whether Salesforce needs updating.
df["FlagEarlyCommit"] = (
    (df["ForecastCategory"] == "Commit")
    & df["StageName"].isin(["Discovery", "Qualification"])
)

# An opportunity is problematic if any flag is raised.
df["IsProblem"] = df[
    ["FlagOverdue", "FlagStaleNearClose", "FlagStaleCommit", "FlagLongOverdue", "FlagEarlyCommit"]
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


# --- Gong Recency Bonus ---

# Gong red flags, scored by how recent the call was on the snapshot date.
# (A fresh index: the exploded Gong table repeats each call's row label.)
gong_signals = gong_key_points.dropna(subset=["red_flag"]).reset_index(drop=True)

gong_signals["CallDate"] = (
    pd.to_datetime(gong_signals["started"], utc=True)
    .dt.tz_localize(None)
    .dt.normalize()
)
gong_signals["AgeDays"] = (reference_date - gong_signals["CallDate"]).dt.days

# Ignore calls after the snapshot date, and calls older than 90 days (worth 0).
gong_signals = gong_signals[gong_signals["AgeDays"].between(0, 90)].copy()

# Recency: 20 points up to day 2, falling linearly to 5 at day 30 and to 0 at day 90.
age = gong_signals["AgeDays"]
gong_signals["RecencyPoints"] = 20.0
gong_signals.loc[age > 2, "RecencyPoints"] = 20 - (age - 2) * 15 / 28
gong_signals.loc[age > 30, "RecencyPoints"] = 5 - (age - 30) * 5 / 60

# Every red flag counts the same: the bonus depends only on how recent the call was.
gong_signals["SignalPoints"] = gong_signals["RecencyPoints"]

# If one call raises several flags, they tie on points; show them in red_flag_map's order
# (Closing risk first) so the drawer always names the same one.
flag_order = list(dict.fromkeys(red_flag_map.values()))
gong_signals["FlagOrder"] = gong_signals["red_flag"].map(flag_order.index)

# Note whether the call was about a deal or the account as a whole, for the drawer.
account_wide = gong_signals["associated_opp"].isna()
gong_signals["SignalScope"] = "deal"
gong_signals.loc[account_wide, "SignalScope"] = "account"

# Signals that apply to each open deal: calls linked to that deal, plus calls on
# its account that aren't linked to any deal.
deal_signals = gong_signals.merge(df[["Id"]], left_on="associated_opp", right_on="Id")
account_signals = gong_signals[account_wide].merge(
    df[["Id", "AccountId"]], left_on="associated_account", right_on="AccountId"
)

# Each deal keeps its strongest signal (the more recent call if two are equal,
# then the flag that comes first in red_flag_map).
best_signals = (
    pd.concat([deal_signals, account_signals])
    .sort_values(["SignalPoints", "CallDate", "FlagOrder"], ascending=[False, False, True])
    .drop_duplicates("Id")
    .set_index("Id")
)

# Round half up to whole points (pandas' round() would round 0.5 to the even number).
best_signals["Bonus"] = (best_signals["SignalPoints"] + 0.5) // 1

# Each deal's Gong bonus and the signal that earned it.
df["GongPoints"] = df["Id"].map(best_signals["Bonus"]).fillna(0).astype(int)
df["GongSignal"] = df["Id"].map(best_signals["red_flag"])
df["GongSignalText"] = df["Id"].map(best_signals["key_points"])
df["GongSignalDate"] = df["Id"].map(best_signals["CallDate"].dt.strftime("%Y-%m-%d"))
df["GongSignalAge"] = df["Id"].map(best_signals["AgeDays"])
df["GongSignalScope"] = df["Id"].map(best_signals["SignalScope"])

# The same ID the deal's evidence uses for this key point, so the drawer can show
# the bonus on that evidence line instead of repeating it.
signal_evidence_ids = {}
for deal_id, signal in best_signals.iterrows():
    key_point_hash = hashlib.sha1(signal["key_points"].encode()).hexdigest()[:6]
    signal_evidence_ids[deal_id] = f"{signal['id']}-{key_point_hash}"
df["GongSignalEvidenceId"] = df["Id"].map(signal_evidence_ids)

# Each deal's final score: its Salesforce score plus its Gong bonus.
df["FinalScore"] = df["PriorityScore"] + df["GongPoints"]


# --- Account Scores ---

# Each account's best renewal score and best upsell/new score (see scoring.py).
type_scores = score_types(df)

# Account priority is its highest-scoring open opportunity, i.e. the higher
# of the two type scores.
priority_scores = df.groupby("AccountName")["PriorityScore"].max()

# Accounts are ranked by their best deal once the Gong bonus is added.
final_scores = df.groupby("AccountName")["FinalScore"].max()


# --- Account Analysis ---

# Count opportunities by account and closing quarter.
df["OpportunityQuarter"] = df["CloseDate"].dt.to_period("Q")

quarter_counts = pd.crosstab(
    df["AccountName"],
    df["OpportunityQuarter"]
)



# --- Export for the UI ---

# Get each account's highest-scoring opportunity (Salesforce + Gong); among equal
# scores, a deal with a problem comes first, then the larger deal.
top_opportunities = (
    df.sort_values(["FinalScore", "IsProblem", "Amount"], ascending=False)
    .drop_duplicates("AccountName")
    .set_index("AccountName")
)

# Combine account scores and opportunity details.
ui_accounts = pd.DataFrame({
    "account_score": final_scores,
    "salesforce_score": top_opportunities["PriorityScore"],
    "gong_bonus": top_opportunities["GongPoints"],
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
    "top_early_commit": top_opportunities["FlagEarlyCommit"],
    "top_days_since_activity": top_opportunities["DaysSinceActivity"],
    "top_gong_issues": top_opportunities["GongIssues"],
    # Only accounts with open deals are ranked, so ignore calls from other accounts.
    "account_call_issues": account_call_issues.reindex(final_scores.index),
})

# --- Evidence for Next Actions ---

# The facts behind every open deal, each with an ID so a drafted next action
# can cite exactly what it is based on. Evidence only: no scoring.

# Every key point from Gong calls in the last 90 days, newest first. Key points
# without a red flag are kept as context, so the evidence isn't only bad news.
recent_key_points = gong_key_points.drop_duplicates(subset=["id", "key_points"]).copy()

recent_key_points["CallDate"] = (
    pd.to_datetime(recent_key_points["started"], utc=True)
    .dt.tz_localize(None)
    .dt.normalize()
)

recent_key_points = (
    recent_key_points[recent_key_points["CallDate"] >= reference_date - pd.Timedelta(days=90)]
    .sort_values("CallDate", ascending=False)
)

evidence_by_opportunity = {}

for _, deal in df.iterrows():
    evidence = []

    # Close date, with how far away it is.
    close_date = deal["CloseDate"].strftime("%d %b %Y")
    if deal["DaysToClose"] < 0:
        close_text = f"{close_date} (overdue by {-int(deal['DaysToClose'])} days)"
    else:
        close_text = f"{close_date} (in {int(deal['DaysToClose'])} days)"

    # Last Salesforce activity, or none logged.
    if pd.isna(deal["DaysSinceActivity"]):
        activity_text = "None logged"
    else:
        activity_text = f"{int(deal['DaysSinceActivity'])} days ago"

    # Salesforce problem flags raised on the deal.
    flag_names = []
    if deal["FlagLongOverdue"]:
        flag_names.append("Long overdue")
    elif deal["FlagOverdue"]:
        flag_names.append("Overdue")
    if deal["FlagStaleNearClose"]:
        flag_names.append("No recent activity before close")
    if deal["FlagStaleCommit"]:
        flag_names.append("Stale Commit")
    if deal["FlagEarlyCommit"]:
        flag_names.append("Early-stage Commit")

    # Salesforce fields of the top deal.
    salesforce_fields = [
        ("sf-opportunity", "Opportunity", deal["Name"]),
        ("sf-stage", "Stage", str(deal["StageName"])),
        ("sf-amount", "Amount", f"€{deal['Amount']:,.0f}"),
        ("sf-close", "Close date", close_text),
        ("sf-forecast", "Forecast category", deal["ForecastCategory"]),
        ("sf-activity", "Last activity logged in Salesforce", activity_text),
    ]
    if flag_names:
        salesforce_fields.append(("sf-flags", "Problem flags", ", ".join(flag_names)))
    if pd.notna(deal["NextStep"]):
        salesforce_fields.append(("sf-next-step", "Next step", deal["NextStep"]))

    for evidence_id, label, value in salesforce_fields:
        evidence.append({
            "id": evidence_id,
            "source": "Salesforce",
            "scope": "deal",
            "label": label,
            "value": value,
        })

    # Gong key points from calls about the top deal, then from calls not
    # linked to any deal, which keep their account-wide label.
    deal_points = recent_key_points[recent_key_points["associated_opp"] == deal["Id"]]
    account_points = recent_key_points[
        recent_key_points["associated_opp"].isna()
        & (recent_key_points["associated_account"] == deal["AccountId"])
    ]

    for scope, points in [("deal", deal_points), ("account", account_points)]:
        for _, point in points.iterrows():
            # Red-flag key points are named by their issue; the rest are context.
            if pd.notna(point["red_flag"]):
                point_type = point["red_flag"]
            else:
                point_type = "Context"

            # A stable ID: the call ID plus a short hash of the key point, so a
            # saved draft still points to the same key point after new calls arrive.
            key_point_hash = hashlib.sha1(point["key_points"].encode()).hexdigest()[:6]

            evidence.append({
                "id": f"{point['id']}-{key_point_hash}",
                "source": "Gong",
                "scope": scope,
                "label": f"{point_type} · call on {point['CallDate'].strftime('%d %b')}",
                "value": point["key_points"],
                "url": point["url"],
            })

    evidence_by_opportunity[deal["Id"]] = evidence

df["Evidence"] = df["Id"].map(evidence_by_opportunity)

# Each account row carries its top deal's ID; the deal's evidence is in opportunity_scores.json.
ui_accounts["top_opportunity_id"] = top_opportunities["Id"]

# Each account's recent calls not linked to any deal, newest first, for the drawer.
# Every red flag on such a call earns the same recency bonus on all the account's deals.
account_wide_signals = gong_signals[gong_signals["SignalScope"] == "account"].sort_values(
    ["CallDate", "FlagOrder"], ascending=[False, True]
)

account_wide_calls = {}
for call_id, call in account_wide_signals.groupby("id", sort=False):
    first = call.iloc[0]
    account_wide_calls.setdefault(first["associated_account"], []).append({
        "call_date": first["CallDate"].strftime("%Y-%m-%d"),
        "age_days": int(first["AgeDays"]),
        "bonus": int((first["RecencyPoints"] + 0.5) // 1),
        "flags": list(dict.fromkeys(call["red_flag"])),
        "key_points": list(call["key_points"]),
        "url": first["url"],
        "call_id": call_id,
    })

# Show an account-wide call (and its pills on the list row) only when it earned the top
# deal's bonus, i.e. when it counts toward the account's score.
top_signal_call_ids = top_opportunities["GongSignalEvidenceId"].str.split("-").str[0]
counted_call_ids = top_signal_call_ids[top_opportunities["GongSignalScope"] == "account"]

shown_calls = {}
shown_call_flags = {}
for account_name, counted_call_id in counted_call_ids.items():
    account_id = top_opportunities.loc[account_name, "AccountId"]
    for call in account_wide_calls.get(account_id, []):
        if call["call_id"] == counted_call_id:
            shown_calls[account_name] = [call]
            shown_call_flags[account_name] = call["flags"]

ui_accounts["account_wide_calls"] = pd.Series(shown_calls, dtype=object)
ui_accounts["account_call_issues"] = pd.Series(shown_call_flags, dtype=object)

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
        "Id": "opportunity_id",
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
        "FlagEarlyCommit": "early_commit",
        "DaysSinceActivity": "days_since_activity",
        "GongIssues": "gong_issues",
        "GongPoints": "gong_points",
        "FinalScore": "final_score",
        "GongSignal": "gong_signal",
        "GongSignalText": "gong_signal_text",
        "GongSignalDate": "gong_signal_date",
        "GongSignalAge": "gong_signal_age",
        "GongSignalScope": "gong_signal_scope",
        "GongSignalEvidenceId": "gong_signal_evidence_id",
        "Evidence": "evidence",
    })
    [[
        "account_name", "opportunity_id", "opportunity", "type", "amount", "stage",
        "close_date", "days_to_close", "value_score", "timing_score",
        "stage_score", "priority_score", "gong_points", "final_score",
        "gong_signal", "gong_signal_text", "gong_signal_date", "gong_signal_age", "gong_signal_scope",
        "gong_signal_evidence_id",
        "is_problem", "is_overdue", "stale_near_close", "stale_commit", "long_overdue", "early_commit",
        "days_since_activity", "gong_issues", "evidence",
    ]]
    .sort_values(
        ["account_name", "final_score", "is_problem", "amount"],
        ascending=[True, False, False, False]
    )
    .to_json("data/opportunity_scores.json", orient="records", indent=2)
)

# --- Gong Calls for the UI ---

# Every call with its summary and key points, so "Open call" can show the call in the app
# (the mock Gong URLs don't resolve). Each key point keeps its evidence ID and category.
calls_for_ui = {}
for call_id, call in gong_key_points.groupby("id", sort=False):
    first = call.iloc[0]
    key_points = []
    for _, point in call.iterrows():
        key_point_hash = hashlib.sha1(point["key_points"].encode()).hexdigest()[:6]
        category = point["red_flag"] if pd.notna(point["red_flag"]) else "Context"
        key_points.append({
            "evidence_id": f"{call_id}-{key_point_hash}",
            "text": point["key_points"],
            "category": category,
        })
    calls_for_ui[call_id] = {
        "started": first["started"],
        "brief": first["brief"],
        "key_points": key_points,
    }

with open("data/gong_calls.json", "w") as file:
    json.dump(calls_for_ui, file, indent=2)
