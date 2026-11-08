# ShorGul Bench

**An open benchmark for how Indian-language speech recognition breaks on real phone calls.**

*Shor-gul* (शोर-गुल) means "din, racket". Most ASR leaderboards score clean, wideband
read speech. Indian voice traffic doesn't sound like that: it's 8 kHz G.711 telephony,
dropped packets, and a caller standing next to an auto-rickshaw or a sabzi mandi. ShorGul
Bench takes clean speech, puts it through a reproducible simulation of an Indian phone call, and
measures how **Gnani Prisma v2.5**, **Prisma v3.0** and **Whisper-small** hold up, both on
word accuracy and on the thing a call-centre actually needs: *did the ₹ amount and the date
survive?*

> Entry for Gnani AI's Great Indian AI Internship Challenge (2026).

## Pipeline

```
clean 16 kHz speech
   │  FLEURS hi / bn / ta (25 clips each)  +  25 Hinglish call-centre lines (Gnani Timbre TTS)
   ▼
[1] background noise at target SNR      ← caller side, acoustic (DEMAND traffic / market)
[2] phone channel                       ← 300–3400 Hz band-pass → 8 kHz → G.711 μ-law → 16 kHz
[3] packet loss                         ← 20 ms frames dropped at random
   ▼
optional fixes:  denoise (spectral gating)  |  Prisma v3.0 domain context (topic + keyterms)
   ▼
ASR:  Prisma v2.5  ·  Prisma v3.0  ·  Whisper-small (local)
   ▼
score: WER · CER · entity hit rate · runaway (hallucination) rate · latency
   ▼
results/results.parquet  →  summary.csv  →  charts  +  Streamlit dashboard
```

The order matters. Noise is mixed **before** the phone channel because that's where it is
physically: in the caller's room. So the band-pass removes traffic rumble below 300 Hz but
keeps market chatter, which sits in the speech band. That's exactly what happens on a real call.

### Conditions

| condition | noise | SNR (acoustic) | phone channel | packet loss |
|---|---|---|---|---|
| `clean` | – | – | – | – |
| `phone` | – | – | ✓ | – |
| `loss_5` | – | – | ✓ | 5 % |
| `traffic_10` | street traffic | 10 dB | ✓ | – |
| `traffic_5` | street traffic | 5 dB | ✓ | – |
| `market_10` | public square + crowd chatter | 10 dB | ✓ | – |
| `market_0` | public square + crowd chatter | 0 dB | ✓ | – |

Every clip × condition is **deterministic**: seed = `sha256(clip_id | condition)`.
(Python's `hash()` is salted per process, so it can't be used.)

### Metrics

- **WER / CER** after Unicode NFC, native-digit → ASCII, punctuation/danda/₹ removal, and
  lower-casing. Group numbers are **corpus-level** (errors ÷ reference words), not a mean of
  per-clip ratios.
- **Hinglish WER**: models legitimately write the same words in Devanagari *or* Latin. Both
  sides are romanized (ITRANS + schwa deletion) before scoring, so a choice of script isn't
  counted as an error. This is approximate: `लोन` → `lon` ≠ `loan`. That's why the headline
  Hinglish metric is the next one.
- **Entity hit rate** (Hinglish): the share of reference entities (₹ amounts, dates, day numbers)
  reproduced *in written form* (`₹4,500`, `5 March`/`5 मार्च`, `5th`). Spoken-form numbers
  ("चार हज़ार पाँच सौ") don't count: a CRM can't use them. Prisma is called with
  `format=transcribe` (ITN) for these clips. FLEURS clips use `format=verbatim`.
- **Runaway rate**: the share of hypotheses more than 2× longer than the reference, counted in words or characters.
  This catches Whisper's repetition loops under heavy noise.
- **Wrong-script rate**: the share of hypotheses whose letters are mostly outside the language's
  own script. For example, Whisper-small often writes Bengali speech in Devanagari: phonetically close,
  but useless downstream.

## Results

100 clips × 7 conditions × 3 models, plus denoised, context and matched-config variants:
**3,825 transcripts, 0 failed.** Every number below is generated from `results/summary.csv` and
`results/comparisons.csv` (`python -m shorgul.cli readme-tables`). Brackets are **95% bootstrap CIs
over clips** (1,000 resamples). Every "A beats B" claim is a **paired** bootstrap on the same clips.

![WER by condition](results/charts/wer_by_condition.png)

**Corpus WER, clean → `market_0` (0 dB crowd noise through a phone line):**

