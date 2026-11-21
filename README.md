## How accounts are ranked

> Show the most important opportunity at each account. When two accounts are equally important, prioritize the one showing signs of trouble.

1. **Opportunity score:** each open opportunity gets `PriorityScore = value + quarter + stage` (10–90).
2. **Account score:** an account's priority is its highest-scoring open opportunity. The **Renewal** and **Upsell/New** scores shown next to it are the best opportunity of each type, so the account score is the higher of the two.
3. **Ranking:** accounts are sorted by score. Among equal scores, an account whose top opportunity has a problem comes first, then the larger deal.

### Problem flags

An opportunity is flagged as a problem if any of these apply:

- **Overdue:** the close date has passed, but the deal is still open.
- **No recent activity before close:** it closes within 30 days, and Salesforce shows no activity in the last 30 days (or none logged at all).
- **Stale Commit:** it's forecast as Commit, and Salesforce shows no activity in the last 30 days (or none logged at all).

Flags only break ties between accounts with equal scores; they never add points.

## Known limitations

- **Other opportunities don't affect the ranking.** Only each account's best opportunity counts, so an account with several live deals scores the same as one with only its best deal. Because `PriorityScore` can only take a few values (10–90), many accounts share a score, and the problem flags and amount do much of the ordering (today six accounts score 90).
- **A flagged deal never outranks a higher-scoring healthy one.** Flags only break ties: an overdue 80-point renewal still ranks below a healthy 90. How much a problem should count is left until stronger signals (Gong) are available.
- **The problem flags rely on Salesforce data quality.** The 30-day thresholds are assumptions, not tested against outcomes. Missing `LastActivityDate` counts as "no recent activity", and activity that isn't logged in Salesforce (calls, email) isn't seen.
- **Scores depend on the date the script runs.** Scoring uses today's date (`pd.Timestamp.today()`), by design, so priorities stay current. The mock data, however, is a snapshot from mid-November 2026: as time passes, more deals show as overdue, and from 1 January the current quarter becomes Q1 2027, so quarter scores and the ranking shift. Score checks that expect fixed totals (e.g. Krakatoa = 90) will fail after the quarter changes. Automated scoring tests will need a controllable reference date.
