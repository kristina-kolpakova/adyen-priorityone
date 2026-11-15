"""Phase 2a tests: joining accounts, opportunities and Gong calls."""

import csv
import shutil
from datetime import date
from pathlib import Path

import pytest

from integration import DATA_DIR, IntegrationError, load_and_integrate

NO_GONG_ACCOUNTS = {
    "Tidewater", "Halcyon", "Oakmoor",
    "Petrel", "Quillon", "Redfern", "Zephyrine",
}

LATEST_ACCOUNT_CALL_FIELDS = (
    "latest_opportunity_linked_gong_call",
    "latest_account_level_gong_call",
    "latest_gong_call_any_scope",
)


# --- Fixtures and helpers ------------------------------------------------------
@pytest.fixture(scope="module")
def records():
    return load_and_integrate()


@pytest.fixture(scope="module")
def records_by_name(records):
    by_name = {}
    for record in records:
        by_name[record["source"]["account"]["Name"]] = record
    return by_name


@pytest.fixture
def data_copy(tmp_path):
    """A temporary copy of the source CSVs that a test can safely change."""
    for file_name in ("accounts.csv", "opportunities.csv", "gong_calls.csv"):
        shutil.copy(DATA_DIR / file_name, tmp_path / file_name)
    return tmp_path


def read_csv_rows(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def source_rows(file_name: str) -> list[dict]:
    """Rows of a source CSV exactly as stored, for independent comparisons."""
    _, rows = read_csv_rows(DATA_DIR / file_name)
    return rows


def account_name(record: dict) -> str:
    return record["source"]["account"]["Name"]


def account_id(record: dict) -> str:
    return record["source"]["account"]["Id"]


def all_opportunities(records: list[dict]) -> list[dict]:
    opportunities = []
    for record in records:
        opportunities.extend(record["opportunities"])
    return opportunities


def all_gong_call_ids(records: list[dict]) -> list[str]:
    call_ids = []
    for record in records:
        for opportunity in record["opportunities"]:
            for call in opportunity["gong_calls"]:
                call_ids.append(call["id"])
        for call in record["account_level_gong_calls"]:
            call_ids.append(call["id"])
    return call_ids


def find_opportunity(record: dict, name: str) -> dict:
    for opportunity in record["opportunities"]:
        if opportunity["source"]["Name"] == name:
            return opportunity
    raise AssertionError(f"No opportunity named {name!r}")


def call_date(call: dict) -> date:
    return call["date"]


# --- Record counts and no duplication ----------------------------------------
def test_one_record_per_account(records):
    account_ids = [account_id(record) for record in records]
    assert len(records) == 30
    assert len(set(account_ids)) == 30


def test_every_opportunity_appears_exactly_once(records):
    opportunity_ids = [opportunity["source"]["Id"]
                       for opportunity in all_opportunities(records)]
    source_ids = {row["Id"] for row in source_rows("opportunities.csv")}

    assert len(opportunity_ids) == 100
    assert set(opportunity_ids) == source_ids


def test_every_gong_call_appears_exactly_once(records):
    call_ids = all_gong_call_ids(records)
    source_ids = {row["id"] for row in source_rows("gong_calls.csv")}

    assert len(call_ids) == 44
    assert set(call_ids) == source_ids


def test_open_opportunity_amount_not_inflated_by_joins(records, records_by_name):
    # Opportunities with several Gong calls must still be counted once.
    # Expected total comes straight from the CSV, independent of the join.
    expected_total = 0.0
    for row in source_rows("opportunities.csv"):
        if row["IsClosed"] == "false":
            expected_total += float(row["Amount"])

    # Total across all integrated account records.
    integrated_total = 0.0
    for record in records:
        integrated_total += record["derived"]["open_opportunity_amount_total"]

    assert integrated_total == expected_total
    krakatoa = records_by_name["Krakatoa"]["derived"]
    assert krakatoa["open_opportunity_amount_total"] == 1_770_000


# --- Relationships -------------------------------------------------------------
def test_opportunities_belong_to_their_account(records):
    for record in records:
        for opportunity in record["opportunities"]:
            assert opportunity["source"]["AccountId"] == account_id(record)


def test_linked_calls_sit_under_their_opportunity(records):
    for record in records:
        for opportunity in record["opportunities"]:
            for call in opportunity["gong_calls"]:
                assert call["associated_opp"] == opportunity["source"]["Id"]
                assert call["associated_account"] == account_id(record)


def test_account_level_calls_not_attributed_to_opportunities(records):
    for record in records:
        for call in record["account_level_gong_calls"]:
            assert call["associated_opp"] is None
            assert call["associated_account"] == account_id(record)


def test_one_owner_per_account_from_opportunities(records, records_by_name):
    # Each account's opportunities share a single owner.
    for record in records:
        assert len(record["derived"]["opportunity_owner_ids"]) == 1

    # Four AMs in total; the demo AM (Krakatoa's owner) has 8 accounts.
    owner_ids = {record["derived"]["opportunity_owner_id"] for record in records}
    assert len(owner_ids) == 4

    demo_am = records_by_name["Krakatoa"]["derived"]["opportunity_owner_id"]
    demo_am_accounts = [record for record in records
                        if record["derived"]["opportunity_owner_id"] == demo_am]
    assert len(demo_am_accounts) == 8


# --- Missing data is preserved, not filled in ----------------------------------
def test_accounts_without_gong_history(records):
    accounts_without_gong = {account_name(record) for record in records
                             if not record["derived"]["has_gong_history"]}
    assert accounts_without_gong == NO_GONG_ACCOUNTS

    # Those accounts report no calls in any scope, rather than invented values.
    for record in records:
        if account_name(record) not in NO_GONG_ACCOUNTS:
            continue
        derived = record["derived"]
        assert derived["gong_call_count"] == 0
        for field in LATEST_ACCOUNT_CALL_FIELDS:
            assert derived[field] is None


def test_missing_salesforce_activity_stays_none(records_by_name):
    renewal = find_opportunity(records_by_name["Monogram"],
                               "Monogram - Renewal - Jun 2027")
    assert renewal["source"]["LastActivityDate"] is None
    assert renewal["derived"]["salesforce_last_activity_date"] is None


def test_opportunity_without_calls_has_no_latest_call(records):
    opportunities_without_calls = [opportunity
                                   for opportunity in all_opportunities(records)
                                   if not opportunity["gong_calls"]]
    assert opportunities_without_calls

    for opportunity in opportunities_without_calls:
        assert opportunity["derived"]["latest_opportunity_gong_call"] is None


def test_salesforce_activity_matches_source_csv(records):
    # LastActivityDate per opportunity as stored in the CSV (blank -> None).
    source_activity = {}
    for row in source_rows("opportunities.csv"):
        source_activity[row["Id"]] = row["LastActivityDate"] or None

    # The parsed date must match the source exactly, including missing values.
    for opportunity in all_opportunities(records):
        parsed = opportunity["derived"]["salesforce_last_activity_date"]
        as_text = parsed.isoformat() if parsed else None
        assert as_text == source_activity[opportunity["source"]["Id"]]


# --- Krakatoa: stale Salesforce activity, recent Gong engagement ---------------
def test_krakatoa_salesforce_and_gong_dates_preserved(records_by_name):
    krakatoa = records_by_name["Krakatoa"]
    renewal = find_opportunity(krakatoa, "Krakatoa - Renewal - Nov 2026")

    # Salesforce activity is untouched by the newer Gong call.
    assert renewal["source"]["LastActivityDate"] == date(2026, 10, 8)
    assert renewal["derived"]["salesforce_last_activity_date"] == date(2026, 10, 8)
    assert renewal["derived"]["latest_opportunity_gong_call"] == {
        "id": "gong_call_0034", "date": date(2026, 11, 6)}

    # The account-level call is tracked separately and not attached to any opp.
    assert krakatoa["derived"]["latest_account_level_gong_call"] == {
        "id": "gong_call_0041", "date": date(2026, 11, 12)}
    for opportunity in krakatoa["opportunities"]:
        for call in opportunity["gong_calls"]:
            assert call["id"] != "gong_call_0041"

    assert krakatoa["derived"]["latest_opportunity_salesforce_activity_date"] == \
        date(2026, 10, 8)


# --- Validation rejects data that can't be joined safely -----------------------
def test_rejects_opportunity_with_unknown_account(data_copy):
    # Point one opportunity at an account that doesn't exist.
    path = data_copy / "opportunities.csv"
    fieldnames, rows = read_csv_rows(path)
    rows[0]["AccountId"] = "001Hp00000XXXXXAAA"
    write_csv_rows(path, fieldnames, rows)

    with pytest.raises(IntegrationError, match="unknown Account"):
        load_and_integrate(data_copy)


def test_rejects_gong_call_linked_to_another_accounts_opportunity(data_copy):
    # Re-link one opportunity call to a different account's opportunity,
    # leaving its associated_account unchanged.
    path = data_copy / "gong_calls.csv"
    fieldnames, calls = read_csv_rows(path)
    linked_calls = [call for call in calls if call["associated_opp"]]
    call = linked_calls[0]

    other_account_opportunities = [row for row in source_rows("opportunities.csv")
                                   if row["AccountId"] != call["associated_account"]]
    call["associated_opp"] = other_account_opportunities[0]["Id"]
    write_csv_rows(path, fieldnames, calls)

    with pytest.raises(IntegrationError, match="belongs to"):
        load_and_integrate(data_copy)


def test_rejects_duplicate_opportunity_ids(data_copy):
    # Append an exact copy of an existing opportunity.
    path = data_copy / "opportunities.csv"
    fieldnames, rows = read_csv_rows(path)
    rows.append(dict(rows[0]))
    write_csv_rows(path, fieldnames, rows)

    with pytest.raises(IntegrationError, match="Duplicate"):
        load_and_integrate(data_copy)


# --- Latest-Gong-call fields: scope and structure ------------------------------
def test_latest_gong_call_any_scope_is_latest_of_both_scopes(records):
    # For each account, the any-scope call must be the newer of the
    # opportunity-linked and account-level calls (or None if neither exists).
    for record in records:
        derived = record["derived"]
        opportunity_call = derived["latest_opportunity_linked_gong_call"]
        account_call = derived["latest_account_level_gong_call"]

        calls = [call for call in (opportunity_call, account_call) if call]
        expected = max(calls, key=call_date) if calls else None

        assert derived["latest_gong_call_any_scope"] == expected


def test_krakatoa_latest_call_any_scope_is_account_level(records_by_name):
    # Krakatoa's newest call (12 Nov) is account-level, newer than any
    # opportunity-linked call (6 Nov).
    derived = records_by_name["Krakatoa"]["derived"]
    assert derived["latest_opportunity_linked_gong_call"]["id"] == "gong_call_0034"
    assert derived["latest_gong_call_any_scope"] == {
        "id": "gong_call_0041", "date": date(2026, 11, 12)}


def test_all_latest_gong_call_fields_are_id_date_or_none(records):
    # Collect every latest-call value at account and opportunity level.
    values = []
    for record in records:
        for field in LATEST_ACCOUNT_CALL_FIELDS:
            values.append(record["derived"][field])
        for opportunity in record["opportunities"]:
            values.append(opportunity["derived"]["latest_opportunity_gong_call"])

    # Each one is either None or exactly {id, date}.
    for value in values:
        if value is None:
            continue
        assert set(value) == {"id", "date"}
        assert isinstance(value["date"], date)


# --- Accounts with no opportunities (temporary test data) ----------------------
def test_account_with_no_opportunities(data_copy):
    account_with_call_id = "001Hp00000TEST1AAA"
    empty_account_id = "001Hp00000TEST2AAA"

    # Add two accounts with no opportunities: one with an account-level
    # Gong call, one with no Gong history at all.
    accounts_path = data_copy / "accounts.csv"
    fieldnames, accounts = read_csv_rows(accounts_path)
    accounts.append({"Id": account_with_call_id, "Name": "Test Account With Call"})
    accounts.append({"Id": empty_account_id, "Name": "Test Account Empty"})
    write_csv_rows(accounts_path, fieldnames, accounts)

    # Give the first test account a single account-level call.
    calls_path = data_copy / "gong_calls.csv"
    fieldnames, calls = read_csv_rows(calls_path)
    calls.append({
        "id": "gong_call_9999",
        "started": "2026-11-01T10:00:00+01:00",
        "brief": "Test call.",
        "key_points": '["Test point"]',
        "associated_account": account_with_call_id,
        "associated_opp": "",
        "url": "https://gong.example.invalid/call?id=gong_call_9999",
    })
    write_csv_rows(calls_path, fieldnames, calls)

    records = {account_id(record): record for record in load_and_integrate(data_copy)}
    assert len(records) == 32

    # Both accounts get empty opportunity data, not errors or invented values.
    for test_account_id in (account_with_call_id, empty_account_id):
        record = records[test_account_id]
        derived = record["derived"]
        assert record["opportunities"] == []
        assert derived["opportunity_count"] == 0
        assert derived["open_opportunity_count"] == 0
        assert derived["open_opportunity_amount_total"] == 0.0
        assert derived["opportunity_owner_ids"] == []
        assert derived["opportunity_owner_id"] is None
        assert derived["latest_opportunity_salesforce_activity_date"] is None
        assert derived["latest_opportunity_linked_gong_call"] is None

    # The account-level call is still found without any opportunity link.
    with_call = records[account_with_call_id]["derived"]
    expected_call = {"id": "gong_call_9999", "date": date(2026, 11, 1)}
    assert with_call["latest_account_level_gong_call"] == expected_call
    assert with_call["latest_gong_call_any_scope"] == expected_call
    assert with_call["has_gong_history"] is True
    assert with_call["gong_call_count"] == 1

    # The account with no calls reports no Gong history.
    empty = records[empty_account_id]["derived"]
    assert empty["latest_account_level_gong_call"] is None
    assert empty["latest_gong_call_any_scope"] is None
    assert empty["has_gong_history"] is False
    assert empty["gong_call_count"] == 0


# --- Underlying Salesforce and Gong dates are preserved -----------------------
def test_latest_opportunity_gong_call_matches_source_csv(records):
    # Recompute each opportunity's latest linked call straight from the CSV.
    latest_call_by_opportunity = {}
    for row in source_rows("gong_calls.csv"):
        opportunity_id = row["associated_opp"]
        if not opportunity_id:
            continue
        current = latest_call_by_opportunity.get(opportunity_id)
        if current is None or row["started"] > current["started"]:
            latest_call_by_opportunity[opportunity_id] = row

    for opportunity in all_opportunities(records):
        expected_row = latest_call_by_opportunity.get(opportunity["source"]["Id"])
        actual = opportunity["derived"]["latest_opportunity_gong_call"]
        if expected_row is None:
            assert actual is None
        else:
            assert actual == {
                "id": expected_row["id"],
                "date": date.fromisoformat(expected_row["started"][:10]),
            }


def test_saltmarsh_missing_salesforce_activity_preserved_alongside_gong(records_by_name):
    # Saltmarsh's Marketplace payouts deal has Gong calls but no Salesforce
    # LastActivityDate. Both facts are kept as they are; nothing is inferred.
    opportunity = find_opportunity(records_by_name["Saltmarsh"],
                                   "Saltmarsh - New - Marketplace payouts")
    call_ids = [call["id"] for call in opportunity["gong_calls"]]

    assert opportunity["source"]["LastActivityDate"] is None
    assert opportunity["derived"]["salesforce_last_activity_date"] is None
    assert call_ids == ["gong_call_0024", "gong_call_0033"]
    assert opportunity["derived"]["latest_opportunity_gong_call"] == {
        "id": "gong_call_0033", "date": date(2026, 11, 5)}
    assert set(opportunity["derived"]) == {"salesforce_last_activity_date",
                                           "latest_opportunity_gong_call"}


def test_account_salesforce_date_ignores_missing_opportunity_dates(records_by_name):
    # One Saltmarsh opportunity has no LastActivityDate; the account-level date
    # is the latest of the dates that exist, not None.
    saltmarsh = records_by_name["Saltmarsh"]
    dates = [opportunity["source"]["LastActivityDate"]
             for opportunity in saltmarsh["opportunities"]]
    known_dates = [activity_date for activity_date in dates if activity_date is not None]

    assert None in dates
    assert saltmarsh["derived"]["latest_opportunity_salesforce_activity_date"] == \
        max(known_dates)