<!-- table:wer -->
| | Hindi | Bengali | Tamil | Hinglish* |
|---|---|---|---|---|
| Prisma v2.5 | 7.1% [4.5, 10.0] → 13.2% [9.1, 17.4] | 13.1% [9.2, 17.3] → 18.7% [11.4, 28.4] | 21.3% [16.1, 26.6] → 32.5% [25.4, 40.8] | 62.1% [56.1, 69.0] → 65.5% [59.4, 72.2] |
| Prisma v3.0 | 9.0% [5.8, 12.6] → 21.3% [15.0, 28.1] | 13.8% [9.9, 18.5] → 27.5% [19.4, 38.1] | 25.9% [20.2, 32.4] → 41.2% [32.7, 51.9] | 38.2% [34.3, 42.7] → 40.9% [35.9, 46.2] |
| Prisma v3.0 + context | – | – | – | 36.7% [31.7, 42.0] → 38.8% [33.4, 44.4] |
| Whisper-small | 79.3% [53.6, 109.2] → 97.5% [78.8, 123.2] | 108.2% [104.1, 112.8] → 123.2% [102.3, 151.6] | 73.5% [61.8, 90.2] → 110.8% [95.2, 132.0] | 61.5% [52.8, 70.2] → 104.6% [83.5, 132.3] |
<!-- /table:wer -->

\*Hinglish WER is computed after romanization, and v2.5 here is the `en-IN` config. Read Hinglish through the
entity table and the matched-config tests, not this row.

![Entity hit rate](results/charts/entity_hit_rate.png)

**Hinglish entity hit rate** (did `₹4,500` and `5 मार्च` come out in usable written form?):

<!-- table:entity -->
| | clean | market_0 |
|---|---|---|
| Prisma v3.0 (`hi-IN,en-IN`) | 96.0% [90.0, 100.0] | 96.0% [90.0, 100.0] |
| Prisma v2.5 (`hi-IN`, matched) | 94.0% [88.0, 100.0] | 92.0% [84.0, 98.0] |
| Prisma v3.0 (`hi-IN`, matched) | 96.0% [90.0, 100.0] | 96.0% [90.0, 100.0] |
| Prisma v3.0 + context | 92.0% [82.0, 100.0] | 92.0% [82.0, 100.0] |
| Whisper-small | 22.0% [8.0, 38.0] | 12.0% [4.0, 24.0] |
| Prisma v2.5 (`en-IN`) | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] |
<!-- /table:entity -->

The 0% row is a **config effect, not a model limit**. See [`results/finding_check.md`](results/finding_check.md).

![Denoise effect](results/charts/denoise_delta.png)

### Does the phone line hurt? WER change vs clean, same model, same clips (pts; \* = significant)

<!-- table:degradation -->
| model | lang | phone | loss_5 | traffic_10 | traffic_5 | market_10 | market_0 |
|---|---|---|---|---|---|---|---|
| prisma-v2.5 | bn | -0.2 | +0.0 | +0.8 | -0.2 | -1.0 | +5.7* |
| prisma-v2.5 | hi | -0.4 | -0.1 | -0.1 | +0.9 | +0.4 | +6.1* |
| prisma-v2.5 | hinglish | -0.3 | +0.0 | +0.3 | +0.6 | -0.3 | +3.3* |
| prisma-v2.5 | ta | +0.7 | +0.9 | +0.5 | +0.7 | +0.7 | +11.2* |
| prisma-v3.0 | bn | +0.6 | +2.3* | +1.6 | +3.7* | +1.9 | +13.7* |
| prisma-v3.0 | hi | +0.4 | +1.3 | +1.2 | -0.1 | +0.9 | +12.3* |
| prisma-v3.0 | hinglish | +0.6 | -1.5 | +1.5 | +1.5 | +2.1 | +2.7 |
| prisma-v3.0 | ta | +0.2 | -0.5 | -1.6 | -1.4 | -0.5 | +15.3* |
<!-- /table:degradation -->

### Every comparison the findings rely on (paired bootstrap, A − B; for WER, negative favours A)

