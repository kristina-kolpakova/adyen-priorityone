## How accounts are ranked

> Show the most important opportunity at each account. When two accounts are equally important, prioritize the one showing signs of trouble.

1. **Opportunity score:** each open opportunity gets a `PriorityScore` out of 100:
   - **Value (max 40):** eight equal-sized tiers by amount, 5 points per tier.
   - **Timing (max 30):** closes in 0–7 days 30 · 8–14 days 25 · 15–30 days 20 · 31–60 days 10 · 61–90 days 5 · later 0. Overdue by up to 30 days: 30 (it needs action now). Overdue by more than 30 days: 10 (more likely a stale record).
   - **Stage (max 30):** Negotiation 30 · Proposal 20 · Discovery 10 · Qualification 0.
2. **Account score:** an account's priority is its highest-scoring open opportunity. The **Renewal** and **Upsell/New** scores shown next to it are the best opportunity of each type, so the account score is the higher of the two.
3. **Ranking:** accounts are sorted by score. Among equal scores, an account whose top opportunity has a problem comes first, then the larger deal.

### Problem flags

An opportunity is flagged as a problem if any of these apply:

- **Overdue:** the close date has passed, but the deal is still open.
- **No recent activity before close:** it closes within 30 days, and Salesforce shows no activity in the last 30 days (or none logged at all).
- **Stale Commit:** it's forecast as Commit, and Salesforce shows no activity in the last 30 days (or none logged at all).
- **Long overdue:** the close date passed more than 30 days ago. The record may be stale and should be checked.

Flags only break ties between accounts with equal scores; they never add points.

## Known limitations

- **Other opportunities don't affect the ranking.** Only each account's best opportunity counts, so an account with several live deals scores the same as one with only its best deal. Because `PriorityScore` is built from bands, several deals can reach the same score, including the maximum of 100 (big, closing this week, in Negotiation). The score can't separate deals beyond that ceiling, so the problem flags and amount decide the order among them.
- **A flagged deal never outranks a higher-scoring healthy one.** Flags only break ties: an overdue 80-point renewal still ranks below a healthy 90. How much a problem should count is left until stronger signals (Gong) are available.
- **The problem flags rely on Salesforce data quality.** The 30-day thresholds (and the timing bands) are assumptions, not tested against outcomes. Missing `LastActivityDate` counts as "no recent activity", and activity that isn't logged in Salesforce (calls, email) isn't seen.
- **Scores use a fixed date, not today's.** The mock data is a snapshot dated 25 November 2026 (generated as of 15 November, then shifted forward 10 days), so `integration.py` scores as of that date and the ranking stays the same whenever it runs. With live Salesforce data the reference date would be today (`pd.Timestamp.today()`), and the ranking would shift day by day as close dates move into different timing bands. Automated scoring tests will need a controllable reference date.
