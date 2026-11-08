# ShorGul pilot protocol (one team, two weeks)

What it would take to show that ShorGul's grades predict production. This hasn't been run yet.

## What the team sends
- **200 consented production calls** from one use case (for example collections), with PII handled under their policy.
  Long calls are fine, since ShorGul chunks them at pauses.
- **Reference transcripts for 50 of them**, plus the amounts, dates and account numbers a human agent captured.
- **The exact ASR config they run in production:** model, `language_code`, `format`, and context hints.

## What ShorGul returns (day 1–3)
1. `shorgul audit` on all 200: a health check per call, its nearest benchmark condition, a stability grade and the
   breaking point. This needs no references.
2. On the 50 referenced calls: WER, currency-neutral WER, entity accuracy, and entity repair before/after, all with
   paired CIs.
3. A config check: the same 50 calls under their config and under the matched alternative (the `en-IN` vs `hi-IN`
   lesson). Cost is 100 calls per alternative.

## How we know it worked (day 4–14)
| question | measured how | pass if |
|---|---|---|
| Do grades predict errors? | Spearman ρ between per-call stability and their QA team's error flags | ρ > 0.4, CI excludes 0 |
| Does repair help on their calls? | Entity accuracy before/after, paired, on the 50 referenced calls | gain with CI above 0, 0 entity regressions |
| Was there a config issue? | Matched-config comparison | any significant entity difference is reported to the team |
| Would the gate have caught a regression? | `shorgul compare` on their last two model or config versions | the verdict agrees with what they saw in production |

## Known gaps to state up front
- **Dropouts:** the dropout detector doesn't work on real calls (it looks for silence, but real networks conceal lost
  packets), so dropouts aren't flagged.
- **Calibration:** the grade is calibrated on Prisma. Other vendors' models need their own calibration.
- **Repair scope:** repair covers ₹ amounts, dates and day numbers. Account numbers, phone numbers and names need
  extending before go-live.
