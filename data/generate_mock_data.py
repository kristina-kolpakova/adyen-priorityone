"""Generate PriorityOne's fictional Salesforce and Gong mock datasets.

Outputs (written next to this script):
    accounts.csv       30 Salesforce Accounts      (Id, Name)
    opportunities.csv  100 Salesforce Opportunities
    gong_calls.csv     44 simplified Gong call records

Run from the project root:
    .venv/bin/python data/generate_mock_data.py

The output is deterministic: a fixed random seed and a fixed reference date
(2026-11-15) mean every run produces identical files.

All companies, people, deals and calls are fictional. Stage names are an
illustrative pipeline configuration, not Adyen's real Salesforce setup.

Assumptions:
- Amounts are EUR (the schema has no currency field).
- One opportunity owner per account; that OwnerId stands in for the
  account's AM. In real Salesforce the Opportunity owner is not necessarily
  the person responsible for the account.
- There is no stage history. CreatedDate is the only measure of how old an
  opportunity is; nothing here says how long it has sat in its current stage.
- Renewals are annual and named by close month ("Renewal - Nov 2026"). When an
  account has an open and a won renewal, the won one closed a year earlier.
- Gong briefs for the 25 generated accounts come from 14 call types with
  several phrasings each; customer contact roles are fictional job titles.
- ForecastCategory: open opps use Commit / Best Case / Pipeline; Closed Won is
  "Closed" and Closed Lost is "Omitted" (standard Salesforce mapping).
"""

from __future__ import annotations

import csv
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SEED = 20261115
REFERENCE_DATE = date(2026, 11, 15)
OUT_DIR = Path(__file__).resolve().parent

rng = random.Random(SEED)

# --------------------------------------------------------------------------
# Salesforce ID helpers
# --------------------------------------------------------------------------
BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CHECKSUM_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
KEY_PREFIX = {"Account": "001", "Opportunity": "006", "User": "005"}
POD = "Hp"  # fictional instance identifier
_used_ids: set[str] = set()


def sf_checksum(id15: str) -> str:
    """Salesforce case-safe suffix: one char per 5-char chunk, encoding which
    characters in that chunk are uppercase letters."""
    suffix = ""
    for chunk_start in range(0, 15, 5):
        flags = 0
        for i, ch in enumerate(id15[chunk_start:chunk_start + 5]):
            if "A" <= ch <= "Z":
                flags |= 1 << i
        suffix += CHECKSUM_CHARS[flags]
    return suffix


def sf_id(sobject: str) -> str:
    while True:
        body = "00000" + "".join(rng.choice(BASE62) for _ in range(5))
        id15 = KEY_PREFIX[sobject] + POD + body
        if id15 not in _used_ids:
            _used_ids.add(id15)
            return id15 + sf_checksum(id15)


# --------------------------------------------------------------------------
# Date helpers
# --------------------------------------------------------------------------
def days_ago(n: int) -> date:
    return REFERENCE_DATE - timedelta(days=n)


def days_ahead(n: int) -> date:
    return REFERENCE_DATE + timedelta(days=n)


