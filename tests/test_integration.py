"""Step 1 tests: loading Salesforce data, joining accounts, and value tiers."""

from pathlib import Path

import pandas as pd
import pytest

import integration

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

EXPECTED_TIER_COUNTS = {"low": 18, "medium": 17, "high": 17, "critical": 18}


# --- Fixtures --------------------------------------------------------------------
@pytest.fixture(scope="module")
def integrated():
    """The joined table built by integration.py."""
    return integration.df


@pytest.fixture(scope="module")
def source_accounts():
    """Accounts exactly as stored in the CSV, for independent comparisons."""
    return pd.read_csv(DATA_DIR / "accounts.csv")


@pytest.fixture(scope="module")
def source_open_opportunities():
    """Open opportunities exactly as stored in the CSV."""
    opportunities = pd.read_csv(DATA_DIR / "opportunities.csv")
    return opportunities[opportunities["IsClosed"] == False]


# --- Accounts ----------------------------------------------------------------------
def test_accounts_with_open_opportunities_are_kept(integrated, source_open_opportunities):
    # The left join keeps every open opportunity, so every account that has at
    # least one open opportunity appears: 29 of the 30 accounts.
    assert integrated["AccountId"].nunique() == 29
    assert set(integrated["AccountId"]) == set(source_open_opportunities["AccountId"])


def test_every_opportunity_gets_its_account_name(integrated, source_accounts):
    # Each open opportunity picks up the name of its Salesforce account.
    assert integrated["AccountName"].notna().all()

    account_names = dict(zip(source_accounts["Id"], source_accounts["Name"]))
    for _, row in integrated.iterrows():
        assert row["AccountName"] == account_names[row["AccountId"]]


# --- Opportunities and no duplication -------------------------------------------
def test_only_open_opportunities_come_through(integrated, source_open_opportunities):
    opportunity_ids = integrated["Id"]

    assert len(opportunity_ids) == 70
    assert set(opportunity_ids) == set(source_open_opportunities["Id"])


def test_join_does_not_duplicate_opportunities(integrated, source_open_opportunities):
    # Each open opportunity appears once after the join.
    assert integrated["Id"].is_unique

    # Expected total comes straight from the CSV, independent of the join.
    expected_total = source_open_opportunities["Amount"].sum()
    assert integrated["Amount"].sum() == expected_total


# --- Value tiers -------------------------------------------------------------------
def test_value_tiers_split_open_opportunities_evenly(integrated):
    # Tiers are calculated once across all 70 open opportunities, so each tier
    # holds roughly a quarter of them.
    tier_counts = integrated["AmountBuckets"].value_counts().to_dict()
    assert tier_counts == EXPECTED_TIER_COUNTS

    # Krakatoa's €1.45M renewal is in the top tier.
    krakatoa_renewal = integrated[integrated["Name"] == "Krakatoa - Renewal - Nov 2026"]
    assert krakatoa_renewal["AmountBuckets"].tolist() == ["critical"]
    assert krakatoa_renewal["ValueScore"].tolist() == [40]


# --- Accounts with no open opportunities ----------------------------------------
def test_account_without_open_opportunities_is_not_included(integrated):
    # Thistle has only closed opportunities, so the left join leaves it out.
    assert "Thistle" not in set(integrated["AccountName"])
