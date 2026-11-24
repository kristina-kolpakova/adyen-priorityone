# AI Tool Log

A running record of how AI coding tools were used on PriorityOne: what they were used for, how they were steered, how their output was checked, and where they failed or were corrected. The case study asks for specific examples, so each entry records one concrete moment.

> Unverified details are identified explicitly rather than guessed. Entries describe the state of the project at the time recorded.
>
> Account names: the 25 generated accounts were later shortened by dropping the industry descriptor (e.g. "Saltmarsh Games" became "Saltmarsh"). Entries below use the current names.

---

## Summary

| # | Date | Tool | Used for | What happened |
|---|------|------|----------|---------------|
| 1 | 2026-11-15 | ChatGPT | Choosing the frontend | Rejected the PyScript-in-browser suggestion |
| 2 | 2026-11-15 | ChatGPT | Choosing the frontend | Built in Streamlit, then dropped it for custom HTML/CSS |
| 3 | 2026-11-15 | Claude Code | Mock data model | Claude invented Salesforce fields; real schemas fixed the model |
| 4 | 2026-11-15 | Claude Code | Mock data generation | Data passed every structural check but still needed realism fixes |
| 5 | 2026-11-15 | Claude Code | Data integration | Cut interpretation fields Claude added; kept integration to joining data |
| 6 | 2026-11-15 | Claude Code | Data integration | Naming audit fixed field names that claimed more than the data supports |
| 7 | 2026-11-15 | Claude Code | Code quality | Readability pass: no lambdas, descriptive names, stage comments |
| 8 | 2026-11-15 | Claude Code | Test tooling | Considered Allure reporting, then dropped it to keep tooling light |
| 9 | 2026-11-19 | Claude Code | Scoring design | Design too complex to defend; asked for a plain-English walkthrough |
| 10 | 2026-11-19 | Claude Code | Data integration | pandas refactor kept the old architecture (345 → 343 lines) |
| 11 | 2026-11-19 | Claude Code | Data integration | Wrote a 500-line pipeline despite "build incrementally"; stopped |
| 12 | 2026-11-19 | Claude Code | Data integration | Rebuilt from my snippet, one step at a time (42 lines) |
| 13 | 2026-11-19 | Claude Code | Testing | Old tests deleted instead of replaced; 6 new tests written |
| 14 | 2026-11-20 | Claude Code, ChatGPT | Scoring dates | Rejected a fixed reference date; scoring uses today |
| 15 | 2026-11-20 | ChatGPT, Claude Code | Account scoring | Switched from ranking deals to ranking accounts |
| 16 | 2026-11-20 | ChatGPT, Claude Code | Account scoring | Kept overdue deals in the score instead of excluding them |
| 17 | 2026-11-20 | ChatGPT | Account scoring | Quarter-based weights for additional deals, verified on five accounts |
| 18 | 2026-11-20 | ChatGPT | Code quality | Kept the pandas scoring explicit and commented |
| 19 | 2026-11-20 | ChatGPT | Ranking review | Challenged Kestrel ranking above Krakatoa instead of accepting it |
| 20 | 2026-11-20 | Claude Code | Account scoring | Separated renewals from upsell/new; caught duplicated scoring logic |
| 21 | 2026-11-20 | Claude Code | Naming | Renamed scores and "segments" to match Salesforce terms |
| 22 | 2026-11-20 | Claude Code | Testing | Simplified the test suite; 8 tests passing |
| 23 | 2026-11-20 | Claude Code | UI | Hooked the dashboard up to exported scores; hid fake metrics |
| 24 | 2026-11-20 | Claude Code | Account scoring | Caught totals that didn't add up; total is now the higher type score |
| 25 | 2026-11-20 | Claude Code | UI | Built the detail panel; recovered discarded data; fixed alignment at the layout level |
| 26 | 2026-11-21 | Claude Code | Account scoring | Ranked accounts by their best deal, ties by amount; reversed entry 15 |
| 27 | 2026-11-21 | Claude Code | Account scoring | Dropped renewal weighting; problem flags break ties instead |
| 28 | 2026-11-21 | Claude Code | Data | Shifted mock dates forward; fixed the reference date at 25 Nov; reversed entry 14 |
| 29 | 2026-11-22 | Claude Code | Account scoring | Added Gong issues: display, then tie-break, then +2/+1 points kept below a Salesforce step |
| 30 | 2026-11-22 | Claude Code | Next actions | One next action per open deal from cited evidence; drafts reviewed and edited before saving |
| 31 | 2026-11-22 | Claude Code | Account scoring | Gong points moved onto every deal so the deal and account scores match |
| 32 | 2026-11-22 | Claude Code | Account scoring | Gong bonus by recency only (20 → 5 at 30 days → 0 at 90); every red flag counts equally |
| 33 | 2026-11-22 | Claude Code | UI | Traceable red pills, top-deal border, source colours, header and drawer tweaks; undid what didn't work |
| 34 | 2026-11-22 | Claude Code | Data | Sync date now comes from the data (23 Nov); reverses entry 28's fixed 25 Nov |
| 35 | 2026-11-22 | Claude Code | Feedback loop | Drag to reorder, then a review item for the model owner instead of a JSON download |
| 36 | 2026-11-23 | Claude Code | Data health | Simulated Gong outage; rejected a demo clock and "hours ago" as too complex |
| 37 | 2026-11-23 | Claude Code | AM workload | Log to Salesforce and a weekly digest that always matches the priority list |
| 38 | 2026-11-23 | Claude Code | Slack | Added Slack as a renewal-only signal; Unanswered request comes from thread timing |
| 39 | 2026-11-23 | Claude Code | Next actions | Updated six actions from Slack after matching opportunity IDs; active voice throughout |
| 40 | 2026-11-23 | Claude Code | Ranking | Priority cutoff moved from 90 to 100; Top accounts shows only priority accounts |

---

## 1. Rejected PyScript as the architecture

