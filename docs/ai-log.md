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
