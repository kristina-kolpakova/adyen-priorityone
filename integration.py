"""PriorityOne Phase 2a: load, validate and join the source CSVs.

Produces one unified record per Salesforce Account, holding every opportunity
and Gong call that belongs to it. This module only joins and summarises data;
it does no scoring, Gong classification, confidence or recommendations (those
come in Phase 2b, in scoring.py).

Each record keeps two kinds of data apart:
- "source": values exactly as they appear in the CSVs, only type-converted
  (dates -> date, Amount -> float, IsClosed -> bool, key_points -> list).
  Empty cells become None; nothing is filled in or overwritten.
- "derived": facts computed from the source data (counts, totals, latest
  dates). Every derived field says what it was computed from. Comparisons
  between Salesforce and Gong dates are left to Phase 2b.

Activity rules (agreed design decision):
- Salesforce LastActivityDate is never overwritten by Gong.
- Opportunity-linked Gong calls and account-level Gong calls are tracked
  separately; account-level calls are never attributed to an opportunity.

Usage:
    .venv/bin/python integration.py              # summary of all accounts
    .venv/bin/python integration.py Krakatoa     # one account as JSON
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date, datetime
from operator import itemgetter
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

ACCOUNT_FIELDS = ["Id", "Name"]
OPPORTUNITY_FIELDS = ["Id", "AccountId", "OwnerId", "Name", "Amount",
                      "CreatedDate", "StageName", "CloseDate", "Type",
                      "IsClosed", "ForecastCategory", "LastActivityDate",
                      "NextStep"]
GONG_FIELDS = ["id", "started", "brief", "key_points", "associated_account",
               "associated_opp", "url"]


class IntegrationError(ValueError):
    """The source data can't be joined safely (bad columns, IDs or links)."""


# --------------------------------------------------------------------------
# Loading: read CSVs and convert types. No values are altered or inferred.
# --------------------------------------------------------------------------
def _read_csv(path: Path, expected_fields: list[str]) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != expected_fields:
            raise IntegrationError(
                f"{path.name}: expected columns {expected_fields}, "
                f"got {reader.fieldnames}")
        return list(reader)


def _blank_to_none(value: str) -> str | None:
    return value if value != "" else None