- **Tool:** ChatGPT
- **Used for:** Proposing how to host a Python-based prototype for free.
- **What it suggested:** GitHub Pages + PyScript/WebAssembly: one `index.html`, with Python running in the visitor's browser via Pyodide.
- **Correction:** Didn't adopt it. Loading a Python runtime in the browser adds page weight and complexity for a prototype whose scoring only needs to run when the data changes. Python moved to a build step (`scoring.py` → JSON), and the browser only renders.
- **Trade-off accepted:** The hosted site can't recalculate scores live. That's stated openly in the README.

## 2. Dropped Streamlit after building with it

- **Tool:** ChatGPT
- **Used for:** Scaffolding the first app (`app.py`), chosen because Kristina knows Python well and could explain every line.
- **How it was checked:** Ran it locally and confirmed the environment worked.
- **Correction:** After seeing it, decided the framework's look and branding didn't fit an internal SaaS tool and gave too little design control. Switched to a custom HTML/CSS frontend (Linear/Attio-style) on GitHub Pages, keeping Python for data and scoring.
- **Lesson:** Seeing the output in front of me changed the decision faster than discussing it would have.

## 3. Claude invented Salesforce fields

- **Tool:** Claude Code
- **Used for:** Designing the mock data model.
- **What went wrong:** Before the real schemas arrived, Claude's data model included Salesforce fields that don't exist in our schema (segment, annual value, renewal date, last AM activity), all flattened into one accounts CSV.
- **How it was steered:** I paused the build until the actual Salesforce object schemas were available. When they arrived (Account: `Id`, `Name`; Opportunity: 11 fields), a ChatGPT review flagged the invented fields and the single flat file.
- **Fix:** Separate `accounts.csv` and `opportunities.csv`, joined on `AccountId`. No unsupported Salesforce fields: renewal timing, upsells and open pipeline are derived from existing fields (e.g. `Type = Renewal` plus `CloseDate`), and anything else is labelled as synthetic data from another source.
- **Lesson:** Invented fields and APIs are a known AI failure mode. Real schemas first, then the data model.

## 4. Mock data passed validation but wasn't yet realistic

- **Tool:** Claude Code
- **Used for:** Phase 1: generating `accounts.csv` (30), `opportunities.csv` (100) and `gong_calls.csv` (44) with a seeded script, `data/generate_mock_data.py`.
- **How it was steered:** A written phase spec with exact record counts, fields, featured-account scenarios, and a hard stop after the datasets (no scoring, no frontend, no commits). Before generating, Claude raised four ambiguities, and I answered them: drop the old account names, use the standard Closed/Omitted forecast categories, keep the generator in the repo, and use 4 AMs.
- **How the output was checked:** A temporary validation script with 37 structural checks (counts, unique IDs, Salesforce ID checksums, account/opportunity/Gong links, `IsClosed`/`StageName` consistency, date order, parseable `key_points`) and 8 scenario-coverage checks (e.g. at least one renewal within 30 days, one overdue open opp). Both sets ran from the first run, but Claude's first report said "37 checks", counting only the structural ones; the total is 45. Running the generator twice gave byte-identical files.
- **What went wrong:** The first version **passed every check**, but Claude then read the generated Gong calls next to the opportunities they were linked to and found problems no check covered:
  - "Request for proposal kickoff" calls were linked to renewals, including one already in Negotiation (Saltmarsh).
  - "Integration work is behind schedule" calls were linked to deals still in Discovery (Pinecrest, Quayside), before anything had been implemented.
  - Support-frustration and routine check-in calls were tied to specific deals when they're really account-level.
  - Two still-open renewals were labelled FY26 (Fernhill, Marlowe).
  - After the first fix, one account (Bramblewood) had two identical RFP-kickoff calls on the same deal.
- **Fixes (Claude):** Each call type now says where it fits: account-level only, or only on opportunities of a matching type and stage (e.g. procurement blockers only on Proposal/Negotiation deals). An account can't repeat a call type. Renewal labels were tied to close dates.
- **Fixes after user review with ChatGPT:** The review pushed back on two things:
  - **Fiscal year:** Claude's label fix had introduced a fictional July–June fiscal year (FY27 = Jul 2026–Jun 2027). That's an invented convention the data didn't need. Renewals are now named by close month (e.g. "Krakatoa - Renewal - Nov 2026"). Where an account has both an open and a won renewal, the won one now closed exactly a year earlier, which moved 5 won renewals (by 1 day for Krakatoa and Mosaic, by up to 3 months for others).
  - **Repetitive briefs:** Generated Gong briefs repeated across accounts (the most-used brief appeared 5 times; Claude had flagged this as a known limitation). Each call type now has three phrasings that name the account, a fictional contact role and the deal. All 44 briefs are now distinct. Wording uses a separate random generator, so no call's date, account or opportunity link changed.
