
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
    expected = {"low": 18, "medium": 17, "high": 17, "critical": 18}
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
