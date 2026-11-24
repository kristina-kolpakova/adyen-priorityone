# AI tool log

I used Claude Code to build the pipeline and UI, and ChatGPT as a reviewer. All data is mock; no company data went into either tool.

These are the moments where I corrected the tools or pushed back.

## 1. Stopping a 500-line rewrite

- **What happened.** I asked for a simpler pandas pipeline, built one step at a time. Claude wrote about 500 lines in one pass, brought back features I'd cut, and crashed when it ran.
- **What I did.** I stopped it and rebuilt from my own 42-line snippet, reviewing each step before the next.
- **Why it mattered.** "Incremental" has to mean one reviewed step at a time. The smallest working code became the foundation for everything after it.

## 2. A fix that invented something new

- **What happened.** Claude's mock data passed all 45 of its structural checks but still didn't make business sense, like RFP-kickoff calls on renewals. Claude's fix then introduced a July–June fiscal year the data never needed.
- **What I did.** A ChatGPT review caught the fiscal year, and renewals are now named by close month. Reading the rows myself, I also found a call that said "launching in Q2" and "a March go-live" together, which both tools had missed.
- **Why it mattered.** Checks prove data is well-formed, not that it makes sense. An AI fix can add a new assumption, so the fix needs checking too.

## 3. A feedback form cut down to drag and drop

- **What happened.** Claude proposed a long form for AMs to flag a wrong priority.
- **What I did.** I cut it to drag and drop with an optional note. I also rejected copy promising that notes would "tune next week's ranking".
- **Why it mattered.** The move already says where the account belongs, and a form is friction busy AMs skip. Each note becomes a review item with the original score breakdown, so the model owner can see which signal misled the ranking. Weights should change only after checking real outcomes, not because a note says so.

## Testing AI-drafted next actions

Claude drafted 39 of the 70 next actions. I reviewed each one before saving.

- **How I'd test it before trusting it.** In the pilot, AMs would follow the drafted actions instead of their usual Monday list. Every week I'd check how many actions they followed, how many were wrong or unhelpful, and how often they reordered accounts. If AMs skip the actions or keep reordering, the drafts aren't better than the old approach yet.
- **What happens when it's wrong.** Every action shows its evidence, so the AM can spot a bad one before acting on it, and nothing is sent until they click. When an AM skips an action or moves an account, their note becomes a review item for me, and I'd fix the rule or prompt behind it before the next week.
