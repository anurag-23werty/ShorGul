# ShorGul: solution pitch

**ShorGul tests Indian-language speech recognition on real phone-call conditions, and catches the failures that WER misses.**
[Website](https://anurag-23werty.github.io/ShorGul/) · [Dashboard](https://shorgul.streamlit.app/) · [Code](https://github.com/anurag-23werty/ShorGul)

## The problem
Indian voice bots (collections, KYC, EMI reminders) run on narrowband phone lines, mobile codecs and lossy VoIP, and
callers are often in traffic or crowded markets. Speech models are chosen on clean audio with one number, WER. WER
treats "₹4,500" and "chaar hazaar paanch sau rupay" as equally wrong, so it can't tell a model that misheard the
amount from one that wrote it differently. And a misconfigured deployment fails **silently**: the API returns success.

## What we found (Gnani Prisma v2.5 / v3.0, Whisper-small; 1,140 paired statistical tests)
- **One API setting decides whether amounts survive.** On the same Hinglish customer-care audio, `language_code=en-IN`
  gives **0%** amount accuracy (amounts come back as romanised words), and `hi-IN` gives **94% [88, 100]**. No error, no warning.
- **A bad phone line barely matters.** Band-limiting, μ-law, the AMR-NB mobile codec, Opus VoIP, packet loss and 10 dB
  noise caused no significant WER change in **52 of 56** Prisma cells. Only 0 dB crowd noise breaks it (7 of 8 cells).
- **Common "fixes" can hurt.** A generic denoiser before Prisma made WER significantly worse in **5 of 6** cells.
- **Real audio check:** on 60 real Hindi phone calls (Gram Vaani), Prisma v2.5 had 16.1% WER and v3.0 had 18.9%
  (+2.7 [+0.3, +5.3] pts, paired): the newer model is not automatically the better one.

## The solution: three tools for three expensive moments
| moment | tool | what it does |
|---|---|---|
| **Before go-live** | `shorgul audit ./calls` | Replays a team's own calls through phone line, packet loss, traffic and market noise, and measures how much the transcript changes. Gives an **A–F grade, the breaking point** and a one-file `report.html`. **No reference transcripts needed.** |
| **In a sales deal** | the same audit, on the prospect's calls | Gives a solutions engineer evidence on the client's own audio, and catches config mistakes like `en-IN` vs `hi-IN` before the contract. |
| **In CI** | `shorgul compare` | A paired-bootstrap release gate: fails the build only when a new model or config is **significantly** worse on the chosen metric (WER or amount accuracy), not on noise. |

Plus **entity repair**: turns spoken amounts and dates back into "₹4,500 · 5 March" (0% → **94%** on unseen lines), model-agnostic.

## Why it's credible
- Every number on the site and in the README is generated from results files; differences whose CI includes 0 are reported as ties.
- 127 tests with no network; every API call is cached and capped (`--max-calls`); the key never leaves `.env`.
- A Streamlit dashboard and a website where you can hear the same call degrade and watch the amount get lost.

## Honest limits and next step
The Hinglish set is synthetic (Gnani Timbre); real calls are 60 Hindi Gram Vaani calls, reported in aggregate only.
The A–F grade is calibrated on Prisma. Next step: a two-week pilot with one team ([docs/PILOT.md](docs/PILOT.md))
to test whether grades predict production errors.

*Built by Anurag Choudhury for Gnani AI's Great Indian AI Internship Challenge 2026, on Gnani Prisma and Timbre.*
