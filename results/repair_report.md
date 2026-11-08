# Entity repair: results (Phase C)

`shorgul/entities/repair.py` is a model-agnostic post-processor that rewrites spoken-form ₹ amounts
and dates into written form. It **only converts number words in an entity context**: followed by a
currency word, a month or तारीख/tarikh, preceded by ₹, or containing a scale word (sau/hazaar/lakh/crore).
That keeps "do teen log", "kar do" and "ek baar" untouched. It has 64 unit tests, 17 of them traps that must not be converted.

Measured on **all 4,175 cached transcripts**, with no new API calls. Hinglish, pooled over the 8
conditions; Δ = repaired − raw, paired bootstrap over clips, 95% CI, `*` = significant:

<!-- table:repair -->
| model (Hinglish) | entity acc. raw → repaired | Δ entity [95% CI] | Δ WER as scored | Δ WER currency-neutral |
|---|---|---|---|---|
| Prisma v2.5 (`en-IN`) | 0% → 100% | +100.0 [+100.0, +100.0] * | -36.6 [-41.4, -31.8] * | -29.5 [-34.0, -25.1] * |
| Prisma v2.5 (`hi-IN`) | 94% → 100% | +6.0 [+0.0, +12.0] | -1.8 [-3.9, +0.0] | -1.8 [-3.9, +0.0] |
| Prisma v3.0 | 96% → 97% | +1.3 [+0.0, +4.0] | -7.7 [-8.9, -6.6] * | -0.4 [-1.3, +0.0] |
| Prisma v3.0 + context | 92% → 96% | +4.0 [+0.0, +12.0] | -7.9 [-9.4, -6.6] * | -0.6 [-1.8, +0.0] |
| Whisper-small | 18% → 25% | +7.8 [+2.4, +14.2] * | -3.3 [-5.6, -1.4] * | -3.3 [-5.6, -1.4] * |
<!-- /table:repair -->

> **In-sample caveat, now measured.** The table above is the dev set the rules were written on. On 25 held-out lines
> (42 entities, new speakers, committed before any audio existed, code frozen at `0aa0b95`), repair took Prisma v2.5
> `en-IN` from 0% to **94% [90, 98]** against 100% in-sample: a 6-point generalisation gap. Across 4,955 transcripts,
> including 60 real phone calls, there were **0 entity regressions**. See `results/validation.md`.

## What this shows

1. **Do no harm: 0 regressions.** On all 4,175 transcripts, repair never lowered entity
   accuracy or raised WER on a single row. On FLEURS (Hindi/Bengali/Tamil read speech), it changed only 23 rows
   and WER stayed the same or improved slightly (Hindi −0.4 pts, not significant).
2. **It rescues output that has no number formatting.** Prisma v2.5 with `language_code=en-IN` returns romanized
   number words ("chaar hazaar paanch sau rupay"). Repair takes it from **0% to 100%** entity accuracy on these
   25 clips and cuts currency-neutral WER by about 29 pts. That's on par with Gnani's own formatting under the right config.
   Whisper-small also gains significantly, but its ceiling is set by misrecognition, not formatting.
3. **On Prisma output with formatting on (`format=transcribe`), Gnani's formatting already does the job.** Repair's
   gains there aren't significant on 25 clips. It fixes the split-digit dates that formatting leaves behind
   (`1 8 अगस्त → 18 अगस्त`, `2 0 जनवरी → 20 जनवरी`, `3 1 मई → 31 मई`, `3/1/May → 31 May`), which moves
   v2.5 (`hi-IN`) from 93% to 99%, but 25 clips can't prove that pooled.
4. **The as-scored WER gain on v3.0 (about −7.6 pts) is a convention effect, not a fix.** It comes from
   rewriting `4,500 रुपये` → `₹4,500` to match how our references are written. On currency-neutral WER,
   v3.0's change is about −0.4 pts, not significant. The headline numbers use currency-neutral WER.

## Where repair beats, ties with, or loses to built-in formatting

| situation | built-in formatting | repair | verdict |
|---|---|---|---|
| verbatim / romanized output (`en-IN`, Whisper) | can't convert romanized Hindi | converts | **repair wins** |
| split two-digit days (`1 8 अगस्त`, `3/1/May`) | leaves them broken | fixes | **repair wins** (small n) |
| amounts on Prisma `transcribe` output | already written form | no change needed | **tie** |
| information lost in recognition (`18 अगस्त` → `1 August`) | wrong | can't recover | **neither**, a recognition error |
| garbled words (Whisper `पाज्सो` for पाँच सौ) | wrong | converts only what's legible | **neither** |

**Positioning:** repair is the fix for (1) verbatim output and other vendors' models, and (2) the date
formatting bugs that remain under noise. It's **not** a replacement for Prisma's
`format=transcribe`, which is already at parity on amounts.