def sf_datetime(d: date) -> str:
    """Salesforce export datetime, UTC, business hours."""
    dt = datetime(d.year, d.month, d.day, rng.randint(7, 16),
                  rng.choice([0, 5, 15, 20, 30, 40, 45, 50]), 0,
                  tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000+0000")


def gong_started(d: date) -> str:
    """Gong-style ISO 8601 with Amsterdam offset (CET/CEST)."""
    offset = "+02:00" if (4 <= d.month <= 9) or (d.month == 10 and d.day < 25) \
        or (d.month == 3 and d.day >= 29) else "+01:00"
    hour = rng.randint(9, 17)
    minute = rng.choice([0, 0, 15, 30, 30, 45])
    return f"{d.isoformat()}T{hour:02d}:{minute:02d}:00{offset}"


# --------------------------------------------------------------------------
# Owners (4 AMs). Owner 0 is the demo AM.
# --------------------------------------------------------------------------
OWNERS = [sf_id("User") for _ in range(4)]
DEMO_AM = OWNERS[0]

# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------
FEATURED = ["Krakatoa", "Aster", "Mosaic", "Wayfarer", "Monogram"]
OTHER_NAMES = [
    "Bramblewood", "Cobalt", "Tidewater", "Fernhill",
    "Quayside", "Pinecrest", "Saltmarsh",
    "Orchard Lane", "Copperleaf", "Driftwood",
    "Halcyon", "Kestrel", "Larkspur",
    "Marlowe", "Lanternfly", "Oakmoor", "Petrel",
    "Quillon", "Redfern", "Silverbirch",
    "Thistle", "Umberleaf", "Vellum",
    "Willowbank", "Zephyrine",
]

accounts: list[dict] = [{"Id": sf_id("Account"), "Name": n}
                        for n in FEATURED + OTHER_NAMES]
acct = {a["Name"]: a["Id"] for a in accounts}

# Ownership: demo AM owns the 5 featured accounts + 3 others; the remaining
# 22 are split across the other three AMs.
account_owner: dict[str, str] = {}
for name in FEATURED:
    account_owner[acct[name]] = DEMO_AM
others_shuffled = OTHER_NAMES[:]
rng.shuffle(others_shuffled)
for name in others_shuffled[:3]:
    account_owner[acct[name]] = DEMO_AM
for i, name in enumerate(others_shuffled[3:]):
    account_owner[acct[name]] = OWNERS[1 + i % 3]

# --------------------------------------------------------------------------
# Opportunities
# --------------------------------------------------------------------------
OPP_FIELDS = ["Id", "AccountId", "OwnerId", "Name", "Amount", "CreatedDate",
              "StageName", "CloseDate", "Type", "IsClosed", "ForecastCategory",
              "LastActivityDate", "NextStep"]
opportunities: list[dict] = []
opp_key: dict[str, str] = {}  # featured scenario key -> opp Id


def add_opp(account: str, name: str, type_: str, stage: str, amount: float,
            created: date, close: date, last_activity: date | None,
            next_step: str = "", forecast: str | None = None,
            key: str | None = None) -> dict:
    account_id = acct[account]
    is_closed = stage in ("Closed Won", "Closed Lost")
    if forecast is None:
        forecast = {"Closed Won": "Closed", "Closed Lost": "Omitted",
                    "Negotiation": "Commit", "Proposal": "Best Case"
                    }.get(stage, "Pipeline")
    opp = {
        "Id": sf_id("Opportunity"),
        "AccountId": account_id,
        "OwnerId": account_owner[account_id],
        "Name": f"{account} - {name}",
        "Amount": f"{amount:.2f}",
        "CreatedDate": sf_datetime(created),
        "StageName": stage,
        "CloseDate": close.isoformat(),
        "Type": type_,
        "IsClosed": "true" if is_closed else "false",
        "ForecastCategory": forecast,
        "LastActivityDate": last_activity.isoformat() if last_activity else "",
        "NextStep": next_step,
    }
    opportunities.append(opp)
    if key:
        opp_key[key] = opp["Id"]
    return opp


# ---- Featured scenarios (hand-designed) ----------------------------------
# Krakatoa: revenue risk. Large Commit renewal closing in 12 days with no
# activity for 5+ weeks, a stalled overdue upsell, and a recent lost deal.
add_opp("Krakatoa", "Renewal", "Renewal", "Negotiation", 1_450_000,
        date(2026, 8, 18), days_ahead(12), date(2026, 10, 8),
        "Confirm renewal pricing with procurement", key="K_RENEWAL")
add_opp("Krakatoa", "Upsell - Unified commerce POS rollout", "Upsell",
        "Proposal", 320_000, date(2025, 9, 2), date(2026, 10, 31),
        date(2026, 9, 12), "", key="K_POS")
add_opp("Krakatoa", "New - Marketplace payouts", "New", "Closed Lost",
        180_000, date(2026, 2, 9), date(2026, 8, 21), date(2026, 8, 19))
add_opp("Krakatoa", "Renewal", "Renewal", "Closed Won", 1_300_000,
        date(2025, 8, 25), date(2025, 11, 28), date(2025, 11, 27))

# Aster: upsell / expansion. Proposal requested for Brazil expansion, early
# interest in Pay by Bank, renewal far out.
add_opp("Aster", "Upsell - Brazil local payment methods", "Upsell",
        "Proposal", 410_000, date(2026, 9, 15), days_ahead(34),
        date(2026, 11, 13), "Send proposal covering Pix and Boleto",
        key="A_BRAZIL")
add_opp("Aster", "Upsell - Pay by Bank", "Upsell", "Discovery", 95_000,
        date(2026, 10, 20), date(2027, 2, 26), date(2026, 11, 4),
        "Share Pay by Bank case studies", key="A_PBB")
add_opp("Aster", "Renewal", "Renewal", "Qualification", 640_000,
        date(2026, 10, 1), date(2027, 5, 31), date(2026, 10, 28), "")
add_opp("Aster", "New - Online checkout", "New", "Closed Won", 520_000,
        date(2025, 1, 14), date(2025, 5, 30), date(2025, 5, 28))

# Mosaic: renewal in 23 days. Commit, recently active, but a procurement
# blocker surfaces only in Gong.
add_opp("Mosaic", "Renewal", "Renewal", "Negotiation", 880_000,
        date(2026, 8, 10), days_ahead(23), date(2026, 11, 10),
        "Legal redlines on MSA", key="M_RENEWAL")
add_opp("Mosaic", "Upsell - Risk & fraud add-on", "Upsell", "Discovery",
        60_000, date(2026, 9, 29), date(2027, 3, 15), date(2026, 10, 15),
        "Book fraud review workshop")
add_opp("Mosaic", "Renewal", "Renewal", "Closed Won", 820_000,
        date(2025, 9, 1), date(2025, 12, 10), date(2025, 12, 9))

# Wayfarer: customer health / escalation. Renewal in Proposal, a stale
# overdue upsell, a lost new-entity deal, and an escalation in Gong.
add_opp("Wayfarer", "Renewal", "Renewal", "Proposal", 560_000,
        date(2026, 9, 8), date(2027, 2, 27), date(2026, 11, 11),
        "Prepare renewal proposal", key="W_RENEWAL")
add_opp("Wayfarer", "Upsell - Network tokenization", "Upsell",
        "Qualification", 140_000, date(2026, 1, 12), date(2026, 9, 30),
        date(2026, 7, 22), "", key="W_TOKENS")
add_opp("Wayfarer", "New - Hotel bookings entity", "New", "Closed Lost",
        210_000, date(2026, 1, 20), date(2026, 6, 30), date(2026, 6, 26))

# Monogram: growth. Commit upsell for new stores, new-market deal in
# Discovery, a recent won upsell.
add_opp("Monogram", "Upsell - In-store payments for 40 new stores",
        "Upsell", "Negotiation", 275_000, date(2026, 8, 24), days_ahead(19),
        date(2026, 11, 12), "Agree final terminal pricing", key="G_STORES")
add_opp("Monogram", "New - Nordics entity", "New", "Discovery", 390_000,
        date(2026, 10, 1), date(2027, 4, 30), date(2026, 11, 5),
        "Scope Nordic payment methods", key="G_NORDICS")
add_opp("Monogram", "Renewal", "Renewal", "Qualification", 300_000,
        date(2026, 10, 12), date(2027, 6, 30), None, "")
add_opp("Monogram", "Upsell - Gift cards", "Upsell", "Closed Won", 45_000,
        date(2026, 4, 2), date(2026, 7, 15), date(2026, 7, 14))

FEATURED_OPP_COUNT = len(opportunities)  # 18 (12 open, 6 closed)

# ---- Generated opportunities for the other 25 accounts --------------------
NEW_DESCRIPTORS = ["Online checkout", "Marketplace payouts", "In-store payments",
                   "Subscription billing", "Mobile app payments", "Pay by Link",
                   "Platform onboarding", "Cross-border acquiring"]
UPSELL_DESCRIPTORS = ["Tap to Pay on mobile", "Network tokenization",
                      "Risk & fraud add-on", "Local payment methods (DE)",
                      "Local payment methods (BR)", "Card issuing",
                      "Revenue optimization", "Data & insights",
                      "Terminal fleet expansion", "Pay by Bank",
                      "Additional entity (UK)", "Additional entity (US)",
                      "Buy now pay later"]
NEXT_STEPS = {
    "Qualification": ["Confirm decision makers", "Intro call with finance",
                      "Qualify volumes and markets"],
    "Discovery": ["Technical discovery session", "Map current payment stack",
                  "Share solution overview"],
    "Proposal": ["Send commercial proposal", "Review pricing with deal desk",
                 "Follow up on proposal feedback"],
    "Negotiation": ["Finalize contract terms", "Legal review of MSA",
                    "Agree pricing and signature date"],
}

TOTAL_OPPS = 100
TARGET_OPEN = 70
other_slots = TOTAL_OPPS - FEATURED_OPP_COUNT          # 82
other_open = TARGET_OPEN - 12                          # 58
other_closed = other_slots - other_open                # 24
closed_outcomes = ["Closed Won"] * 16 + ["Closed Lost"] * (other_closed - 16)
rng.shuffle(closed_outcomes)
open_flags = [True] * other_open + [False] * other_closed
rng.shuffle(open_flags)

# 25 accounts x 3 opps = 75, plus 7 accounts with a 4th opp = 82.
per_account = {n: 3 for n in OTHER_NAMES}
for n in rng.sample(OTHER_NAMES, other_slots - 75):
    per_account[n] = 4

# Account size factor drives amounts (a few large merchants).
size = {n: rng.choice([0.4, 0.6, 0.8, 1.0, 1.0, 1.3, 1.8, 2.5])
        for n in OTHER_NAMES}


def amount_for(type_: str, account: str) -> float:
    base = {"New": (60_000, 600_000), "Upsell": (20_000, 350_000),
            "Renewal": (150_000, 900_000)}[type_]
    raw = rng.uniform(*base) * size[account]
    return round(raw / 5_000) * 5_000 or 5_000


def open_stage_for(close: date) -> str:
    days = (close - REFERENCE_DATE).days
    if days <= 30:
        return rng.choice(["Negotiation", "Negotiation", "Proposal"])
    if days <= 90:
        return rng.choice(["Proposal", "Negotiation", "Discovery"])
    return rng.choice(["Qualification", "Discovery", "Discovery", "Proposal"])


def forecast_for(stage: str) -> str:
    if stage == "Negotiation":
        return "Commit" if rng.random() < 0.8 else "Best Case"
    if stage == "Proposal":
        return "Best Case" if rng.random() < 0.75 else "Pipeline"
    return "Pipeline"


slot = 0
for account in OTHER_NAMES:
    has_open_renewal = False
    has_closed_renewal = False
    used_descriptors: set[str] = set()
    for _ in range(per_account[account]):
        is_open = open_flags[slot]
        slot += 1
        if is_open:
            if not has_open_renewal and rng.random() < 0.5:
                type_ = "Renewal"
                has_open_renewal = True
            else:
                type_ = "Upsell" if rng.random() < 0.6 else "New"

            # Close date profile: overdue / closing soon / later.
            r = rng.random()
            if r < 0.12:
                close = days_ago(rng.randint(5, 75))           # overdue
            elif r < 0.27:
                close = days_ahead(rng.randint(2, 14))         # within 14 days
            elif type_ == "Renewal" and r < 0.45:
                close = days_ahead(rng.randint(15, 30))        # renewal soon
            else:
                close = days_ahead(rng.randint(15, 240))

            # Created date: most opps 1-9 months old, some unusually old.
            if rng.random() < 0.12:
                created = days_ago(rng.randint(370, 520))      # long-open
            else:
                created = days_ago(rng.randint(20, 270))
            if created >= close:
                created = close - timedelta(days=rng.randint(60, 150))

            stage = (rng.choice(["Discovery", "Proposal", "Negotiation"])
                     if close < REFERENCE_DATE else open_stage_for(close))
            forecast = forecast_for(stage)

            r = rng.random()
            if r < 0.06:
                last_activity = None                            # never logged
            elif r < 0.18:
                last_activity = days_ago(rng.randint(46, 140))  # no recent activity
            elif r < 0.40:
                last_activity = days_ago(rng.randint(15, 45))
            else:
                last_activity = days_ago(rng.randint(0, 14))
            if last_activity and last_activity < created:
                last_activity = created + timedelta(days=rng.randint(1, 10))
            next_step = "" if rng.random() < 0.15 else rng.choice(NEXT_STEPS[stage])
        else:
            stage = closed_outcomes.pop()
            if stage == "Closed Won" and not has_closed_renewal and rng.random() < 0.5:
                type_ = "Renewal"
                has_closed_renewal = True
            else:
                type_ = "Upsell" if rng.random() < 0.5 else "New"
            # Won renewals closed 5-12 months ago; if the account also has an
            # open renewal, align_renewals() moves this to one year before it.
            close = (days_ago(rng.randint(140, 380)) if type_ == "Renewal"
                     else days_ago(rng.randint(20, 380)))
            created = close - timedelta(days=rng.randint(45, 200))
            last_activity = close - timedelta(days=rng.randint(0, 6))
            forecast = None
            next_step = ""

        if type_ == "Renewal":
            label = "Renewal"  # dated label applied in align_renewals()
        else:
            pool = NEW_DESCRIPTORS if type_ == "New" else UPSELL_DESCRIPTORS
            descriptor = rng.choice([d for d in pool if d not in used_descriptors])
            used_descriptors.add(descriptor)
            label = f"{type_} - {descriptor}"

        add_opp(account, label, type_, stage, amount_for(type_, account),
                created, close, last_activity, next_step, forecast)

# A couple of large merchants carry high-value (> EUR 1M) open renewals.
for name, amount in (("Petrel", 1_850_000), ("Tidewater", 1_200_000)):
    for o in opportunities:
        if (o["AccountId"] == acct[name] and o["Type"] == "Renewal"
                and o["IsClosed"] == "false"):
            o["Amount"] = f"{amount:.2f}"
            break
    else:
        o = next(o for o in opportunities
                 if o["AccountId"] == acct[name] and o["IsClosed"] == "false")
        o["Amount"] = f"{amount:.2f}"

# --------------------------------------------------------------------------
# Renewal timing and labels
# --------------------------------------------------------------------------
def _shift(value: str, delta: timedelta) -> str:
    """Shift the date part of a CloseDate / CreatedDate / LastActivityDate."""
    if not value:
        return value
    return (date.fromisoformat(value[:10]) + delta).isoformat() + value[10:]


def align_renewals() -> None:
    """Annual contracts: when an account has both an open renewal and a won
    renewal, the won one closed exactly a year before the open one. Then label
    every renewal with its close month, e.g. "Renewal - Nov 2026". Uses no
    randomness, so the rest of the generated data is unaffected."""
    by_account: dict[str, list[dict]] = {}
    for o in opportunities:
        if o["Type"] == "Renewal":
            by_account.setdefault(o["AccountId"], []).append(o)
    for renewals in by_account.values():
        open_r = [o for o in renewals if o["IsClosed"] == "false"]
        won_r = [o for o in renewals if o["StageName"] == "Closed Won"]
        if open_r and won_r:
            target = date.fromisoformat(open_r[0]["CloseDate"]).replace(
                year=date.fromisoformat(open_r[0]["CloseDate"]).year - 1)
            won = won_r[0]
            delta = target - date.fromisoformat(won["CloseDate"])
            for field in ("CloseDate", "CreatedDate", "LastActivityDate"):
                won[field] = _shift(won[field], delta)
    for o in opportunities:
        if o["Type"] == "Renewal":
            account_name = o["Name"].split(" - ")[0]
            close = date.fromisoformat(o["CloseDate"])
            o["Name"] = f"{account_name} - Renewal - {close:%b %Y}"


align_renewals()

# --------------------------------------------------------------------------
# Gong calls
# --------------------------------------------------------------------------
GONG_FIELDS = ["id", "started", "brief", "key_points", "associated_account",
               "associated_opp", "url"]
gong_calls: list[dict] = []


def add_call(account: str, when: date, brief: str, key_points: list[str],
             opp_id: str = "") -> None:
    gong_calls.append({
        "id": "",  # assigned after sorting by start time
        "started": gong_started(when),
        "brief": brief,
        "key_points": json.dumps(key_points),
        "associated_account": acct[account],
        "associated_opp": opp_id,
        "url": "",
        "_date": when,
    })


# ---- Featured calls (13) --------------------------------------------------
add_call("Krakatoa", date(2026, 11, 6),
         "Quarterly review with Krakatoa's Head of Payments ahead of renewal. "
         "Customer confirmed they are running a parallel evaluation with "
         "another payment provider.",
         ["Customer evaluating another payment provider before renewal",
          "Asked for a 15% reduction in processing fees",
          "Decision expected within two weeks",
          "Procurement now leading the renewal, not the payments team"],
         opp_key["K_RENEWAL"])
add_call("Krakatoa", date(2026, 10, 2),
         "Check-in on the unified commerce POS rollout. Rollout is on hold "
         "because internal IT resourcing is frozen until Q1.",
         ["Implementation delayed: IT resourcing frozen until Q1",
          "No new date committed for the store pilot",
          "Budget owner for POS has changed"],
         opp_key["K_POS"])
add_call("Krakatoa", date(2026, 11, 12),
         "Operations sync on checkout performance. Ops lead was positive "
         "about authorization rates and recent uptime.",
         ["Ops team satisfied with authorization rates",
          "No open technical issues",
          "Ops lead not involved in the renewal decision"])

add_call("Aster", date(2026, 11, 13),
         "Expansion planning call. Aster is launching in Brazil in Q2 2027 "
         "and wants local payment methods live at launch.",
         ["Expanding to Brazil in Q2 2027",
          "Requested a proposal for Pix and Boleto",
          "Strong buying intent: budget approved for the launch",
          "Wants a timeline that supports an April go-live"],
         opp_key["A_BRAZIL"])
add_call("Aster", date(2026, 10, 30),
         "Discovery on Pay by Bank to reduce card fees on high-value orders.",
         ["Interested in Pay by Bank for high-value orders",
          "Asked for case studies from similar retailers",
          "Finance team wants a cost comparison"],
         opp_key["A_PBB"])
add_call("Aster", date(2026, 8, 20),
         "Quarterly business review. General satisfaction; early mention of "
         "longer-term plans for Latin America.",
         ["Customer satisfied with current platform",
          "Mentioned possible Mexico launch in 2027",
          "No commercial asks at this stage"])

add_call("Mosaic", date(2026, 11, 10),
         "Renewal working session with Mosaic legal and procurement. Pricing "
         "is accepted, but a new procurement policy adds a security review.",
         ["Pricing accepted for the upcoming renewal",
          "New procurement policy requires a security questionnaire",
          "Legal review may push signature past the planned close date"],
         opp_key["M_RENEWAL"])
add_call("Mosaic", date(2026, 9, 24),
         "Early renewal conversation. Customer is happy and open to a "
         "multi-year agreement.",
         ["Customer satisfied with service levels",
          "Asked about a discount for a multi-year term",
          "Champion is the VP of Ecommerce"],
         opp_key["M_RENEWAL"])

add_call("Wayfarer", date(2026, 11, 11),
         "Escalation call requested by Wayfarer's VP Finance about payout "
         "delays and settlement reconciliation issues.",
         ["Customer dissatisfied with payout delays over the last month",
          "Settlement reports not reconciling with their ledger",
          "Requested an executive sponsor and a remediation plan",
          "Renewal discussions on hold until issues are resolved"])
add_call("Wayfarer", date(2026, 10, 21),
         "Renewal planning call. The 3DS2 migration is running late and "
         "affecting conversion on European bookings.",
         ["Implementation delay on 3DS2 migration",
          "Customer reports lower conversion on EU bookings",
          "Wants migration fixed before discussing renewal terms"],
         opp_key["W_RENEWAL"])
add_call("Wayfarer", date(2026, 7, 22),
         "Intro call on network tokenization. Interest, but no follow-up "
         "agreed.",
         ["Initial interest in network tokens",
          "No technical owner identified on customer side",
          "No follow-up meeting scheduled"],
         opp_key["W_TOKENS"])

add_call("Monogram", date(2026, 11, 12),
         "Store rollout planning for Monogram's 40 new stores. Rollout "
         "schedule confirmed by their retail ops team.",
         ["Positive buying intent: rollout schedule confirmed",
          "Terminal pricing is the last open item",
          "Wants first 10 stores live in January"],
         opp_key["G_STORES"])
add_call("Monogram", date(2026, 11, 5),
         "Discovery for Monogram's Nordics expansion.",
         ["Expanding into Denmark, Norway and Sweden next year",
          "Interested in local Nordic wallets",
          "Needs a separate legal entity set up first"],
         opp_key["G_NORDICS"])

FEATURED_CALLS = len(gong_calls)  # 13

# ---- Generated calls for other accounts (31) ------------------------------
# Each template says where it fits: "account" calls are never tied to an
# opportunity; opportunity calls only link to opps whose type/stage matches
# (e.g. a procurement blocker only on late-stage deals, an RFP kickoff only on
# early-stage New/Upsell deals).
LATE = {"Proposal", "Negotiation"}
EARLY = {"Qualification", "Discovery"}


def late_stage(o: dict) -> bool:
    return o["StageName"] in LATE


def early_new_or_upsell(o: dict) -> bool:
    return o["StageName"] in EARLY and o["Type"] in ("New", "Upsell")


def new_or_upsell(o: dict) -> bool:
    return o["Type"] in ("New", "Upsell")


def evaluating_new_or_upsell(o: dict) -> bool:
    return o["StageName"] in {"Discovery", "Proposal"} and o["Type"] in ("New", "Upsell")


def renewal(o: dict) -> bool:
    return o["Type"] == "Renewal"


# (kind, scope, brief, key_points); scope is "account" or a predicate on the opp
TEMPLATES = [
    ("risk", late_stage,
     "Pricing review call. Customer is benchmarking fees against another "
     "payment provider.",
     ["Customer benchmarking fees against another provider",
      "Asked for a pricing review before signing",
      "Champion still supportive internally"]),
    ("risk", late_stage,
     "Call with finance about commercial terms. Pricing pushback on the "
     "current proposal.",
     ["Pricing objection on transaction fees",
      "Finance wants a revised offer",
      "Timeline unchanged for now"]),
    ("risk", late_stage,
     "Procurement call. Vendor onboarding is slowing the deal down.",
     ["Procurement blocker: vendor onboarding not started",
      "Security questionnaire outstanding",
      "Signature unlikely before the planned close date"]),
    ("risk", renewal,
     "Renewal check-in. Customer is reviewing alternatives before committing "
     "to a new term.",
     ["Customer evaluating another payment provider at renewal",
      "Wants a shorter contract term",
      "Asked for a summary of value delivered this year"]),
    ("risk", "account",
     "Project check-in. Integration work on the customer's new checkout is "
     "behind schedule.",
     ["Implementation delayed by customer's engineering backlog",
      "Go-live pushed by roughly six weeks",
      "Customer still committed to the project"]),
    ("risk", "account",
     "Service review. Customer raised frustration about support response "
     "times.",
     ["Customer dissatisfied with support response times",
      "Two unresolved tickets mentioned by name",
      "Asked for a dedicated technical contact"]),
    ("opportunity", "account",
     "Strategy call about international growth plans.",
     ["Planning launch in a new market next year",
      "Wants local payment methods at launch",
      "Asked for a high-level timeline"]),
    ("opportunity", new_or_upsell,
     "Product discussion on additional payment methods.",
     ["Interest in adding wallets and Pay by Bank",
      "Expects higher conversion on mobile",
      "Requested pricing for additional methods"]),
    ("opportunity", evaluating_new_or_upsell,
     "Follow-up after demo. Strong engagement from the buying team.",
     ["Positive buying intent from the economic buyer",
      "Requested a formal proposal",
      "Wants to align on dates this quarter"]),
    ("opportunity", "account",
     "Expansion discussion with the customer's COO.",
     ["Discussing rollout to additional business units",
      "Volumes expected to grow next year",
      "Asked for a joint business plan"]),
    ("opportunity", early_new_or_upsell,
     "Request for proposal kickoff.",
     ["Customer issued a request for proposal",
      "Evaluation criteria shared",
      "Shortlist decision in about four weeks"]),
    ("opportunity", renewal,
     "Renewal planning call. Customer wants to extend and grow the "
     "partnership.",
     ["Customer intends to renew",
      "Interested in a multi-year term",
      "Exploring additional markets as part of the renewal"]),
    ("neutral", "account",
     "Routine check-in on account health.",
     ["No major issues raised",
      "Customer satisfied with current setup",
      "Next review scheduled for next quarter"]),
    ("neutral", "account",
     "Quarterly business review.",
     ["Reviewed volumes and authorization rates",
      "No commercial asks this quarter",
      "Customer team reorganising, new contacts to follow"]),
]
RISK_POINTS = [t[3][0] for t in TEMPLATES if t[0] == "risk"]
OPPORTUNITY_POINTS = [t[3][0] for t in TEMPLATES if t[0] == "opportunity"]

# Brief wording. Each template has several phrasings that name the account,
# a plausible customer contact and (for opportunity calls) the deal. Wording
# is picked with a separate random generator, so it never changes which
# template, date or opportunity a call gets.
brief_rng = random.Random(SEED + 1)
BRIEF_VARIANTS: dict[str, tuple[list[str], list[str]]] = {
    TEMPLATES[0][2]: (
        ["{account_poss} {role} said they are benchmarking our fees against "
         "another payment provider before signing {deal}.",
         "Pricing review on {deal}. {account} is comparing our offer with a "
         "competing provider's quote.",
         "Call with {account_poss} {role}, who wants our pricing on {deal} "
         "checked against another provider before deciding."],
        ["Head of Payments", "CFO", "Payments Lead"]),
    TEMPLATES[1][2]: (
        ["{account_poss} finance team pushed back on transaction fees in the "
         "current proposal for {deal}.",
         "Commercial terms call with {account_poss} {role}, who asked for a "
         "revised offer on {deal}.",
         "The {role} at {account} raised pricing concerns on {deal} and wants "
         "a revised offer before moving forward."],
        ["CFO", "VP Finance", "Finance Director"]),
    TEMPLATES[2][2]: (
        ["Procurement call with {account}. Vendor onboarding hasn't started, "
         "which is slowing down {deal}.",
         "{account_poss} {role} flagged an outstanding security questionnaire "
         "that is holding up {deal}.",
         "Check-in with {account} procurement: vendor setup and the security "
         "review are still open for {deal}."],
        ["Head of Procurement", "Procurement Manager", "Vendor Management Lead"]),
    TEMPLATES[3][2]: (
        ["Renewal check-in with {account}. The {role} said they are reviewing "
         "alternatives before committing to a new term.",
         "{account} is looking at other providers ahead of {deal} and wants a "
         "shorter contract.",
         "Call with {account_poss} {role} about {deal}. They asked for a recap of "
         "value delivered this year while they review options."],
        ["Head of Payments", "CFO", "COO"]),
    TEMPLATES[4][2]: (
        ["Project check-in with {account}. Their new checkout integration is "
         "behind schedule.",
         "{account_poss} {role} said an engineering backlog has pushed their "
         "checkout go-live back by about six weeks.",
         "Integration status call with {account}. Go-live is slipping, but the "
         "team is still committed."],
        ["CTO", "Engineering Manager", "Head of Ecommerce"]),
    TEMPLATES[5][2]: (
        ["Service review with {account}. The {role} raised frustration about "
         "support response times.",
         "{account} escalated slow support responses; two tickets are still "
         "unresolved.",
         "Call with {account_poss} {role} about support quality. They asked for a "
         "dedicated technical contact."],
        ["Head of Operations", "Payments Operations Lead", "CTO"]),
    TEMPLATES[6][2]: (
        ["Strategy call with {account_poss} {role} about launching in a new "
         "market next year.",
         "{account} shared international growth plans and wants local payment "
         "methods ready at launch.",
         "Planning session with {account}: a new-market launch is under "
         "discussion for next year."],
        ["COO", "Head of International", "VP Strategy"]),
    TEMPLATES[7][2]: (
        ["Product discussion with {account} on adding wallets and Pay by Bank "
         "alongside {deal}.",
         "{account_poss} {role} asked for pricing on additional payment methods "
         "as part of {deal}.",
         "Call with {account} about their payment method mix for {deal}; they "
         "expect wallets to lift mobile conversion."],
        ["Head of Ecommerce", "Payments Product Manager", "Digital Director"]),
    TEMPLATES[8][2]: (
        ["Follow-up after the demo for {deal}. {account_poss} buying team was "
         "highly engaged.",
         "{account_poss} {role} asked for a formal proposal on {deal} after the "
         "demo.",
         "Post-demo call with {account}: strong engagement, and they want to "
         "agree dates for {deal} this quarter."],
        ["CFO", "Head of Payments", "VP Ecommerce"]),
    TEMPLATES[9][2]: (
        ["Expansion discussion with {account_poss} {role} about rolling out to "
         "more business units.",
         "{account} expects volumes to grow next year and asked for a joint "
         "business plan.",
         "Call with {account_poss} {role} on extending the partnership to "
         "additional business units."],
        ["COO", "Managing Director", "VP Operations"]),
    TEMPLATES[10][2]: (
        ["{account} kicked off a request for proposal for {deal}.",
         "RFP kickoff with {account_poss} {role}; evaluation criteria shared for "
         "{deal}.",
         "{account} issued an RFP covering {deal}, with a shortlist decision "
         "in about four weeks."],
        ["Head of Procurement", "Head of Payments", "CFO"]),
    TEMPLATES[11][2]: (
        ["Renewal planning call with {account}. They intend to renew and want "
         "to grow the partnership.",
         "{account_poss} {role} confirmed plans to renew and asked about a "
         "multi-year term for {deal}.",
         "Positive renewal conversation with {account}: a multi-year term and "
         "new markets are on the table."],
        ["CFO", "Head of Payments", "COO"]),
    TEMPLATES[12][2]: (
        ["Routine account health check-in with {account}.",
         "Check-in with {account_poss} {role}; no major issues raised.",
         "Regular touchpoint with {account}. The customer is happy with the "
         "current setup."],
        ["Head of Payments", "Payments Operations Lead", "Head of Ecommerce"]),
    TEMPLATES[13][2]: (
        ["Quarterly business review with {account}.",
         "QBR with {account_poss} {role}: volumes and authorization rates "
         "reviewed, no commercial asks.",
         "{account} quarterly review. Their team is reorganising and new "
         "contacts will follow."],
        ["Head of Payments", "CFO", "VP Finance"]),
}
assert len(BRIEF_VARIANTS) == len(TEMPLATES)

KEEP_CAPITAL = ("Pay", "Tap")


def deal_phrase(opp: dict) -> str:
    """'Cobalt - Upsell - Pay by Bank' -> 'the Pay by Bank upsell'."""
    parts = opp["Name"].split(" - ")
    if opp["Type"] == "Renewal":
        return f"the {parts[-1]} renewal"
    descriptor = parts[-1]
    if not descriptor.startswith(KEEP_CAPITAL):
        descriptor = descriptor[0].lower() + descriptor[1:]
    noun = "upsell" if opp["Type"] == "Upsell" else "project"
    return f"the {descriptor} {noun}"


def render_brief(template_brief: str, account: str, opp: dict | None) -> str:
    variants, roles = BRIEF_VARIANTS[template_brief]
    text = brief_rng.choice(variants)
    possessive = account + ("'" if account.endswith("s") else "'s")
    return text.format(account=account, account_poss=possessive,
                       role=brief_rng.choice(roles),
                       deal=deal_phrase(opp) if opp else "")

# 18 of the 25 other accounts get calls; 7 have no Gong history.
with_calls = rng.sample(OTHER_NAMES, 18)
call_counts = {n: 2 for n in with_calls}
for n in rng.sample(with_calls, 5):
    call_counts[n] = 1                               # 13*2 + 5*1 = 31

for account in with_calls:
    open_opps = [o for o in opportunities
                 if o["AccountId"] == acct[account] and o["IsClosed"] == "false"]
    linked_opp = rng.choice(open_opps) if open_opps else None
    used_templates: set[str] = set()  # no repeated call type per account
    for i in range(call_counts[account]):
        r = rng.random()
        if r < 0.55:
            when = days_ago(rng.randint(1, 30))      # recent
        elif r < 0.80:
            when = days_ago(rng.randint(31, 90))
        else:
            when = days_ago(rng.randint(91, 200))    # stale

        # ~65% of calls are about an opportunity; a second call on the same
        # account reuses the same opp (multiple calls per opp).
        about_opp = linked_opp is not None and rng.random() < 0.65
        if about_opp:
            fitting = [t for t in TEMPLATES
                       if t[1] != "account" and t[1](linked_opp)
                       and t[2] not in used_templates]
            about_opp = bool(fitting)
        if not about_opp:
            fitting = [t for t in TEMPLATES
                       if t[1] == "account" and t[2] not in used_templates]
        kind, _, brief, points = rng.choice(fitting)
        used_templates.add(brief)

        opp_id = ""
        if about_opp:
            opp_created = date.fromisoformat(linked_opp["CreatedDate"][:10])
            if when < opp_created:
                when = min(opp_created + timedelta(days=rng.randint(3, 20)),
                           days_ago(1))
            opp_id = linked_opp["Id"]

        points = list(points)
        # Some calls carry contradictory signals: positive intent plus a risk,
        # or a risk call where the customer also flags growth.
        if kind != "neutral" and rng.random() < 0.2:
            points.append(rng.choice(OPPORTUNITY_POINTS if kind == "risk"
                                     else RISK_POINTS))
        brief = render_brief(brief, account, linked_opp if opp_id else None)
        add_call(account, when, brief, points, opp_id)

# Assign readable ids in chronological order and build fictional URLs.
gong_calls.sort(key=lambda c: c["started"])
for i, call in enumerate(gong_calls, start=1):
    call["id"] = f"gong_call_{i:04d}"
    call["url"] = f"https://gong.example.invalid/call?id={call['id']}"
    del call["_date"]

# --------------------------------------------------------------------------
# Write CSVs
# --------------------------------------------------------------------------
def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)


write_csv(OUT_DIR / "accounts.csv", ["Id", "Name"], accounts)
write_csv(OUT_DIR / "opportunities.csv", OPP_FIELDS, opportunities)
write_csv(OUT_DIR / "gong_calls.csv", GONG_FIELDS, gong_calls)

print(f"accounts.csv:      {len(accounts)} rows")
print(f"opportunities.csv: {len(opportunities)} rows")
print(f"gong_calls.csv:    {len(gong_calls)} rows")
