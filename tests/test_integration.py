
"""Tests for Salesforce data integration and account scoring."""

import pandas as pd
import integration


def test_only_open_opportunities():
    assert len(integration.df) == 70
    assert (integration.df["IsClosed"] == False).all()


def test_accounts_are_preserved():
    assert integration.df["AccountId"].nunique() == 29
    assert integration.df["AccountName"].notna().all()


def test_opportunities_are_not_duplicated():
    assert integration.df["Id"].is_unique


def test_account_names_match_source():
    accounts = pd.read_csv("data/accounts.csv")
    expected_names = dict(zip(accounts["Id"], accounts["Name"]))

    for _, row in integration.df.iterrows():
        assert row["AccountName"] == expected_names[row["AccountId"]]


def test_value_tiers():
    expected = {1: 9, 2: 9, 3: 8, 4: 9, 5: 9, 6: 8, 7: 9, 8: 9}
    actual = integration.df["AmountBuckets"].value_counts().to_dict()

    assert actual == expected


def test_type_score_columns():
    assert list(integration.type_scores.columns) == [
        "RenewalScore",
        "UpsellNewScore"
    ]


def test_type_scores_are_the_best_deal_of_each_type():
    # Each type score is the highest PriorityScore among that account's
    # opportunities of that type (0 if it has none).
    df = integration.df
    renewals = df[df["Type"] == "Renewal"]
    upsell_new = df[df["Type"].isin(["Upsell", "New"])]
    type_scores = integration.type_scores

    expected_renewal = renewals.groupby("AccountName")["PriorityScore"].max()
    expected_upsell_new = upsell_new.groupby("AccountName")["PriorityScore"].max()

    assert (type_scores["RenewalScore"] == expected_renewal.reindex(type_scores.index, fill_value=0)).all()
    assert (type_scores["UpsellNewScore"] == expected_upsell_new.reindex(type_scores.index, fill_value=0)).all()


def test_account_priority_is_the_higher_type_score():
    # An account's priority is its best opportunity, so it equals the
    # higher of its two type scores.
    type_scores = integration.type_scores
    higher = type_scores[["RenewalScore", "UpsellNewScore"]].max(axis=1)

    assert (integration.priority_scores == higher).all()


def test_timing_score_follows_days_to_close():
    # Sooner closes get more points; deals overdue by more than 30 days get less.
    for _, row in integration.df.iterrows():
        days = row["DaysToClose"]
        if days < -30:
            expected = 10
        elif days <= 7:
            expected = 30
        elif days <= 14:
            expected = 25
        elif days <= 30:
            expected = 20
        elif days <= 60:
            expected = 10
        elif days <= 90:
            expected = 5
        else:
            expected = 0
        assert row["TimingScore"] == expected


def test_priority_score_is_out_of_100():
    df = integration.df
    total = df["ValueScore"] + df["TimingScore"] + df["StageScore"]

    assert (df["PriorityScore"] == total).all()
    assert df["PriorityScore"].between(0, 100).all()


def test_early_stage_commit_flag():
    # Commit in Discovery or Qualification is flagged, and counts as a problem.
    df = integration.df
    early_commit = (df["ForecastCategory"] == "Commit") & df["StageName"].isin(["Discovery", "Qualification"])

    assert (df["FlagEarlyCommit"] == early_commit).all()
    assert df.loc[df["FlagEarlyCommit"], "IsProblem"].all()


def test_final_score_adds_gong_bonus():
    # An account's score is its top deal's Salesforce score plus that deal's Gong bonus (0-20).
    accounts = integration.ui_accounts

    assert (accounts["account_score"] == accounts["salesforce_score"] + accounts["gong_bonus"]).all()
    assert accounts["gong_bonus"].between(0, 20).all()


def test_gong_bonus_follows_recency():
    # Every red flag counts the same: 20 points up to day 2 after the call,
    # then down to 5 at day 30 and 0 at day 90, rounded half up. No other weights.
    df = integration.df

    for _, deal in df.iterrows():
        if pd.isna(deal["GongSignal"]):
            assert deal["GongPoints"] == 0
            continue

        age = deal["GongSignalAge"]
        assert 0 <= age <= 90
        if age <= 2:
            recency = 20
        elif age <= 30:
            recency = 20 - (age - 2) * 15 / 28
        else:
            recency = 5 - (age - 30) * 5 / 60

        assert deal["GongPoints"] == int(recency + 0.5)


def test_every_deal_final_score_includes_gong():
    # Each deal's final score is its Salesforce score plus its Gong bonus, and
    # an account's score is its best deal's final score.
    df = integration.df

    assert (df["FinalScore"] == df["PriorityScore"] + df["GongPoints"]).all()
    assert df["GongPoints"].between(0, 20).all()

    best_final = df.groupby("AccountName")["FinalScore"].max()
    accounts = integration.ui_accounts.set_index("account_name")
    assert (accounts["account_score"] == best_final.reindex(accounts.index)).all()


def test_accounts_ranked_by_final_score_then_tie_breaks():
    # Highest final score first; ties go to a Salesforce problem flag, then the larger deal.
    accounts = integration.ui_accounts
    expected = accounts.sort_values(
        ["account_score", "top_is_problem", "top_amount", "account_name"],
        ascending=[False, False, False, True],
    )

    assert list(accounts["account_name"]) == list(expected["account_name"])
    assert list(accounts["rank"]) == list(range(1, len(accounts) + 1))


def test_demo_ranking_on_the_snapshot_date():
    # The mock data is scored as of 25 Nov 2026, so these stay fixed.
    accounts = integration.ui_accounts.set_index("account_name")

    assert (accounts.loc["Krakatoa", "rank"], accounts.loc["Krakatoa", "account_score"]) == (1, 116)
    assert (accounts.loc["Mosaic", "rank"], accounts.loc["Mosaic", "account_score"]) == (2, 113)
    assert (accounts.loc["Marlowe", "rank"], accounts.loc["Marlowe", "account_score"]) == (5, 94)
    assert (accounts.loc["Orchard Lane", "rank"], accounts.loc["Orchard Lane", "account_score"]) == (8, 88)
