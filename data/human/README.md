# Human validation recordings

Put up to 10 of your own Hinglish recordings here (wav/flac/ogg, ≤ 30 s each, phone or laptop mic is fine),
plus a `refs.csv`:

```csv
file,reference,entities
call_01.wav,"नमस्ते सर, आपकी loan EMI ₹4,500 की 5 मार्च को due है।","₹4,500;5 मार्च"
```

Write the reference exactly as said, with amounts and dates in written form (₹4,500, 5 मार्च). Then:

```bash
python -m shorgul.cli prepare --langs "" --human --no-noise
python -m shorgul.cli degrade --langs hinglish_human
python -m shorgul.cli run --langs hinglish_human --dry-run      # shows the call count first
```

Results are reported as **hinglish_human**, next to (never mixed with) the TTS results.
