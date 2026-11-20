
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


def test_single_type_accounts_keep_their_blended_score():
    # An account with only renewals, or only upsell/new deals, has nothing to
    # split, so its type score should equal its blended score.
    type_scores = integration.type_scores
    account_scores = integration.account_scores

    has_renewal = type_scores["RenewalScore"] > 0
    has_upsell_new = type_scores["UpsellNewScore"] > 0
    single_type = has_renewal != has_upsell_new
    combined = type_scores["RenewalScore"] + type_scores["UpsellNewScore"]

    assert single_type.any()
    assert (combined[single_type] == account_scores[single_type]).all()


def test_splitting_by_type_never_lowers_the_total():
    # In the blended score only one deal counts at 100%. Split by type, each
    # type's top deal counts at 100%, so together they can't be lower.
    type_scores = integration.type_scores
    combined = type_scores["RenewalScore"] + type_scores["UpsellNewScore"]

    assert (combined >= integration.account_scores).all()