<!-- table:claims -->
| claim (A − B) | lang | conditions | metric | Δ (pts) | 95% CI | verdict |
|---|---|---|---|---|---|---|
| v3.0 vs v2.5 | hi | all | WER | +3.2 | [+2.1, +4.3] | prisma-v2.5/raw better (significant) |
| v3.0 vs v2.5 | bn | all | WER | +3.5 | [+1.3, +6.1] | prisma-v2.5/raw better (significant) |
| v3.0 vs v2.5 | ta | all | WER | +4.2 | [+0.6, +8.6] | prisma-v2.5/raw better (significant) |
| v3.0 vs v2.5 | hi | clean | WER | +1.9 | [+0.6, +3.4] | prisma-v2.5/raw better (significant) |
| v3.0 vs v2.5 | bn | clean | WER | +0.8 | [-1.9, +3.6] | tie (not significant) |
| v3.0 vs v2.5 | ta | clean | WER | +4.6 | [+0.7, +9.7] | prisma-v2.5/raw better (significant) |
| v3.0 matched vs v2.5 matched | hinglish | all | WER | +5.9 | [+2.6, +9.2] | prisma-v2.5/matched better (significant) |
| v3.0 matched vs v2.5 matched | hinglish | all | WER (currency-neutral) | -1.4 | [-4.8, +2.0] | tie (not significant) |
| v3.0 matched vs v2.5 matched | hinglish | all | entity acc. | +2.6 | [+0.0, +7.1] | tie (not significant) |
| v3.0 context vs v3.0 raw | hinglish | all | WER | -2.2 | [-5.5, +0.6] | tie (not significant) |
| v3.0 context vs v3.0 raw | hinglish | all | entity acc. | -4.0 | [-12.0, +0.0] | tie (not significant) |
| prisma-v2.5 denoised vs raw | hi | all | WER | +2.5 | [+1.2, +3.8] | prisma-v2.5/raw better (significant) |
| prisma-v2.5 denoised vs raw | bn | all | WER | +1.3 | [+0.3, +2.4] | prisma-v2.5/raw better (significant) |
| prisma-v2.5 denoised vs raw | ta | all | WER | +1.4 | [+0.6, +2.2] | prisma-v2.5/raw better (significant) |
| prisma-v2.5 denoised vs raw | hinglish | all | WER | +0.2 | [-0.6, +1.0] | tie (not significant) |
| prisma-v3.0 denoised vs raw | hi | all | WER | +2.9 | [+0.8, +5.5] | prisma-v3.0/raw better (significant) |
| prisma-v3.0 denoised vs raw | bn | all | WER | +1.7 | [+0.4, +3.0] | prisma-v3.0/raw better (significant) |
| prisma-v3.0 denoised vs raw | ta | all | WER | +2.2 | [-0.3, +4.5] | tie (not significant) |
| prisma-v3.0 denoised vs raw | hinglish | all | WER | -3.1 | [-5.1, -1.6] | prisma-v3.0/denoised better (significant) |
| whisper-small denoised vs raw | hi | all | WER | +8.5 | [-1.8, +20.6] | tie (not significant) |
| whisper-small denoised vs raw | bn | all | WER | -4.2 | [-17.9, +10.7] | tie (not significant) |
| whisper-small denoised vs raw | ta | all | WER | +0.4 | [-3.7, +4.4] | tie (not significant) |
| whisper-small denoised vs raw | hinglish | all | WER | +7.4 | [-2.5, +19.7] | tie (not significant) |
<!-- /table:claims -->

### Findings

1. **The eval config picks the winner, not the model.** On identical Hinglish audio, switching
   Prisma v2.5's `language_code` from `en-IN` to `hi-IN` moved its entity accuracy from **0% to 94%**.
   Under that matched config, v2.5 and v3.0 are **statistically tied** on entities and on
   currency-neutral WER. The as-scored WER "win" for v2.5 comes only from v3.0 writing `4,500 रुपये`
   where the reference writes `₹4,500`. With default settings and WER alone, you can pick the wrong model.
2. **The phone line itself is almost free for Prisma.** The 300–3400 Hz band, 8 kHz μ-law, 5% packet loss,
   traffic at 10/5 dB and market at 10 dB cause **no significant WER change in 22 of 24** Prisma
   model × language cells. The two exceptions are small: v3.0 Bengali, +2.3 and +3.7 pts. Only **0 dB babble**
   (`market_0`) breaks them: significant in 7 of 8 cells. Babble sits in the speech band and
   survives the channel; traffic rumble mostly doesn't. Hinglish entity accuracy shows no significant change
   from clean under any condition, for any model.
3. **On verbatim read speech, v2.5 has lower WER than v3.0.** This is significant pooled over conditions in Hindi,
   Bengali and Tamil. On clean audio it's significant in Hindi and Tamil and a tie in Bengali. The gap widens at
   `market_0`. Error diffs show that v3.0 splits and merges compounds differently (Tamil
   "சுட்டுக் கொல்லப்பட்டார்") and misrecognizes more under 0 dB babble.
4. **Domain context: no significant effect.** Keyterms visibly fixed `ईएमआई → EMI`, but the WER change
   (−2.2 pts) and the entity change (−4.0 pts) are both inside the noise on 25 clips.
5. **Classic denoising hurts Prisma on real speech.** Pooled over the noisy conditions, spectral gating
   significantly *raised* WER for v2.5 in Hindi, Bengali and Tamil, and for v3.0 in Hindi and Bengali.
   v3.0 Tamil is a tie. The one significant improvement is v3.0 on *synthetic* Hinglish, which likely
   won't transfer to real callers. Whisper's denoise effects are all ties: its repetition loops make it too noisy to tell.
   *Don't put a generic denoiser in front of Prisma.*
