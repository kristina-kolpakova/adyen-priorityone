## How accounts are ranked

> Show the most important opportunity at each account. When two accounts are equally important, prioritize the one showing signs of trouble.

1. **Opportunity score:** each open opportunity gets a `PriorityScore` out of 100:
   - **Value (max 40):** eight equal-sized tiers by amount, 5 points per tier.
   - **Timing (max 30):** closes in 0–7 days 30 · 8–14 days 25 · 15–30 days 20 · 31–60 days 10 · 61–90 days 5 · later 0. Overdue by up to 30 days: 30 (it needs action now). Overdue by more than 30 days: 10 (more likely a stale record).
   - **Stage (max 30):** Negotiation 30 · Proposal 20 · Discovery 10 · Qualification 0.
2. **Salesforce score:** an account's Salesforce score is its highest-scoring open opportunity. The **Renewal** and **Upsell/New** scores shown next to it are the best opportunity of each type, so the Salesforce score is the higher of the two.
3. **Gong points:** every open opportunity gets +2 if it had a Gong issue in the last 90 days, otherwise +1 if a recent call not linked to any deal raised one for the account (see [Gong issues](#gong-issues)). Its final score is `PriorityScore` + Gong points, so it can reach 102.
4. **Final score and ranking:** an account's score is its best opportunity's final score. Accounts are sorted by that score. Among equal scores, an account whose top opportunity has a Salesforce problem flag comes first, then the larger deal.

### Problem flags

An opportunity is flagged as a problem if any of these apply:

- **Overdue:** the close date has passed, but the deal is still open.
- **No recent activity before close:** it closes within 30 days, and Salesforce shows no activity in the last 30 days (or none logged at all).
- **Stale Commit:** it's forecast as Commit, and Salesforce shows no activity in the last 30 days (or none logged at all).
- **Long overdue:** the close date passed more than 30 days ago. The record may be stale and should be checked.
- **Early-stage Commit:** it's forecast as Commit while still in Discovery or Qualification. The AM should check what supports the forecast, or update Salesforce. (Proposal and Negotiation are left alone; none of the mock deals trigger this today.)

Salesforce flags only break ties between accounts with equal scores; they never add points.

### Gong issues

`gong.py` reads each Gong call's key points and matches them against a list of phrases (for example "evaluating another payment provider" or "renewal discussions on hold") to sort them into nine categories: Closing risk, Competitor risk, Pricing pressure, Implementation delay, Technical issue, Procurement / legal, Executive escalation, Stakeholder change and Missing next step.

- **Only calls from the last 90 days count.** Older issues may already be resolved.
- **Deal-linked issues** (lighter blue pills) belong to that opportunity. The list row shows the top opportunity's issues; the detail panel shows each opportunity's own.
- **Issues from calls not linked to a deal** (stronger blue pills) apply to the account as a whole.
- **Gong points stay below 5 on purpose.** Every Salesforce score is a multiple of 5, so +2 or +1 can only reorder accounts with the same Salesforce score. Gong never lifts an account above one that Salesforce rates higher.

## Known limitations

- **Other opportunities don't affect the ranking.** Only each account's best opportunity counts, so an account with several live deals scores the same as one with only its best deal. Because `PriorityScore` is built from bands, several deals can reach the same score, including the maximum of 100 (big, closing this week, in Negotiation). The score can't separate deals beyond that ceiling, so Gong points, the problem flags and amount decide the order among them.
- **A troubled deal never outranks a higher-scoring healthy one.** Salesforce flags only break ties and Gong adds at most 2 points: an overdue 80-point renewal with Gong issues still ranks below a healthy 90. How much trouble should count is left until it can be tested against deal outcomes.
- **Salesforce flags and Gong are weighted differently.** Gong issues add points that show in the score, while Salesforce flags only break remaining ties. Both reorder accounts only within the same Salesforce score.
- **Gong classification is keyword matching.** It only finds the phrasings in `red_flag_map`, so new wording is missed until a phrase is added, and each key point gets only the first category it matches. It hasn't been tested against which deals were actually lost.
- **The problem flags rely on Salesforce data quality.** The 30-day thresholds (and the timing bands) are assumptions, not tested against outcomes. Missing `LastActivityDate` counts as "no recent activity", and activity that isn't logged in Salesforce (calls, email) isn't seen.
- **Scores use a fixed date, not today's.** The mock data is a snapshot dated 25 November 2026 (generated as of 15 November, then shifted forward 10 days), so `integration.py` scores as of that date and the ranking stays the same whenever it runs. With live Salesforce data the reference date would be today (`pd.Timestamp.today()`), and the ranking would shift day by day as close dates move into different timing bands. Automated scoring tests will need a controllable reference date.
