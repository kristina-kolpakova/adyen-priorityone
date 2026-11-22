
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


def test_final_score_adds_gong_points():
    # Final score = Salesforce score + Gong points, and Gong adds 0, 1 or 2.
    accounts = integration.ui_accounts

    assert (accounts["account_score"] == accounts["salesforce_score"] + accounts["gong_bonus"]).all()
    assert accounts["gong_bonus"].isin([0, 1, 2]).all()


def test_top_deal_gong_issue_gives_two_points():
    # An issue on the account's top deal is worth the full 2 points.
    accounts = integration.ui_accounts
    has_top_deal_issue = accounts["top_gong_issues"].notna()

    assert (accounts.loc[has_top_deal_issue, "gong_bonus"] == 2).all()


def test_gong_never_outranks_a_higher_salesforce_score():
    # Gong points only reorder accounts with the same Salesforce score.
    accounts = integration.ui_accounts

    assert accounts["salesforce_score"].is_monotonic_decreasing