6. **Whisper-small isn't a viable baseline for Indic telephony.** It writes Bengali speech in
   Devanagari 99% of the time, falls into repetition loops in 4–10% of clips, and runs at
   ~6.7 s per clip on CPU. Prisma's median API round-trip is ~0.3 s.

Errors that remain in both Prisma models, in every condition: `18 अगस्त → 1 8 अगस्त / 1 August`,
`31 मई → 3 1 मई / 3/1/May`. The digits are heard; the formatting breaks the date.

**Reliability note:** 3 requests (one clip, clean audio only) returned `403` for its WAV bytes.
They were resent once as lossless FLAC (identical samples) and succeeded. These rows are marked
`sent_as: flac_after_403` in the cache.

## Quickstart

```bash
uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env            # add GNANI_API_KEY (never committed)

# 1. data: FLEURS subset + DEMAND noise (free); Hinglish TTS is billed → capped
python -m shorgul.cli prepare
python -m shorgul.cli prepare --langs "" --tts --max-calls 25 --no-noise

# 2. simulate calls, 3. denoise
python -m shorgul.cli degrade
python -m shorgul.cli enhance

# 4. transcribe: ALWAYS dry-run first; billed calls are capped by --max-calls
python -m shorgul.cli run --variants raw,denoised,context --dry-run
python -m shorgul.cli run --models whisper-small --variants raw,denoised     # local, free
python -m shorgul.cli run --models prisma-v3.0 --langs hi --max-calls 200

# 5. score + charts, 6. explore
python -m shorgul.cli score
streamlit run app/dashboard.py
```

**Try the whole thing without credits:** `run --mock` returns deterministic fake
transcripts (worse on harder conditions) and writes to `results/mock/`, a separate cache
and results folder that never mixes with real data. Then run `score --mock`, and the dashboard's *Data* switch shows it.

## Cost and safety rails

- **Every billed call goes through `results/cache.sqlite`**, keyed by
  `sha256(audio bytes + model + params)`. A key is never sent twice; re-running any stage is free.
- `--max-calls` caps **new** billed requests per run (default `0` = cache only). `--dry-run`
  prints cached-vs-needed counts per model.
- Prisma calls are sequential. `429 RATE_LIMITED` → exponential back-off (1, 2, 4, 8, 16 s).
  `400/422` → logged, not retried, and cached as an error so it isn't re-billed.
  `truncated: true` → status `ok_truncated`.
- The API key is read from `.env` only, and is never logged or written to results. A test checks this.
- Each stage reads from and writes to disk (`data/clean`, `data/degraded`, `data/enhanced`,
  `results/hyps.parquet`, `results/results.parquet`), so any stage can be re-run on its own.

## Design notes

- **Context variant without leakage**: the Prisma v3.0 `topic`/`keyterms` are one fixed,
  domain-level list (EMI, KYC, UPI, किस्त, …) in `configs/bench.yaml`. They are **never**
  derived from a clip's own reference or entities.
- **Denoising is applied where a vendor could apply it**: to the received 8 kHz-band audio,
  after the channel. Spectral gating can *hurt* ASR by smearing consonants, and the benchmark
  reports that honestly (ΔWER chart).
- **SNR is measured on active speech** (frames within 40 dB of the loudest), so FLEURS'
  leading and trailing silence doesn't inflate the effective SNR. Speech and noise are scaled
  together to avoid clipping, which leaves the SNR exact.
- **FLEURS without the deprecated loading script**: the loader streams
  `test.tar.gz` from the Hub and stops after 25 clips (≤ 25 s, one per sentence), instead of
  downloading 250 MB per language.

## Layout

```
configs/bench.yaml        conditions, language codes, context, paths
shorgul/data/             FLEURS loader, Timbre TTS, DEMAND noise, Hinglish script
shorgul/degrade/          noise @ SNR, phone channel (ffmpeg μ-law), packet loss, pipeline
shorgul/enhance/          spectral-gating denoise
shorgul/asr/              Prisma client, Whisper-small, mock, sqlite cache, job runner
shorgul/metrics/          normalization, WER/CER, entities, aggregation, charts
shorgul/cli.py            prepare | degrade | enhance | run | score
app/dashboard.py          Streamlit dashboard
tests/                    pytest (no network, no credits)
```

## Data and licences

- **FLEURS** (Google), CC BY 4.0: `google/fleurs`, test split, `hi_in`, `bn_in`, `ta_in`.
- **DEMAND** (Thiemann, Ito, Vincent, 2013), CC BY-SA 3.0: Zenodo 10.5281/zenodo.1227121.
  `traffic` = STRAFFIC ch01; `market` = SPSQUARE + PCAFETER ch01, mixed.
- **Hinglish call-centre lines**: written for this benchmark and synthesized with Gnani Timbre v2.5
  (voices Nalini, Deepak, Bhavna, Roopesh).

Odia isn't included because Prisma doesn't support it yet.
