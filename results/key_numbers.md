## wer

| | Hindi | Bengali | Tamil | Hinglish* |
|---|---|---|---|---|
| Prisma v2.5 | 7.1% [4.5, 10.0] → 13.2% [9.1, 17.4] | 13.1% [9.2, 17.3] → 18.7% [11.4, 28.4] | 21.3% [16.1, 26.6] → 32.5% [25.4, 40.8] | 62.1% [56.1, 69.0] → 65.5% [59.4, 72.2] |
| Prisma v3.0 | 9.0% [5.8, 12.6] → 21.3% [15.0, 28.1] | 13.8% [9.9, 18.5] → 27.5% [19.4, 38.1] | 25.9% [20.2, 32.4] → 41.2% [32.7, 51.9] | 38.2% [34.3, 42.7] → 40.9% [35.9, 46.2] |
| Prisma v3.0 + context | – | – | – | 36.7% [31.7, 42.0] → 38.8% [33.4, 44.4] |
| Whisper-small | 79.3% [53.6, 109.2] → 97.5% [78.8, 123.2] | 108.2% [104.1, 112.8] → 123.2% [102.3, 151.6] | 73.5% [61.8, 90.2] → 110.8% [95.2, 132.0] | 61.5% [52.8, 70.2] → 104.6% [83.5, 132.3] |

## entity

| | clean | market_0 |
|---|---|---|
| Prisma v3.0 (`hi-IN,en-IN`) | 96.0% [90.0, 100.0] | 96.0% [90.0, 100.0] |
| Prisma v2.5 (`hi-IN`, matched) | 94.0% [88.0, 100.0] | 92.0% [84.0, 98.0] |
| Prisma v3.0 (`hi-IN`, matched) | 96.0% [90.0, 100.0] | 96.0% [90.0, 100.0] |
| Prisma v3.0 + context | 92.0% [82.0, 100.0] | 92.0% [82.0, 100.0] |
| Whisper-small | 22.0% [8.0, 38.0] | 12.0% [4.0, 24.0] |
| Prisma v2.5 (`en-IN`) | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] |

## claims

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

## degradation

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
