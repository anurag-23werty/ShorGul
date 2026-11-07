# ShorGul Bench — implementation plan

## Context
This is the entry for Gnani's Great Indian AI Internship Challenge, due Nov 10, 2026 (today is Nov 8). `/Users/anurag_77y/Shorgul` already has the full file skeleton, but **every file is 0 bytes**. `.venv` is Python 3.13.5 with **no packages installed**. ffmpeg is at /opt/homebrew/bin. There is no git repo. `.env` holds GNANI_API_KEY, and `.gitignore` already covers .env, wavs and cache.sqlite.
The goal is a reproducible benchmark: clean speech → simulated Indian phone call → optional fixes → ASR (Prisma v2.5, Prisma v3.0, Whisper-small) → WER/CER/entity accuracy → Streamlit dashboard and README charts.
Decisions so far: noise comes from **DEMAND (Zenodo, CC BY-SA 3.0)**, and the API budget is **about 5,000 calls**, enough for the full grid.

## Design decisions
- **Order of the degradation chain** (realistic, since noise is acoustic and happens at the caller's end): noise mixed at SNR on clean 16 kHz audio → phone chain (bandpass 300–3400 Hz → 8 kHz → μ-law → 16 kHz, done with ffmpeg) → packet loss.
  - clean = untouched; phone = chain only; loss_5 = phone + 5% loss; traffic/market = noise + phone.
- **Packet loss**: 20 ms frames, Bernoulli 5%, lost frames set to zero. Applied after decoding, at 16 kHz.
- **SNR**: speech power is measured over active frames only, using an energy gate at −40 dB relative to the peak frame, because FLEURS has leading and trailing silence. Formula as in the spec. Noise is looped or cropped from a seeded random offset. If the peak exceeds 0.99, both speech and noise are scaled down together, which keeps the SNR exact.
- **Seed** = `int(sha256(f"{clip_id}|{condition}").hexdigest()[:8], 16)`. Python's `hash()` is salted per process, so it would not be deterministic.
- **Noise** (`shorgul/data/noise_fetch.py`) downloads DEMAND 16k zips from Zenodo: STRAFFIC → `traffic.wav`, SPSQUARE + PCAFETER mixed → `market.wav` (channel 1, about 5 min each).
- **FLEURS**: newer `datasets` releases dropped script loaders, so it uses `huggingface_hub.hf_hub_download` for `data/{cfg}/test.tsv` + `audio/test.tar.gz`, and extracts only the first 25 clips with duration ≤ 25 s. Output is 16 kHz mono wav, and the reference is the normalized `transcription` column.
- **Hinglish**: 25 call-centre lines (EMI, KYC, ₹ amounts, dates) that I write into `scripts_hinglish.txt` as `id|text|entities`. Hindi is in Devanagari and English terms in Latin. TTS uses Timbre v2.5 (`POST /api/v1/tts/inference`, JSON with text, voice, model `timbre-v2.5`, language `hi-IN`, audio_config wav). It rotates 2–3 Hindi voices from the voice catalog (checked before coding). Output is resampled to 16 kHz. TTS calls go through the same cache and `--max-calls` gate.
- **API format per source**: FLEURS uses `format=verbatim` (WER runs). Hinglish uses `format=transcribe` (entity runs: ITN produces ₹/digits that match the written references), so it costs one call per clip, condition and model. Language codes: v2.5 uses `en-IN` for Hinglish; v3.0 uses `hi-IN,en-IN`.
- **Context variant** (v3.0, Hinglish only): a **static domain** `topic` + `keyterms` list in bench.yaml (bank/EMI/KYC vocabulary). These are *not* taken from each clip's reference entities, so there is no leakage.
- **Denoised variant**: `noisereduce` spectral gating (non-stationary), applied to noisy conditions after degradation. That is what a server-side fix would see. It may hurt ASR, and that is a valid finding.
- **Whisper-small**: `faster-whisper` on CPU with int8, a fixed language (hi/bn/ta, and hi for Hinglish), beam 5 and temperature 0. It goes through the cache too.
- **Cache**: `results/cache.sqlite`, with key = sha256(audio bytes + model + canonical JSON params). It stores the response JSON, status and latency, and is never called twice for the same key. `--mock` uses a separate `results/mock/` (its own cache, hypotheses and results), so mock output never mixes with real data.
- **Mock ASR**: returns the reference with seeded word drops and substitutions that scale with how hard the condition is, so charts can be tested end to end.
- **Gnani client**: sequential calls. A 429 triggers exponential backoff (1, 2, 4, 8, 16 s, at most 5 tries). A 400/422 is logged with status=`error`, not retried, and not cached as success. `truncated: true` is recorded in status. The key is read from env and never logged.
- **Scoring**: NFC normalization, punctuation and danda removed, Latin lowercased, whitespace collapsed; WER and CER via `jiwer`. For Hinglish WER, both sides are romanized with `indic-transliteration` first (a script mismatch would otherwise dominate). The README states this caveat; entity_hit_rate is the headline metric for Hinglish.
- **Entity hit rate**: the share of reference entities found in the hypothesis. Amounts are normalized to bare digits (₹ and commas stripped; a small Hindi/English number-word map is used as fallback). Dates match on the day digits plus a month alias table (March/मार्च). It is NaN for FLEURS.

## Call budget (fits 5,000)
| Run | Calls |
|---|---|
| raw: 100 clips × 7 conditions × 2 Prisma models | 1,400 |
| denoised: 100 × 4 noisy conditions × 2 | 800 |
| context: 25 Hinglish × 7 (v3.0) | 175 |
| TTS | 25 |
| **Total** | **≈ 2,400** (plenty of headroom for retries and errors) |

Real runs are staged and each one needs your approval: a 5-call smoke test, then one language, then the rest, always with `--max-calls`. `run --dry-run` prints how many calls are planned versus already cached.

## Files (fill the existing skeleton)
- `requirements.txt`: numpy, scipy, soundfile, pandas, pyarrow, pyyaml, typer, requests, python-dotenv, jiwer, huggingface_hub, noisereduce, faster-whisper, indic-transliteration, streamlit, matplotlib, pytest
- `configs/bench.yaml`: langs, n_clips, max_dur, conditions (type, snr, loss), models, the context topic and keyterms, paths
- `shorgul/config.py`: load YAML, paths, `seed_for()`, `load_env()`
- `shorgul/data/{fleurs_loader,tts_generator,noise_fetch}.py`, `scripts_hinglish.txt` → `data/manifest.csv` (columns as specified)
- `shorgul/degrade/{telephony,codecs,packet_loss,noise,pipeline}.py` → `data/degraded/{condition}/{clip_id}.wav`
- `shorgul/enhance/denoise.py` → `data/enhanced/{condition}/{clip_id}.wav`
- `shorgul/asr/{base,cache,prisma,whisper_local}.py` plus a mock in base → `results/hyps.parquet`
- `shorgul/metrics/{normalize,wer_cer,entities,aggregate}.py` → `results/results.parquet` (spec row schema), `summary.csv`, `charts/*.png`
- `shorgul/cli.py` (typer): `prepare | degrade | enhance | run (--models --conditions --variants --max-calls --mock --dry-run) | score`
- `app/dashboard.py`: filters (lang, model, variant); WER-vs-condition lines; entity-hit bars; worst-case table with clean/degraded audio players
- `README.md`: method, the degradation chain diagram, results charts, caveats, how to reproduce

## Phases (after each one: pytest + a tiny e2e run, show the output, then stop and wait for you)
1. **Scaffold + data**: install requirements with uv; config, CLI skeleton, FLEURS loader, noise fetch, Hinglish script. The TTS code is written but **not called**. E2E: `prepare --langs hi --n 2`, then cat manifest.
2. **Degrade**: all conditions. Tests: measured SNR within ±0.2 dB, length preserved, same seed → identical bytes, packet-loss fraction about 5%. E2E: degrade 2 clips × 7 conditions and print measured SNR and RMS.
3. **ASR + cache + mock**: tests mock `requests` (no double call on a cache hit, backoff on 429, no retry on 400, key never in logs). E2E: `run --mock` on the small set, plus a `--dry-run` count.
4. **Enhance + metrics + score**: tests for normalize, WER/CER on known pairs, entity matching. E2E: mock pipeline → results.parquet → summary.
5. **Dashboard + README charts**: launch Streamlit and check it with mock data.
6. **Real runs** (your approval at each step): TTS (25 calls), smoke (5), then the staged grid; Whisper runs locally.

## Verification
- `.venv/bin/pytest -q` passes after every phase.
- Mock full pipeline: `prepare → degrade → enhance → run --mock → score → streamlit run app/dashboard.py` with no API calls.
- Sanity checks: clean WER < phone < market_0 in real results; a cache replay of a real run makes 0 new calls.
- `grep -r` for the key in results/ and logs finds nothing.