- **Verification after the changes:** All checks pass again. A field-by-field diff against the previous output showed only the intended changes: opportunity names for the 30 renewals, dates on the 5 moved won renewals, 31 generated briefs, and one reworded Mosaic key point (from "FY27 renewal" to "upcoming renewal"). Regeneration is still byte-identical.
- **Final independent review:** I verified byte-for-byte regeneration myself and found one inconsistency that Claude's review and checks had missed: Aster's Brazil call said "launching in Q2 2027" and also "a March go-live" (March is Q1). The go-live is now April, and that one key point is the only change. Claude then scanned every opportunity-linked Gong call against the opp's created, close and last-activity dates. It found no real contradictions: no call before its opp was created, and no call on a closed deal after it closed. Several calls come after the opp's `LastActivityDate` (including Krakatoa's renewal), and a Saltmarsh deal in Negotiation has calls but no logged activity. Those were left as they are, because calls that never reach the CRM are realistic and useful for spotting stale records.
- **Lesson:** Structural validation proves the data is well-formed, not that it makes business sense. Reading actual rows in context caught the problems the checks missed. And one AI fix (the fiscal year) added a new invented assumption that a review had to catch.

## 5. Integration started interpreting data; cut back to joining it

> Later replaced: this implementation was superseded by the 42-line pandas version (entry 12).

- **Tool:** Claude Code
- **Used for:** Phase 2a: `integration.py`, which loads and validates the three CSVs and builds one record per account, with source values and derived fields kept apart.
- **How it was steered:** A written phase spec. Salesforce `LastActivityDate` and Gong calls stay separate signals, and Gong never overwrites Salesforce activity. Account-level calls are never attributed to an opportunity, and amounts must not be inflated by one-to-many joins. No scoring.
- **What went wrong:** Claude added a derived boolean saying whether an opportunity's latest Gong call came *after* its Salesforce activity, plus an account-level list of those opportunities. It treated **missing** Salesforce activity as "Gong is newer", so Saltmarsh's deal (Gong calls, no `LastActivityDate`) was counted as a confirmed CRM/Gong discrepancy, though it's really missing data.
- **Correction, in two steps:**
  1. Review (the reviewer is not established in the available record) asked for a strict comparison: True or False only when both dates exist, None otherwise. Missing Salesforce activity was to be a separate data-quality condition, with a regression test for Saltmarsh.
  2. On reflection, both fields were removed entirely. The underlying dates were already kept, so the comparison belongs in scoring (Phase 2b), not integration. Claude also suggested adding a "missing Salesforce activity" field; that wasn't taken up, for the same reason.
- **How it was checked:** The comparison tests were replaced with tests that the underlying dates are kept as they are. One recalculates every opportunity's latest Gong call straight from the raw CSV. Another confirms Saltmarsh's missing date sits alongside its Gong calls with nothing inferred. A third asserts that an opportunity has only the two agreed derived fields, so interpretation can't creep back in.
- **Lesson:** The AI kept adding "helpful" interpretation to a layer meant only to join data. Keeping each phase to one job made both the code and the tests simpler.

## 6. Naming audit: field names claimed more than the data supports

> Later replaced: this implementation was superseded by the 42-line pandas version (entry 12).

- **Tool:** Claude Code
- **What was wrong:** Several derived names suggested data we don't have:
  - The account-level `salesforce_last_activity_date` read like complete Salesforce account activity, but it's only the latest opportunity `LastActivityDate` (the schema has no account-level activity).
  - `owner_id` read like `Account.OwnerId`, but it's taken from `Opportunity.OwnerId`.
  - `open_pipeline_amount` includes open renewals, which many Salesforce setups don't count as pipeline.
- **How it was steered:** I asked for an audit with explicit rules: keep source CSV names exactly, `snake_case` for derived fields, and names that state their source and scope. I specified the activity and Gong-call renames myself, and Claude was asked to *propose* any others before applying them. It proposed four (owner, the comparison fields, the amount total). I accepted them, with a behaviour correction to the comparison (entry 5).
- **Result:** `latest_opportunity_salesforce_activity_date`, `opportunity_owner_id(s)`, `open_opportunity_amount_total`, and four clearly scoped Gong fields: `latest_opportunity_gong_call` (one opportunity), `latest_opportunity_linked_gong_call` (any of the account's opportunities), `latest_account_level_gong_call` (no opportunity link) and `latest_gong_call_any_scope`. All return `{id, date}` or None.
- **How it was checked:** Tests were updated to the new names, and new ones were added for the any-scope field and for accounts with no opportunities (temporary test data).
- **Lesson:** A field name is a claim about the data. If it overstates the evidence, scoring and UI copy built on it will overstate it too.

## 7. Readability pass: lambdas, cryptic names and comments

> Later replaced: this implementation was superseded by the 42-line pandas version (entry 12).

- **Tool:** Claude Code
- **What I pushed back on:** Lambdas and single-letter names (`r`, `o`, `c`, `e`, `d`) in both the tests and `integration.py`, and dense nested comprehensions in `build_account_records()`.
- **Where Claude needed correction:** On its first pass, Claude swapped each `key=lambda c: c["started"]` for a one-line `_call_start()` helper. That removed the lambda without making anything clearer. I called it out, and `_latest_call()` now compares timestamps in a plain loop. The account totals are now built in one explicit loop over the opportunities instead of four nested comprehensions.
- **Comment convention agreed:** comment each processing stage and any non-obvious business rule (e.g. why amounts can't be inflated, why account-level calls stay separate), not individual statements. Simple loops whose purpose is obvious stay uncommented. Applied across `integration.py` and the tests.
- **How it was checked:** Before the rewrite, Claude saved the full integration output for all 30 records plus the CLI output. After each pass the output was byte-identical, all 23 tests passed, and file hashes confirmed the Phase 1 files and the approved tests were untouched.
- **Lesson:** "Correct" wasn't the bar; I wanted code another engineer could maintain comfortably. Proving the output hadn't changed made a large readability rewrite safe.

## 8. Considered Allure reporting, then dropped it

- **Tool:** Claude Code
- **What happened:** I asked whether the tests could use Allure annotations. A review I'd run suggested a lightweight convention (`@allure.feature`, `story`, `title`, and `step` only where useful). Claude planned to follow it but didn't install anything without approval: it needed a new package (`allure-pytest`), and viewing the HTML report needs a separate Allure command-line tool (Java-based, or Node for Allure 3) that isn't set up on this machine.
- **Decision:** Skipped. PriorityOne is primarily a GTM engineering case study, and plain pytest coverage is enough. No reporting dependencies were added.
- **Lesson:** Not every good tool belongs in a prototype. Asking before adding a dependency kept the setup light and the decision mine.

---

## 9. Scoring design too complex to defend

- **Tool:** Claude Code
- **Used for:** Designing the Phase 2b scoring model.
- **What went wrong:** Claude proposed per-item scores with two caps (45/50), a second-best-item bonus, an account-context weight of ×0.75 plus a freshness bonus, small "renewal due" and "late stage" nudges, three indicators and a "mixed" classification. Each piece was defensible on its own, but together they couldn't be explained in an interview.
- **How it was steered:** I said I didn't understand what we'd actually be building and asked for a plain-English walkthrough: code structure, data flow, rules, insights, frontend, and which parts are essential.
- **Fix:** Claude's own essential-vs-optional breakdown showed much of the design was tuning. For example, the bonus moved Krakatoa by only about 4 points, and the caps only affected Krakatoa. The design wasn't implemented as proposed.
- **Lesson:** If I can't explain why a component exists, it shouldn't be built.

## 10. pandas refactor kept the old architecture

- **Tool:** Claude Code
- **Used for:** Simplifying `integration.py` with pandas.
- **How it was steered:** I gave a foundation snippet (`read_csv`, rename, merge) and asked for a refactor that keeps the existing output and behaviour.
- **What went wrong:** Claude followed the brief literally: 345 → 343 lines, with the same nested records and per-row type conversion. It reported the result as "partly simpler" but didn't recommend dropping the structure that made it complex.
- **How it was checked:** The output was byte-identical and the 23 tests passed. Correct, but no simpler.
- **Fix:** The refactor was reverted.
- **Lesson:** Translating code into a new library isn't the same as simplifying it.

## 11. 500-line pipeline despite "build incrementally"

- **Tool:** Claude Code
- **Used for:** Rebuilding the pipeline on my pandas snippet.
- **How it was steered:** I asked explicitly for a *"genuinely simpler, pandas-first implementation, not another translation of the old architecture"*, built incrementally, with no unnecessary abstractions.
- **What went wrong:** Claude wrote a ~500-line `pipeline.py` in one pass, bringing back reasons, CRM updates, indicators, shortlists and the full JSON. When one function got long, it split it into four more instead of cutting scope. It crashed with a `TypeError`, and I stopped it: *"why are you adding new crazy amounts of code!!"*
- **Fix:** It was deleted. We restarted from step 1 only.
- **Lesson:** "Incremental" has to mean one reviewed step at a time, not the whole design written at once and then reorganised.

## 12. Rebuilt from my snippet, one step at a time

- **Tool:** Claude Code
- **How it was steered:** We did step 1 only: load, filter to open opportunities, join, `qcut` value tiers, then stop for review. Then I asked: *"isn't the code in pipeline.py what should be in integration.py?"*
- **What went wrong:** ChatGPT's version of step 1 used a right join, which added an empty row for Thistle (no open opportunities). That crashed `fillna(0)` on the categorical tier column. Claude patched it with `.astype(float)`.
- **Fix:** The 42-line step 1 replaced the 345-line `integration.py`, and `pipeline.py` was deleted. I switched back to my original left join, so Thistle is excluded and the crash case no longer exists. `fillna(0)` stays as a safety net for missing amounts.
- **How it was checked:** Claude ran each version against the real CSVs before adopting it: 30 accounts with the right join, 29 with the left, and 70 open opportunities either way.
- **Lesson:** The smallest working code was the right foundation. Most of what we'd built before wasn't needed for it.

## 13. Tests deleted instead of replaced

- **Tool:** Claude Code
- **What went wrong:** When `integration.py` was replaced, Claude recommended deleting all 23 old tests. I approved it. ChatGPT pointed out they should have been replaced with a few tests of the new behaviour.
- **Fix:** Claude wrote 5 tests, then rewrote them in the original suite's style on request: fixtures, section headings, comments explaining where each expected value comes from.
- **How it was checked:** When I switched to the left join, 2 tests failed straight away (29 accounts, Thistle missing). They were updated deliberately and are now 6 passing tests: accounts kept, account names attached, open opportunities only, no duplication, value tiers 18/17/17/18, Thistle excluded.
- **Lesson:** Replacing code doesn't mean dropping its safety net. Small tests against the raw CSVs paid off immediately.

## 14. Dynamic reference date

- **Tool:** Claude Code, ChatGPT, Python/pandas
- **Used for:** Calculating whether opportunities close in the current quarter.
- **How it was steered:** Claude proposed keeping a fixed 15 Nov 2026 reference date (the mock data's snapshot date) for reproducible results and tests. I rejected it and required scoring to use the actual date when the script runs.
- **How the output was checked:** Reviewed the pandas implementation and confirmed it uses `pd.Timestamp.today().normalize()`.
- **What went wrong / what I corrected:** Anchoring calculations to the mock dataset's date would make the tool stale. Trade-off accepted: results change over time and the quarter rolls over on 1 Jan, so tests can't hard-code date-dependent scores.
- **Lesson:** Mock data can be static; business logic shouldn't be.

## 15. Switching from opportunity to account prioritization

- **Tool:** ChatGPT, Claude Code, Python/pandas
- **Used for:** Designing account-level scoring from individual Salesforce opportunities.
- **How it was steered:** Clarified that the goal was to rank accounts, not individual deals. Chose 100% contribution for the highest-scoring opportunity, 50% for additional current-quarter deals, 25% for next-quarter deals, and 10% for later-quarter deals.
- **How the output was checked:** Inspected opportunity-level contributions and calculated account totals in Spyder.
- **What went wrong / what I corrected:** Taking the maximum opportunity score ignored additional deals. Simply summing every score would overreward accounts with many distant opportunities.
- **Lesson:** Aggregation should reflect the business decision, not just the easiest pandas operation.

## 16. Preserving overdue opportunities

- **Tool:** ChatGPT, Claude Code
- **Used for:** Deciding how open opportunities with past close dates should affect priority.
- **How it was steered:** Rejected Claude's suggestion to exclude overdue deals, and its alternative of giving every overdue deal the 20 quarter points. Kept overdue current-quarter opportunities eligible for the 50% additional-deal contribution and added an `IsOverdue` flag.
- **How the output was checked:** Verified Krakatoa's overdue €320K opportunity contributed 35 points, bringing its account total to 125.
- **What went wrong / what I corrected:** Excluding overdue deals would hide opportunities that may urgently need follow-up. Adding arbitrary urgency points wasn't justified either.
- **Fixed later:** At first only overdue deals in the *current* quarter contributed. Deals that slipped from an earlier quarter (Marlowe's Sep renewal, Wayfarer's tokenization upsell) contributed 0, because `QuartersAway` was negative and no weight rule matched. The 50% rule now uses `QuartersAway <= 0`, so all overdue deals count (Marlowe 125 → 150, Wayfarer 60 → 65).
- **Lesson:** Preserve useful business signals without inventing scoring weights.

## 17. Implementing quarter-based discounts

- **Tool:** ChatGPT, Python/pandas, Spyder
- **Used for:** Discounting additional opportunities based on how far away their close dates are.
- **How it was steered:** Requested a simple, explainable calculation using `QuartersAway`. Kept the strongest opportunity at 100%, with additional deals weighted by quarter.
- **How the output was checked:** Manually verified Krakatoa (125), Marlowe (125), Aster (79), Oakmoor (73), and Willowbank (105). All five matched the script's results, and Claude confirmed them again against the repo's `integration.py` on 20 Nov.
- **What went wrong / what I corrected:** The initial implementation ignored future-quarter opportunities entirely. The revised logic preserves their contribution at reduced weights.
- **Lesson:** Implement one rule at a time and verify it against known examples before trusting the full ranking.

## 18. Keeping the pandas implementation explainable

- **Tool:** ChatGPT, Python/pandas, Spyder
- **Used for:** Implementing, commenting, and testing account-scoring logic.
- **How it was steered:** Requested explicit pandas operations, consistent section headers, and comments explaining the business rules. Avoided unnecessary functions and abstractions.
- **How the output was checked:** Reran the script after reorganizing the code and verified four existing account scores with assertions in Spyder (not yet in the repo's test suite).
- **What went wrong / what I corrected:** AI suggestions sometimes introduced complexity before the underlying business rules were settled.
- **Lesson:** Code I can explain and debug is more valuable than clever code I can't defend.

## 19. Challenging the first account ranking

- **Tool:** ChatGPT, Python/pandas, Spyder
- **Used for:** Evaluating whether the first 29-account ranking answered the original business question.
- **How it was steered:** Challenged Kestrel ranking first (131) over Krakatoa (125). Requested an opportunity-level breakdown instead of accepting the scores.
- **How the output was checked:** Compared total pipeline (€2.255M vs. €1.77M), largest deals (€1.23M vs. €1.45M), opportunity contributions, and overdue status.
- **What went wrong / what I corrected:** The model favored Kestrel's combined pipeline but didn't account for Krakatoa's overdue follow-up urgency. Quartile scoring also obscured differences between large deals.
- **Lesson:** A correct calculation isn't necessarily a useful recommendation. Don't manipulate weights to force a preferred outcome; introduce evidence-based urgency and Gong context to distinguish pipeline strength from immediate actionability.

## 20. Separating renewals from upsell/new

- **Tool:** Claude Code, Python/pandas
- **Used for:** Splitting the original account score into separate renewal and upsell/new scores.
- **How it was steered:** After comparing Marlowe, Krakatoa and Kestrel, I realised renewals and upsell/new are fundamentally different problems. Renewals are existing customers we're trying to keep, while upsell/new revenue still has to be won. I asked Claude to split the scores by opportunity type without changing the existing weights.
- **What I corrected:** Claude initially duplicated the account-scoring logic in `scoring.py` to avoid changing `integration.py`. I caught that and had it moved into one reusable `score_accounts()` function. We compared all 29 account scores before and after the refactor and confirmed nothing changed.
- **What it showed:** Marlowe's lead comes mostly from upsell/new opportunities. Six renewals still tie at 90, and a renewal 73 days overdue scores only 50. The split made the rankings easier to understand, but also exposed limitations in the current scoring rules.
- **Lesson:** The decision to split the scores came from understanding the business, not adjusting weights to get a particular result.

## 21. Cleaning up naming

- **Tool:** Claude Code
- **How it was steered:** Claude originally called the scores `RetentionScore` and `GrowthScore`, which I changed to `RenewalScore` and `UpsellNewScore`. I also questioned why it was calling them "segments." In GTM, that usually refers to customer segments like enterprise or mid-market, not opportunity types. We renamed `score_segments()` and `segment_scores` to `score_types()` and `type_scores` to match the Salesforce `Type` field.
- **How it was checked:** Verified the new column names and scores in Spyder. The values were unchanged, and the tests passed.
- **Lesson:** Naming should reflect what the code actually does, ideally using the same terminology as the source data.

## 22. Simplifying the test suite

- **Tool:** Claude Code, Spyder, pytest
- **What I did:** I wasn't happy with how complicated `tests/test_integration.py` had become, so I rewrote it with plain functions, no fixtures, and simpler assertions. I also removed the overdue regression test after Claude's proposed replacement felt unnecessarily complicated for what I was trying to check.
- **Where Claude helped:** It pointed out that one of my console checks was recalculating type scores using the same function it was supposed to validate, which wasn't a particularly useful independent test. It also identified which coverage I lost during the rewrite. I reviewed those gaps and decided to add back the two type-scoring tests.
- **How it was checked:** All 8 pytest tests passed. I also checked the scoring output manually in Spyder.
- **Lesson:** I wanted a test suite I could actually read, understand and maintain. That meant keeping the most useful checks and accepting some gaps in coverage for now.

## 23. Hooking up the UI to real scores

- **Tool:** Claude Code, Python/pandas, JavaScript
- **How it was steered:** Export first, then render, one reviewed step at a time. I chose to show only the top 5 and to hide the "Revenue risks" and "Opportunities" cards, because hardcoded numbers next to real scores would look like real results.
- **What I corrected:** A review of Claude's JavaScript caught that dates could shift a day in time zones behind UTC, and that a failed load would show a silently empty list. Both were fixed before it went in.
- **Lesson:** Once part of the page is real, anything still hardcoded has to go or be labelled.

## 24. The totals didn't add up

- **Tool:** Claude Code
- **What I noticed:** Marlowe showed Renewal 50 and Upsell/New 125, but a total of 150. The green number came from a separate blended score, not from the two numbers beside it.
- **How it was steered:** Claude recommended turning the type scores into a breakdown of the blended total. I chose to make the total the higher of the two type scores, so the UI shows exactly what the logic does, even though that creates a six-way tie at 90. I documented the tie in the README as a temporary gap to fix.
- **Lesson:** If the numbers on screen don't reconcile, users stop trusting all of them. A faithful UI with a known gap beats a polished one that hides it.

## 25. Building the detail panel

- **Tool:** Claude Code, Python/pandas, JavaScript/CSS
- **How it was steered:** I designed the panel mockup. Claude flagged that "70 pts" on a deal that doesn't count would read as counted, and that "Next steps" checkboxes had no data behind them, so they were dropped. We built it in three reviewed steps.
- **What Claude found:** The per-opportunity contributions the panel needed were being discarded as `_` in `score_types()`, the same spot where I'd originally kept named variables because "we'll need details later". They're now exported, and for all 29 accounts they add up exactly to the total.
- **What I corrected:** Claude's expand chevron broke the alignment of the points pills, because it became a third flexbox item in a `space-between` row. I asked for an architectural fix rather than a nudge, and each row now uses fixed grid columns.
- **Lesson:** Ask why a layout breaks, not just where.

## 26. Ranking accounts by their best deal

- **Tool:** Claude Code, Python/pandas
- **What I noticed:** Marlowe scored 125, higher than any single deal can score (90), because three mid-sized Upsell/New deals were added together. That didn't match how I'd prioritise an account.
- **How it was steered:** I asked whether the score should simply be the highest-scoring open opportunity. Claude showed that this alone would keep a six-way tie at 90 and suggested breaking ties by the top deal's amount, which I adopted. The Renewal and Upsell/New scores stay as context only.
- **What changed:** This reverses my earlier decision (entry 15) to reward additional deals. No full ties remain: the six 90s are now ordered by deal size (Willowbank €2.06M down to Kestrel €595K), and Marlowe drops out of the top 5. The README's limitations were updated to match.
- **Lesson:** When a number surprises me, the rule behind it is probably wrong. A simple rule I can explain beats a clever aggregation I can't defend.

## 27. Prioritising trouble instead of weighting renewals

- **Tool:** Claude Code, Python/pandas
- **What I proposed:** Weighting renewals 1.2–1.5× and ranking accounts by their most problematic opportunity.
- **What the data showed:** Claude ran both multipliers. Renewals already led 9 of the top 10 because they're the largest deals, and a 1.2× weight pushed out the only growth deal (Aster). The multiplier would also have been an opinion-based weight with no outcome to test it against. The "most problematic" idea held up: six accounts tied at 90, and nothing showed which of them was in trouble.
- **How it was steered:** I had Claude add three Salesforce problem flags as data only first (overdue, no recent activity before close, stale Commit, with 30-day thresholds), then show them on the page. Of the six 90s, only Krakatoa's €1.45M renewal was flagged: a Commit closing in 6 days with no activity for 44 days. Of three ranking options, I chose to use flags as a tie-break rather than adding points, and made the Renewal and Upsell/New scores each type's best deal. The weighted aggregation that no longer fed anything was removed.
- **How it was checked:** The JSON was verified for every account (scores, top deal, order). Tests were updated for the new rules, and the flags are explained in the detail panel and the README.
- **Lesson:** Test a weighting idea against the data before adopting it. A flag that explains why an account matters beats a multiplier I can't justify.

## 28. Fixing the reference date, reversing entry 14

- **Tool:** Claude Code, Python/pandas
- **What I noticed:** Six days after the mock data was generated, too many close dates had passed, with few deals coming up. I had Claude move every date in the mock data forward 10 days (close, created, activity and Gong calls together, so activity gaps stayed consistent), with renewal names following their new close month.
- **What went wrong:** Krakatoa dropped to #2. Claude explained why: the shift put Krakatoa and Lanternfly in different timing bands, so Krakatoa's earlier lead had only come from winning a tie. I moved Lanternfly's renewal one day later (3 Dec) so the two tie again. Localhost still looked the same, because the scores were calculated from today's date and the change only took effect on 25 Nov, the day of my interview.
- **How it was steered:** I decided scores shouldn't change on the day of the demo. Claude laid out the options, and I chose a fixed reference date of 25 Nov 2026, the date the shifted data now represents. This reverses entry 14 for the mock data. With live Salesforce data the reference date would be today again, as noted in the README.
- **Then nothing scored 100:** no large Negotiation deal closed within 7 days of 25 Nov. I chose new close dates for four renewals: Krakatoa 1 Dec (6 days out, as in the original data), Willowbank 28 Nov, Mosaic 7 Dec and Lanternfly 3 Dec. Later, to demo the Early-stage Commit flag (entry 30), I changed Silverbirch's renewal forecast from Pipeline to Commit. These are the only rows changed by hand for the demo.
- **How it was checked:** Reran the scoring, the 10 tests pass, and the ranking is the same whichever day the script runs: Krakatoa 100 (flagged) and Willowbank 100, then Lanternfly and Mosaic on 95.
- **Lesson:** "Use today's date" is right for live data and wrong for a static snapshot. A demo should give the same answer every time it runs.

## 29. Adding Gong: from display-only to a capped tie-break in points

- **Tool:** Claude Code, Python/pandas, JavaScript/CSS
- **What I built:** I wrote `gong.py`, a keyword classifier that sorts Gong call key points into issue categories. Claude ran it against the calls and found it missed the strongest signals ("renewal discussions on hold", "wants migration fixed before discussing renewal terms", ledgers not reconciling). I added phrases for them and merged 13 categories into 9.
- **How it was steered:** Each step was reviewed on localhost. Gong first went in as display-only pills in my own colours. I then chose to show only the top deal's issues on each row, like the Salesforce tags, with a second shade for calls not linked to any deal. Next I made Gong break ties, then decided the ranking should use the same 90-day issues the dashboard shows, and finally turned the tie-break into points: +2 for an issue on the top deal, +1 for one from a call not linked to a deal, with no cap.
- **What Claude found:** Every Salesforce score is a multiple of 5, so a Gong bonus under 5 can only reorder accounts with the same Salesforce score. +2/+1 keeps Gong from overriding Salesforce while showing its effect in the score. Claude also flagged that the list row then showed "Renewal 95" next to a score of 97, so rows now show "+2 Gong".
- **How it was checked:** Three new tests: the final score equals the Salesforce score plus 0–2 Gong points, a top-deal issue gives +2, and Salesforce scores still run from highest to lowest after sorting. All 13 tests pass. The README explains the rule and its limits: keyword matching isn't tested against outcomes, and Salesforce flags still add no points while Gong does.
- **Lesson:** A new signal should earn influence step by step: shown first, then a tie-break, then points kept small enough that it can't override the main score.

## 30. A next action for every deal, drafted from cited evidence

- **Tool:** Claude Code, Python/pandas, JavaScript/CSS
- **What I designed:** Python picks the top deal and gathers the evidence; AI drafts one action and one reason from it; the drawer shows the action with a "View evidence" toggle. I dropped mock Clay data from the first version because it didn't change what an AM would do, and skipped a rules-engine fallback because drafts are generated offline and can be reviewed before publishing.
- **What Claude built:** An evidence list per deal with stable IDs (Gong call ID plus a hash of the key point, so a saved draft can't point at a different fact after new calls arrive), with deal-linked and account-wide evidence labelled separately. Non-red-flag key points are kept as "Context", so drafts see good news too. "Last activity" was relabelled "Last activity logged in Salesforce" after Krakatoa's 38-day gap sat next to a call from 9 days earlier.
- **How it was steered:** Instead of running an API script, I had Claude draft the actions in chat in batches, and I edited them before anything was saved. My edits kept the evidence's certainty ("may push the signature" stays a question to confirm, not a slip), sent Krakatoa's action to procurement rather than the champion, and kept date changes conditional. Then I extended it to all 70 open deals: 38 reviewed drafts (top deals plus deals with signals), 23 Salesforce next steps word for word, and 9 stage-based suggestions where the field is blank, keyed by opportunity ID. A final pass trimmed reasons that repeated their action, keeping logging gaps only where they're the reason to check a deal is still active.
- **Also added:** an Early-stage Commit flag (Commit while in Discovery or Qualification). No mock deal triggered it, so I set Silverbirch's renewal to Commit to show it.
- **How it was checked:** Before saving, every cited ID was checked against that deal's evidence, and every open deal was checked to have exactly one action. Claude also checked the drawer for all 29 accounts: 70 action blocks, one per deal card.
- **Lesson:** A valid citation isn't the same as a faithful draft. The ID check catches made-up sources; only reading the drafts catches "may" turning into "will".

## 31. When the deal said 100 and the account said 102

- **Tool:** Claude Code
- **What I noticed:** Krakatoa's top deal showed 100 pts while the account showed 102. I asked for an audit.
- **What Claude found:** Every number was correct. Gong points were added once at account level, so the deal's own score never included them. Claude first suggested a "+2 Gong = 102" note on the badge, which I rejected: the deal score itself should include Gong.
- **How it was steered:** Gong points now apply to every deal (+2 for its own issue, +1 for an account call), and badges, type chips, the evidence score row and the score box all show the final score. Claude simulated the change first: no account score or top deal changed.
- **How it was checked:** A new test checks that each deal's final score is its Salesforce score plus its Gong points, and that each account's score is its best deal's final score. A browser audit of all 29 drawers confirmed that every badge, chip and score row adds up. 15 tests pass.
- **Lesson:** Numbers that are correct but don't visibly add up still read as wrong. A score should be the same number everywhere it appears.

## 32. Making Gong count by recency, not multipliers

- **Tool:** Claude Code, Python/pandas
- **What I decided:** +2/+1 was far too low to matter. A Gong issue raised 2 days ago should count a lot (about 20 points), one from a month ago much less (about 5), sliding in between.
- **What went wrong:** The first version, built from a spec I pasted in, stacked multipliers on top of recency: full weight for some flags, half for others, and half again for calls not linked to a deal. I couldn't follow it myself, so I asked why we needed multipliers at all. I wanted a simple calculation.
- **How it was steered:** Before changing the app again, I asked for a side-by-side ranking on the 25 Nov snapshot: the old +2/+1, a recency bonus for "serious" issues only, and a recency bonus for every red flag. Seeing it, I decided pricing pressure is serious, and then that every red flag should count equally: if something is classified as a red flag, its category is the account manager's call, not the score's. When Orchard Lane's procurement flags didn't add up, I asked whether one signal per deal made sense, and kept it: the bonus measures how fresh the trouble is, not how many problems a call mentioned.
- **The rule now:** each open deal gets 20 points for a red flag up to 2 days old, falling in a straight line to 5 at 30 days and 0 at 90; only its most recent red flag counts. Accounts rank by their best deal's Salesforce + Gong score, so a fresh issue can now lift a deal above a higher Salesforce score (Orchard Lane, 70 + 18, now ranks above Fernhill at 85).
- **Making it explainable:** I spotted the bonus shown twice in the evidence and designed the fix: it sits under the call that earned it. After Marlowe's account-wide call showed +9 while its score used +14, I set the rule that an account-wide call is shown only when it counts toward the account's score.
- **How it was checked:** Tests recompute every deal's bonus from its call age and pin the demo ranking (Krakatoa 116, Mosaic 113, Marlowe 94, Orchard Lane 88). 16 tests pass.
- **Lesson:** Compare scoring options on the real data before choosing one, and prefer the rule I can say in one sentence. If I can't explain a formula, an account manager won't trust it.

## 33. Design calls in the drawer and header

- **Tool:** Claude Code, JavaScript/CSS
- **What I decided:**
  - **Every red pill has to be traceable.** Krakatoa showed "No recent activity" and "Stale Commit" with nothing behind them in View evidence. I rejected a separate "Why it's flagged" group; the fix was to cite the flags on the two deals that lacked them.
  - **The top deal should look like the top deal:** a mint border like the priority rows on the home page, and its pills in the header as well as the expanded view.
  - **Colours mean the source:** Salesforce evidence bubbles now match the red Salesforce pills, Gong stays blue, and I kept both the Deal and Account bubbles because scope matters.
  - **The header:** I asked for a 15–20% larger wordmark; Claude pointed out that my suggested pixel sizes would barely change it, so we used 27px. I also loosened the heading spacing and italicised "*prioritized.*".
  - **The drawer stays put:** I tried lining its edge up with the "p" in the heading, then decided it shouldn't move with the text and fixed it at 490px.
  - **Room for Clay:** I tried moving the type-score chips up beside the score tile, then undid it to keep the space under the account name for enrichment data.
  - **Small clean-ups:** I asked why a commit added 9,894 lines, which led to dropping duplicate evidence from `scores.json` (about 2,000 lines); I fixed Mosaic's grammar but chose not to rewrite every action.
- **Lesson:** Check each visual change on the real page and be willing to undo it. Several of these ideas looked right until I saw them, and the undos were as useful as the changes.

## 34. Letting the data set the date, reversing entry 28

- **Tool:** Claude Code, Python/pandas
- **What I noticed:** Calls in the drawer said "9 days before 25 Nov", which only made sense if you knew 25 Nov was my interview date. I didn't want the data to shift, and I didn't want a hidden date either.
- **How it was steered:** Of the options Claude laid out, I chose to label the date as a sync: the pipeline now takes the latest Salesforce activity or Gong call as the snapshot date, and the page says when the data was synced. I then moved the sync to Monday 23 Nov, kept Krakatoa's renewal 6 days out (now 29 Nov), and moved the two activities that would have been in the future.
- **How it was checked:** A test pins the sync date and the demo ranking. Claude also checked every day count in the drafted actions against its cited evidence.
- **Lesson:** A demo date shouldn't be a secret. If the data decides it and the page names it, nobody has to explain it.

## 35. A feedback loop the AM would actually use

- **Tool:** Claude Code, JavaScript/CSS
- **What Claude proposed:** A long form for flagging a wrong priority.
- **How it was steered:** I wanted drag to reorder, with optional reasons. Then I questioned the "Download feedback" link: an AM wouldn't know what to do with a JSON file. Each move with a note now becomes a review item for whoever owns the model, with the original rank, the new rank, the note, and the score breakdown behind it. I replaced the reason chips with an optional note in the same popup, rejected copy that promised "your reasons tune next week's ranking", and had the note follow the account into the weekly digest.
- **How it was checked:** Browser tests for drag, note, Undo, and Reset (which keeps the logged moves), and the review item text was checked against the scores.
- **Lesson:** Feedback has to cost the AM nothing and reach someone who can act on it.

## 36. Data health without a fake clock

- **Tool:** Claude Code, JavaScript/CSS
- **What I built:** A Data health tab with Salesforce, Gong, and later Slack, a simulated Gong outage, the accounts using Gong points, Retry sync, a bell, and a refresh icon in the nav.
- **What went wrong:** To show "19 hours ago", Claude added a live clock, then a fixed demo time, then a fixture file. Each step added more code and created new mismatches, including the header and the bell showing different sync times.
- **How it was steered:** I sent it back to simple: every date comes from the sync date, only the cards show (simulated) sync times, and every time is labelled with its source. The README states the limitation: the view is simulated, and its dates stay put until the pipeline runs on new data.
- **Lesson:** I'm making it simpler, not more complex. A timestamp that can't be true is worse than no timestamp.

## 37. Less work for the AM

- **Tool:** Claude Code, JavaScript/CSS
- **What I decided:** One click on **Log to Salesforce** turns the action into the task and the reason into the note, and confirms "Task and note saved (demo)". The weekly digest went from a separate page to a tab to a card on Top accounts that opens a drawer. I made it follow the AM's own order, show the AM's note, and list exactly the priority accounts, not a fixed top 3. I decided against a Send button, because the digest arrives on its own.
- **How it was checked:** Browser tests confirmed that the digest, the Priority accounts card, and the list always match, including after reordering.
- **Lesson:** Reducing work means adding nothing the AM has to do. Every extra step needs a reason the AM can see.

## 38. Adding Slack as a second conversation signal

- **Tool:** Claude Code, Python/pandas, JavaScript/CSS
- **How it was steered:** I set the shape: Slack's own export columns, no opportunity ID (you talk to people, not deals), renewals only (a shared channel exists once someone is a customer), the same red-flag analysis as Gong, and a separate 20-point bonus. I picked four Slack-only categories, including Unanswered request, which comes from thread timing rather than keywords. I also set the colours.
- **What I caught:** The mock data had Gong and Slack each covering exactly 10 accounts, which looked staged, so I had Slack reach more. I had the sender names made plainer and given consistent roles. Krakatoa stays #1 by design (137), and a test pins it.
- **Also added:** **Open thread** shows the whole conversation in the app, with the flagged message outlined and "No reply from Adyen in 4 business days" on unanswered threads.
- **Lesson:** A new source should match how that tool actually works, not be forced into the old one's shape.

## 39. Updating the actions Slack changed

- **Tool:** Claude Code
- **What I noticed:** The drafted actions predated Slack, so some now ignored what customers had said.
- **How it was steered:** Before editing, I had each Slack message matched to its opportunity ID. Tidewater's message was on a renewal that Slack had just made its top deal, so its old action no longer applied. Six actions were revised, each citing the message that prompted it. Krakatoa's and Mosaic's wording stayed, because Slack backed them up. I then asked for active voice across every action and reason (48 edits) and standardized activity gaps as "Salesforce shows no logged activity in the past N days".
- **Lesson:** New evidence can make saved advice wrong. Check what it touches before rewriting anything.

## 40. Raising the priority cutoff to 100

- **Tool:** Claude Code
- **What I noticed:** With Gong and Slack bonuses, scores run up to 140, so 90 had become a low bar.
- **How it was steered:** I moved the cutoff to 100, the most a deal can score from Salesforce alone, and set it in one place. Top accounts now lists only the priority accounts (7), and the digest and the card share the same count. I also removed the unused Signals and Activity tabs and renamed the rest to Top accounts, All accounts, and Data health.
- **Lesson:** A threshold should mean something I can say in one sentence.

---

## Template for new entries

```
## N. <one-line title>

- **Tool:**
- **Used for:**
- **How it was steered:** (prompt, constraints, context given)
- **How the output was checked:** (ran it, read the diff, tests, hand calculation)
- **What went wrong / what I corrected:**
- **Lesson:**
```
