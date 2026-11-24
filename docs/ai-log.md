# AI tool log

I used Claude Code to build the pipeline and UI, and ChatGPT to review parts of the work. I used mock data throughout.

## 1. Stopping a 500-line rewrite

- **Tool:** Claude Code
- **Used for:** Simplifying `integration.py` with pandas.
- **What went wrong / what I corrected:** Claude's first refactor shrank `integration.py` from 345 lines to 343 and kept the old structure. Its next attempt brought back features I’d cut, grew to about 500 lines, and crashed. I stopped it and rebuilt step one from my own snippet, in 42 lines.
- **How it was steered:** I gave Claude a pandas prototype I’d written and asked it to build one step at a time.
- **How the output was checked:** Claude ran the code against the mock CSVs. My original join kept all 70 open deals across 29 accounts and left out Thistle, which had no open deals.
- **Lesson:** Give Claude a stopping point. “Step one only” gave me something I could run and review.

## 2. Cutting a feedback form down to drag and drop

- **Tool:** Claude Code
- **Used for:** Collecting feedback when an AM disagrees with the ranking.
- **What went wrong / what I corrected:** Claude suggested a long form. I cut it to drag and drop with an optional note. I also removed the line promising that notes would tune next week’s ranking.
- **How it was steered:** The move already tells me where the AM thinks the account belongs. I asked Claude to offer an optional note after the drop and save it with the old rank, new rank, and original score breakdown.
- **How the output was checked:** We tested drag and drop, notes, Undo, and Reset in the browser. We also checked the saved feedback against the scores.
- **Lesson:** If an AM can fix the ranking in one drag, stop there.

## Testing AI-drafted next actions

Claude drafted 39 of the 70 next actions. I reviewed each one before saving.

- **How I'd test it.** Each pilot week, I'd check whether AMs followed the suggested next action or did something else, and talk to them about why. I'd also track how much they reorder their list, using the notes from ranking feedback.
- **When it's wrong.** If AMs ignore or rewrite the drafted actions, I'd change how Claude drafts them. If they reorder more than half of the top 7, I'd rework the scoring. If weekly use drops after week 2, I'd shadow the AMs who stopped to find out why.
