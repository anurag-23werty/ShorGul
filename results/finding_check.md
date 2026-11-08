# Finding check (Phase A)

**Verdict: (b), it's an evaluation-config artifact.** On the same audio, the two Prisma models are
statistically tied on Hinglish once both are configured the same way and scored on a
convention-neutral basis. The earlier headline "WER picks the wrong model" is **not supported**
and must not be used.

**Verified framing (use only this):**

> **Your eval config picks the winner, not the model.** On identical call-centre audio, a single
> request parameter (`language_code`) moved Prisma v2.5's entity accuracy from **0% to 94%**, and a
> single reference-writing convention (`₹4,500` vs `4,500 रुपये`) decided which model "wins" on
> WER. With default settings, WER alone can pick the wrong model.

## 1. What was actually sent (from `results/cache.sqlite`)

| data | model | variant | params |
|---|---|---|---|
| FLEURS hi/bn/ta | prisma-v2.5, prisma-v3.0 | raw, denoised | `language_code=<lang>-IN, format=verbatim` (identical for both) |
| Hinglish | prisma-v2.5 | raw, denoised | `language_code=en-IN, format=transcribe` |
| Hinglish | prisma-v3.0 | raw, denoised | `language_code=hi-IN,en-IN, format=transcribe` |
| Hinglish | prisma-v3.0 | context | as above + domain `topic` + 12 `keyterms` |
| Hinglish | **both** | **matched** (new) | `language_code=hi-IN, format=transcribe` (identical) |

- **Formats were never mismatched.** Both models got `transcribe` for entity runs and `verbatim` for WER runs.
- **Language code was mismatched on Hinglish.** v2.5 got `en-IN`, following the original
  project spec ("v2.5 accepts one code; use en-IN for Hinglish"), and v3.0 got `hi-IN,en-IN`.
- **The original "flip" compared different datasets.** v2.5's WER win was on FLEURS, and v3.0's
  entity win was on Hinglish. It was never a same-audio comparison.

## 2. Matched re-run (350 calls: 25 Hinglish clips × 7 conditions × 2 models)

Corpus-level numbers, averaged over all 7 conditions unless stated otherwise:

| prisma-v2.5 config | WER | CER | entity accuracy |
|---|---|---|---|
| `en-IN` (original) | 62.1% clean → 65.4% market_0 | 45.8% clean | **0%** |
| `hi-IN` (matched) | 32.1% clean → 34.8% market_0 | 15.3% clean | **94% clean, 92% market_0** |

With `en-IN`, v2.5 writes romanized Hindi ("chaar hazaar paanch sau rupay"), and its English number
formatting can't convert that. With `hi-IN`, the same model writes "₹4,500".

### Same config, same audio: v3.0 − v2.5 (paired bootstrap over clips, 1,000 resamples, 95% CI)

These are the official values from `results/comparisons.csv` (Phase B scorer), pooled over all 7 conditions.

| metric | difference | 95% CI | significant? |
|---|---|---|---|
| WER, as scored | +5.9 pts | [+2.6, +9.2] | yes, v2.5 "wins" |
| CER, as scored | +10.6 pts | [+8.7, +12.3] | yes, v2.5 "wins" |
| **WER, currency convention neutralized** | **−1.4 pts** | **[−4.8, +2.0]** | **no, tie** |
| entity accuracy | +2.6 pts | [+0.0, +7.1] | no, tie |

**Why the as-scored WER gap disappears:** our references write amounts as `₹4,500`. v2.5 (`hi-IN`)
writes `₹4,500` too. v3.0 writes `4,500 रुपये`, which is just as correct, but "रुपये" counts as an inserted
word. Remove the currency word from both sides and v3.0 is 30.8% against v2.5's 32.2%, a difference
inside the noise. So the as-scored ranking reflects **how the reference was written, not
recognition quality.**

## 3. A shared failure, and a target for the entity-repair layer (Phase C)

Both models drop two-digit days in the *same* clips, under every condition:

| clip | reference | prisma-v2.5 (hi-IN) | prisma-v3.0 |
|---|---|---|---|
| hg_008 | 18 अगस्त | `1 8 अगस्त` | `1 August` |
| hg_021 | 31 मई | `3 1 मई` | `3/1/May` |

The digits are heard but formatted wrongly. That's exactly what a post-processor can repair.

## 4. What still stands from the earlier results

- **FLEURS (verbatim, matched config):** v2.5 has lower WER than v3.0 in all three languages, with
  the gap widening at market_0. Phase B confirmed it with paired tests: significant pooled over conditions in all three languages, and a tie on clean Bengali.
- **Both Prisma models are flat through the phone channel** and break only at 0 dB babble.
- **Whisper-small, denoising and wrong-script findings** are unaffected by this check.

## 5. What must change in the copy

- Drop "only v3.0 is usable for call-centre entities" and "v2.5: 0% entities" as model claims.
  The 0% is a config result, and it now *illustrates* the headline.
- Every model-vs-model claim needs a paired-bootstrap CI (Phase B).
- Report Hinglish WER both as-scored and convention-neutral.
