# ShorGul site: brief

The brief comes from the user's written spec (2026-11-08). Their words are quoted where they gave them. Where the
spec left gaps, the decision is marked **authored**. Where the data forced a change, it is marked **data-forced**,
with the evidence.

## 1. Vibe and references
> "the quality bar is a top YC dev-tool launch page (think Linear, Resend, Vercel changelog pages): restrained,
> precise, every animation explains something."

> Concept: "a phone line going bad." The visual language is signal: waveforms, spectrogram bands, monospace
> transcripts, one accent colour for "signal recovered".

## 2. The journey, in their words
1. HERO: "WER lies about Indian phone calls." (to be adapted to the verified framing)
2. PINNED "A call goes bad": band-limit → μ-law → market 10 dB, with the transcript degrading word by word
3. THE FINDING: two rankings, with lines that cross
4. THE FIX: the broken transcript repaired in place
5. DEGRADATION CURVES
6. WHO USES IT: three stories with real terminal commands
7. HOW IT WORKS: the pipeline assembles
8. CLOSE: built on Gnani, links, method & limitations

## 3. Energy curve (authored, from their section order)
Calm (1) → rising tension (2, the longest scene) → sharp turn (3) → relief (4) → steady competence (5, 6, 7) → quiet resolve (8).

## 4. Feeling curve
```
1  Curiosity     a calm, clean waveform and a claim that sounds too strong to be true
2  Unease        the same real call degrades under your scroll; a generic model loses the money ("₹999" → "नोसो निन्यानवे रुपे")
3  Surprise      the rankings cross: the model WER prefers isn't the one that got the amount right; one setting moves 0% → 94%
4  Relief        the broken transcript repairs in place; the amount snaps back in the accent colour
5  Trust         every curve carries its CI; the visitor can hover and check
6  Recognition   "that's my job": voice-bot go-live, a customer deal, a release gate, each with the real command
7  Clarity       the whole machine in one line of boxes
8  Resolve       built on Gnani, three links, the honest limits one click away
```

**Peak:** act 3. "The model WER ranks first isn't the one that got the payment amount right, and one API setting
moved accuracy from 0% to 94%." It gets the most deliberate scroll room after the pinned scene, and act 2 is
built to set it up.

**Tell-someone sentence:** "It's the site where you watch a phone call lose the money and a metric pick the
wrong model."

**Authored silence:** none. Every scroll span either drives a transformation or holds text.

## 5. Signature move (seed: "every animation explains data")
**The amount chip.** One chip follows the payment amount through the whole page. It reads digits on the clean
call, number words as the line degrades, and turns red and missing for the generic model. It stays orange for
Prisma, then snaps back to "₹999" when the fix runs. Every state is a real transcript from `data.json`.

## 6. Aesthetic range
> Near-black #0B0B0C, off-white #EDEDED, muted greys, ONE accent #FF6A1A only for correct entities and the fix,
> red only for errors. One grotesk (Inter Tight / Geist) + one mono. Left-aligned, 12-col, max ~1100px.
> No gradients, glass, orbs, emoji cards, fake logos, "Revolutionize/Unlock/Seamless".

## 7. One world or scenes
Distinct scenes in a vertical document, with one pinned set piece (act 2). This isn't a continuous flythrough.

## 8. Assets
No photography and no generation. All visuals are drawn from real data: waveform peaks and spectrogram bands
computed from the actual degraded audio, the real transcripts, and the real metrics. Two real audio clips
(clean + market_10), compressed to mp3.

## Data-forced changes (evidence: `results/finding_check.md`, `results/comparisons.csv`)
- **Hero headline.** "WER lies" overstates it. Verified framing: *your eval config picks the winner, not the model*.
  Proposed headline: "WER picks the wrong model for Indian phone calls."
- **Act 2: whose transcript degrades.** At market_10, Prisma v3.0 loses **0** of 25 Hinglish amounts/dates, and
  v2.5 (hi-IN) loses 1. The "₹ → words → missing" arc is real only for the generic baseline (Whisper-small):
  hg_017 "₹999 … 14 तारीख" → "नोसो निन्यानवे रुपे … चोडा तारीक"; hg_020 "40,000" → "खालिख हदारोपे". Act 2 shows that
  arc, with Prisma's chip holding beside it. This is a stronger and true contrast.
- **Act 3: where the lines cross.** On identical Hinglish audio, the WER ranking and the entity ranking disagree.
  The crossing pairs that matter are a statistical **tie** on entities (v3.0 vs v2.5 hi-IN). The site shows CI bars
  and labels ties as ties. The dramatic, significant move is the config: v2.5 en-IN 0% → hi-IN ~94%.
- **Act 4: "15th".** No benchmark clip has "pandrah"/"15th" in a degraded transcript. The fix scene uses real repaired
  outputs only, e.g. v2.5 en-IN "nao sau ninyanave rupay … chaudah tarikh" → "₹999 … 14 tarikh".
- **Act 6: command syntax.** The real CLI is `shorgul audit ./calls --lang hi` (not `hi-IN`), and the terminal output is
  captured from actual runs.
- **Act 8: "Payment Capture demo".** No such demo exists in this repo. The link is omitted unless the user provides one.
