# Adyen PriorityOne

PriorityOne is a Monday briefing for account managers. It shows which accounts need attention this week, why they surfaced, and what to do next. The demo uses mock Salesforce, Gong, and Slack data for 29 accounts and 70 open opportunities.

[Open the live demo](https://kristina-kolpakova.github.io/adyen-priorityone/)

## Try the demo

1. Start with **Top accounts** to see accounts scoring 80 or higher. **All accounts** shows the full list.
2. Open an account to see its opportunities and the suggested next step for its highest-scoring deal.
3. Select **View evidence** to see the score breakdown and the Salesforce fields, Gong call notes, and Slack messages behind it. **Open call** and **Open thread** show the mock conversations in the app.
4. If an account belongs somewhere else, drag it to a new spot. You can add a note explaining why.

## Run locally

Open a terminal in the project folder and run:

```bash
python3 -m http.server 8000
```

Then open [localhost:8000](http://localhost:8000/).

To regenerate the score and evidence exports and run the tests, use a virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python integration.py
python -m pytest
```

## How scores work

I score deals first. An account ranks by its highest-scoring open opportunity, including Gong and Slack points. The **Renewal** and **Upsell/New** chips show the best score for each type.

Each open opportunity starts with up to 100 points from Salesforce.

| Component | Scoring rule |
| --- | --- |
| **Value** · up to 40 | Eight tiers based on deal amount, worth 5–40 points. |
| **Timing** · up to 30 | Closing in 0–7 days earns 30 points, 8–14 earns 25, 15–30 earns 20, 31–60 earns 10, 61–90 earns 5, and anything later earns 0. Deals overdue by 1–30 days earn 30. Deals overdue longer earn 10. |
| **Commit check** · up to 30 | A deal forecast as Commit earns 30 points in Discovery or Qualification, 15 in Proposal, and 0 in Negotiation. The earlier the stage, the more reason to check whether the forecast is realistic. Other forecasts earn 0. |

**Gong** adds up to 20 points for the most recent red flag on a call linked to the deal or account. A flag is worth 20 points through day 2. It then drops linearly to 5 on day 30 and to 0 on day 90. The bonus rounds to a whole point.

**Slack** can add another 20 points on the same curve. Shared customer channels reflect the existing relationship, so I use Slack to score renewals. Each renewal keeps its strongest Slack red flag. Slack uses the Gong categories plus **Service incident**, **Champion departure**, **Billing dispute**, and **Unanswered request**. An unanswered request is a customer question that’s still the last message in the thread after at least two business days.

If two deals tie, the deal with a Salesforce problem flag wins. If they’re still tied, the larger deal wins. These flags cover overdue deals, missing or stale activity near close, stale Commit forecasts, and Commit forecasts in Discovery or Qualification.

## Ranking feedback

After an AM moves an account, PriorityOne offers them an optional note to explain why. The demo saves every move in the browser. If the AM adds a note, it appears on the account row and can be edited there. The note also creates a review item with the old rank, the new rank, and the original score breakdown. A review item looks like this (simplified):

> **Krakatoa moved from #1 to #5**  
> AM note: Procurement confirmed the renewal is on track.  
> Original score: 107 = value 40 + timing 30 + Commit check 0 + Gong 17 + Slack 20.  
> Evidence: Competitor risk on a Gong call 7 days before sync and pricing pressure in Slack 1 day before sync.  
> Salesforce flags: No recent activity, Stale Commit.

**Download ranking feedback** in the footer exports all moves and their review items as JSON. In production, I’d send the review items to a queue tagged with the AM and the scoring version. If AMs keep moving accounts down because a concern from a Gong call was already resolved, I’d check those cases against won and lost deals before changing the weights.

## Data and assumptions

- **Snapshot.** `integration.py` reads the Salesforce, Gong, and Slack CSVs and writes the JSON the app uses. It scores deals as of the latest activity across open Salesforce opportunities, Gong calls, and Slack messages. The published snapshot is **23 November 2026**.
- **Account matching.** `data/slack_channels.csv` maps each shared customer channel to a Salesforce account. In production, I’d maintain that mapping or match channels by customer domain. The app loads mock Gong calls from `data/gong_calls.json` and mock Slack threads from `data/slack_threads.json`.
- **Red flags.** `gong.py` and `slack.py` use phrase matching. Only customer messages can raise a Slack flag. Salesforce activity flags reflect what’s recorded in the CRM, so they can appear alongside recent Slack activity. I’d test the score bands and weights against actual deal outcomes.
- **Clay enrichment.** I left Clay out of the prototype to keep the data simple. My assumption was that recent red flags in Gong and Slack would tell an AM more about which accounts need attention this week. I’d test whether adding Clay enrichment changes the ranking in ways AMs find useful.
- **Data health.** The sync history, Gong outage, and connector times are simulated in `index.html`. The snapshot date comes from `data/sync.json`. In production, each connector would record its own sync times.
- **Next actions.** Each of the 70 open deals has one next action, saved in `data/next_actions.json`. Claude drafted all 70 offline from each deal’s evidence, reusing the Salesforce Next step where it already fit, and I reviewed each one before saving. In production, the pipeline would call an LLM to redraft a deal’s next action when its evidence changes.


## AI tool log

[docs/ai-log.md](docs/ai-log.md) covers where I corrected the AI tools and how I would test the AI-drafted next actions.
