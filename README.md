# Adyen PriorityOne

PriorityOne is a Monday briefing for account managers. It ranks the accounts that need attention, shows the opportunity and evidence behind each score, and suggests a next action. The demo uses synthetic Salesforce and Gong data covering 29 accounts and 70 open opportunities. [Open the live demo](https://kristina-kolpakova.github.io/adyen-priorityone/)

## Run locally

From the repository root, serve the checked-in snapshot with Python 3.

```bash
python3 -m http.server 8000
```

Open [localhost:8000](http://localhost:8000).

To regenerate the score and evidence exports or run the tests, use a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python integration.py
python -m pytest
```

## How to use it

Start with the top 10 on **Overview**, or open **Accounts** to see all 29. Select an account to see its opportunities and the highest-scoring deal's next action. **View evidence** shows the Salesforce fields, Gong key points, and score breakdown. **Open call** opens an in-app preview of the mock Gong call.

Drag an account to change your order and optionally select a reason. Picking a reason saves the ranking feedback.

## Ranking feedback

When an AM disagrees with the ranking, they drag the account and pick a reason. They see **Ranking feedback saved**, and they never need to understand the scoring. Each reasoned move becomes a review item for the model's owner, with the account, the original and new rank, the reason, and the score breakdown behind the original rank:

```
Ranking feedback · Krakatoa
AM moved this account from #1 to #5.
Reason: Concern resolved
Why it ranked #1: score 117 = value 40 + timing 30 + stage 30 + Gong 17 (Competitor risk, call 7 days before sync).
Salesforce flags: No recent activity, Stale Commit
```

In the demo, review items are saved in the browser with the move. **Download ranking feedback** in the footer exports every move and its review item as JSON. In production, each item would go to a review queue the model's owner works through, tagged with the AM and the model version. Patterns across items, such as many "Concern resolved" moves on accounts driven by Gong points, would be checked against won and lost deals before any weight changes.

## How scores work

Each open opportunity gets a Salesforce base score out of 100.

| Component | Rule |
| --- | --- |
| Value, up to 40 | Eight amount-based tiers across open deals, worth 5 to 40 points. |
| Timing, up to 30 | 0–7 days until close earns 30, 8–14 earns 25, 15–30 earns 20, 31–60 earns 10, 61–90 earns 5, and later earns 0. Deals overdue by 1–30 days earn 30. Deals overdue longer earn 10. |
| Stage, up to 30 | Negotiation earns 30, Proposal 20, Discovery 10, and Qualification 0. |

The most recent applicable Gong red flag adds up to 20 points. It earns 20 through day 2, then falls linearly to 5 at day 30 and 0 at day 90. The bonus rounds to a whole point. A deal can use a call linked to it or to its account. Every red-flag category uses the same curve.

The account ranks by the highest **final opportunity score**, including Gong. The **Renewal** and **Upsell/New** chips show the best final score of each type. Ties go to a deal with a Salesforce problem flag, then to the larger deal. Problem flags cover overdue deals, missing or stale activity near close, stale Commit forecasts, and Commit forecasts in Discovery or Qualification.

## Data and assumptions

- `integration.py` reads the Salesforce and Gong CSVs and exports JSON for the static app. It scores as of the latest activity date among open Salesforce opportunities or the latest Gong call, whichever is later. The published snapshot is **23 November 2026**.
- Gong flags come from phrase matching in `gong.py`. The bands and weights are prototype assumptions to test against deal outcomes. A Salesforce activity gap means activity is missing from the CRM log.
- **Data health** is simulated. The sync history, the Gong outage, and the sync times on its cards are written in `index.html`. Only the sync date comes from `data/sync.json`. The app is a fixed snapshot, so every sync date stays **Mon 23 Nov** until `integration.py` runs on new data. In production, each connector would record its own sync times.
- Each open deal has a next action in `data/next_actions.json`. The demo uses 38 reviewed AI drafts, 23 Salesforce next steps, and 9 stage-based suggestions. Drafting and review happened offline.

See the decisions, corrections, and checks made while building the prototype. [AI tool log](docs/ai-log.md)