def _parse_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def _parse_sf_datetime(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f%z")


def _parse_bool(value: str, field: str) -> bool:
    if value not in ("true", "false"):
        raise IntegrationError(f"{field}: expected true/false, got {value!r}")
    return value == "true"


def load_accounts(path: Path) -> list[dict]:
    return [{"Id": row["Id"], "Name": row["Name"]}
            for row in _read_csv(path, ACCOUNT_FIELDS)]


def load_opportunities(path: Path) -> list[dict]:
    opportunities = []
    for row in _read_csv(path, OPPORTUNITY_FIELDS):
        opportunities.append({
            "Id": row["Id"],
            "AccountId": row["AccountId"],
            "OwnerId": _blank_to_none(row["OwnerId"]),
            "Name": row["Name"],
            "Amount": float(row["Amount"]) if row["Amount"] else None,
            "CreatedDate": _parse_sf_datetime(row["CreatedDate"]),
            "StageName": row["StageName"],
            "CloseDate": _parse_date(row["CloseDate"]),
            "Type": _blank_to_none(row["Type"]),
            "IsClosed": _parse_bool(row["IsClosed"], f"{row['Id']}.IsClosed"),
            "ForecastCategory": _blank_to_none(row["ForecastCategory"]),
            "LastActivityDate": _parse_date(row["LastActivityDate"]),
            "NextStep": _blank_to_none(row["NextStep"]),
        })
    return opportunities


def load_gong_calls(path: Path) -> list[dict]:
    calls = []
    for row in _read_csv(path, GONG_FIELDS):
        try:
            key_points = json.loads(row["key_points"])
        except json.JSONDecodeError as error:
            raise IntegrationError(f"{row['id']}.key_points is not JSON: {error}")
        calls.append({
            "id": row["id"],
            "started": datetime.fromisoformat(row["started"]),
            "brief": row["brief"],
            "key_points": key_points,
            "associated_account": row["associated_account"],
            "associated_opp": _blank_to_none(row["associated_opp"]),
            "url": row["url"],
        })
    return calls


# --------------------------------------------------------------------------
# Validation: fail loudly rather than join bad data.
# --------------------------------------------------------------------------
def _check_unique(rows: list[dict], key: str, label: str) -> None:
    seen: set[str] = set()
    for row in rows:
        if row[key] in seen:
            raise IntegrationError(f"Duplicate {label} {key}: {row[key]}")
        seen.add(row[key])


def validate(accounts: list[dict], opportunities: list[dict],
             gong_calls: list[dict]) -> None:
    # Every source record needs a unique ID before anything is joined.
    _check_unique(accounts, "Id", "Account")
    _check_unique(opportunities, "Id", "Opportunity")
    _check_unique(gong_calls, "id", "Gong call")

    account_ids = {account["Id"] for account in accounts}
    account_id_by_opportunity = {opportunity["Id"]: opportunity["AccountId"]
                                 for opportunity in opportunities}

    # Every opportunity must belong to a known account.
    for opportunity in opportunities:
        if opportunity["AccountId"] not in account_ids:
            raise IntegrationError(
                f"Opportunity {opportunity['Id']} references unknown Account "
                f"{opportunity['AccountId']}")
    # Every Gong call must point to a known account. A linked opportunity must
    # exist and belong to that same account, or the call would be filed under
    # the wrong customer.
    for call in gong_calls:
        if call["associated_account"] not in account_ids:
            raise IntegrationError(
                f"Gong call {call['id']} references unknown Account "
                f"{call['associated_account']}")
        opportunity_id = call["associated_opp"]
        if opportunity_id is not None:
            if opportunity_id not in account_id_by_opportunity:
                raise IntegrationError(
                    f"Gong call {call['id']} references unknown Opportunity "
                    f"{opportunity_id}")
            opportunity_account_id = account_id_by_opportunity[opportunity_id]
            if opportunity_account_id != call["associated_account"]:
                raise IntegrationError(
                    f"Gong call {call['id']}: Opportunity {opportunity_id} belongs to "
                    f"{opportunity_account_id}, not {call['associated_account']}")


# --------------------------------------------------------------------------
# Integration: one record per account.
# Opportunities and calls are grouped by ID (never cross-joined), so each
# source row appears exactly once and amounts are summed once per opportunity.
# --------------------------------------------------------------------------
def _latest_call(calls: list[dict]) -> dict | None:
    # Find the most recent call by start time; return {id, date} or None.
    latest = None
    for call in calls:
        if latest is None or call["started"] > latest["started"]:
            latest = call
    if latest is None:
        return None
    return {"id": latest["id"], "date": latest["started"].date()}


def build_account_records(accounts: list[dict], opportunities: list[dict],
                          gong_calls: list[dict]) -> list[dict]:
    # Group Salesforce opportunities by their parent account.
    opportunities_by_account: dict[str, list[dict]] = {
        account["Id"]: [] for account in accounts}
    for opportunity in opportunities:
        opportunities_by_account[opportunity["AccountId"]].append(opportunity)

    # Separate Gong calls linked to an opportunity from account-level calls.
    # Account-level calls are never attributed to an opportunity.
    calls_by_opportunity: dict[str, list[dict]] = {
        opportunity["Id"]: [] for opportunity in opportunities}
    account_level_calls: dict[str, list[dict]] = {
        account["Id"]: [] for account in accounts}
    for call in gong_calls:
        if call["associated_opp"] is None:
            account_level_calls[call["associated_account"]].append(call)
        else:
            calls_by_opportunity[call["associated_opp"]].append(call)

    # Build one integrated record per Salesforce account.
    records = []
    for account in accounts:
        opportunity_entries = []
        opportunity_linked_calls = []
        salesforce_activity_dates = []
        owner_ids = set()
        open_opportunity_count = 0
        open_opportunity_amount_total = 0.0

        # Attach Gong calls to each opportunity and collect account-level
        # totals. Each opportunity is visited once, so amounts are never
        # multiplied by the number of calls linked to it.
        for opportunity in opportunities_by_account[account["Id"]]:
            linked_calls = sorted(calls_by_opportunity[opportunity["Id"]],
                                  key=itemgetter("started"))
            opportunity_entries.append({
                "source": opportunity,
                "gong_calls": linked_calls,
                "derived": {
                    # Parsed Opportunity.LastActivityDate, unchanged.
                    "salesforce_last_activity_date": opportunity["LastActivityDate"],
                    # Latest Gong call linked to this one opportunity.
                    "latest_opportunity_gong_call": _latest_call(linked_calls),
                },
            })

            opportunity_linked_calls.extend(linked_calls)
            if opportunity["LastActivityDate"] is not None:
                salesforce_activity_dates.append(opportunity["LastActivityDate"])
            if opportunity["OwnerId"] is not None:
                owner_ids.add(opportunity["OwnerId"])
            if not opportunity["IsClosed"]:
                open_opportunity_count += 1
                open_opportunity_amount_total += opportunity["Amount"] or 0

        # Combine the two Gong scopes only for the account-wide call fields.
        account_calls = sorted(account_level_calls[account["Id"]],
                               key=itemgetter("started"))
        all_account_calls = opportunity_linked_calls + account_calls
        owner_ids = sorted(owner_ids)

        if salesforce_activity_dates:
            latest_salesforce_activity = max(salesforce_activity_dates)
        else:
            latest_salesforce_activity = None

        if len(owner_ids) == 1:
            single_owner_id = owner_ids[0]
        else:
            single_owner_id = None

        # Assemble the account record with source data and derived summaries.
        records.append({
            "source": {
                "account": account,
            },
            "opportunities": opportunity_entries,
            "account_level_gong_calls": account_calls,
            "derived": {
                # Inferred from Opportunity.OwnerId (our schema has no
                # Account.OwnerId). One owner is expected; more stay visible.
                "opportunity_owner_ids": owner_ids,
                "opportunity_owner_id": single_owner_id,
                "opportunity_count": len(opportunity_entries),
                "open_opportunity_count": open_opportunity_count,
                # Sum of Amount over open opportunities (renewals included),
                # each opportunity counted once.
                "open_opportunity_amount_total": open_opportunity_amount_total,
                # Latest Opportunity.LastActivityDate across this account's
                # opportunities. Not complete account activity: our schema has
                # no Account-level activity. None if no opportunity has one.
                "latest_opportunity_salesforce_activity_date": latest_salesforce_activity,
                # Latest Gong call linked to any of this account's opportunities.
                "latest_opportunity_linked_gong_call": _latest_call(opportunity_linked_calls),
                # Latest Gong call on the account with no opportunity link.
                "latest_account_level_gong_call": _latest_call(account_calls),
                # Latest Gong call on the account, linked or not.
                "latest_gong_call_any_scope": _latest_call(all_account_calls),
                "gong_call_count": len(all_account_calls),
                "has_gong_history": len(all_account_calls) > 0,
            },
        })
    return records


def load_and_integrate(data_dir: Path = DATA_DIR) -> list[dict]:
    accounts = load_accounts(data_dir / "accounts.csv")
    opportunities = load_opportunities(data_dir / "opportunities.csv")
    gong_calls = load_gong_calls(data_dir / "gong_calls.csv")
    validate(accounts, opportunities, gong_calls)
    return build_account_records(accounts, opportunities, gong_calls)


# --------------------------------------------------------------------------
# CLI for reviewing the output
# --------------------------------------------------------------------------
def _to_jsonable(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    return value


def main(argv: list[str]) -> None:
    records = load_and_integrate()
    # With an account name, print that account's full record as JSON.
    if len(argv) > 1:
        name = " ".join(argv[1:])
        for record in records:
            if record["source"]["account"]["Name"] == name:
                print(json.dumps(_to_jsonable(record), indent=2))
                return
        sys.exit(f"No account named {name!r}")

    # Otherwise print a one-line summary per account.
    print(f"{len(records)} accounts")
    for record in records:
        derived = record["derived"]
        latest_call = derived["latest_gong_call_any_scope"]
        latest_call_date = latest_call["date"] if latest_call else None
        print(f"  {record['source']['account']['Name']:22s} "
              f"opps={derived['opportunity_count']} "
              f"open={derived['open_opportunity_count']} "
              f"open_amount={derived['open_opportunity_amount_total']:>12,.0f} "
              f"gong={derived['gong_call_count']} "
              f"opp_sf_activity={derived['latest_opportunity_salesforce_activity_date']} "
              f"latest_gong={latest_call_date}")


if __name__ == "__main__":
    main(sys.argv)
