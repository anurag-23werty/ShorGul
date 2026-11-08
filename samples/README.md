# Bundled samples

Everything here is safe to redistribute. **No real recorded calls are included anywhere in this repo.**

| path | what | licence |
|---|---|---|
| `calls/*.wav` | 6 synthetic Hinglish customer-care lines, written for ShorGul and voiced with Gnani Timbre v2.5 (`hg_000`: "…loan EMI ₹4,500 की 5 मार्च को due है।") | written for this project; synthetic speech |
| `noise/traffic.wav` | 20 s excerpt of DEMAND `STRAFFIC` (channel 1) | CC BY-SA 3.0, Thiemann, Ito, Vincent (2013), doi:10.5281/zenodo.1227121 |
| `noise/market.wav` | 20 s excerpt of DEMAND `SPSQUARE` + `PCAFETER` mix (channel 1) | CC BY-SA 3.0, same source |

`shorgul audit` uses `noise/` automatically when the full DEMAND files (`data/noise/`) haven't been downloaded.
