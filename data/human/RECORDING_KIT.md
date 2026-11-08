# Recording kit: 12 lines × 2 channels (about 20 minutes)

Read each line **naturally, the way you would on a real customer-care call**. Don't read numbers digit by digit
(say *तेरह हज़ार सात सौ पचास*, or however you'd naturally say it). Each line is under 30 seconds.

## Two recordings of every line

**A · direct** (`<id>_direct.m4a`): your phone's voice-memo app, normal room, phone at a normal distance.

**B · real call** (`<id>_call.m4a`): the same line spoken **over an actual phone call**, recorded on the *receiving* end.
Pick one way:
- **Best:** a normal cellular call (not Wi-Fi calling, not WhatsApp) to a second phone, with call recording on the receiving phone
  (built into most Android dialers). That's the real 8 kHz phone path the benchmark simulates.
- **If you can't record calls:** call a second phone, put it on speaker, and record that speaker with a third device's voice memo.
  This adds some room sound, but it's still a real network path.

Write down which way you used (it goes in the report). Any audio format works (m4a, wav, mp3 or ogg); the loader converts it.

## Lines

1. **hh_000** · सर, आपकी car loan की EMI ₹13,750 है और यह 4 जनवरी को auto-debit होगी।
2. **hh_002** · आपका policy renewal ₹8,999 का है, last date 27 फरवरी है।
3. **hh_004** · हम आपको ₹2,400 का refund 11 सितंबर तक भेज देंगे।
4. **hh_005** · मेरी salary ₹46,000 है, क्या मुझे ₹3,00,000 का personal loan मिल सकता है?
5. **hh_007** · credit card bill ₹19,640 का है, minimum due ₹980 है।
6. **hh_010** · मैंने 9 अप्रैल को ₹4,050 का bill pay किया था पर receipt नहीं आई।
7. **hh_011** · आपका loan ₹2,75,000 का sanction हो गया है, disbursement 2 नवंबर को होगा।
8. **hh_014** · मेरी EMI ₹11,200 से कम करके ₹9,800 कर दीजिए।
9. **hh_017** · आपके account से 28 दिसंबर को ₹12,000 ATM से निकाले गए थे।
10. **hh_019** · insurance claim के ₹64,250 आपके account में 19 मई को आएंगे।
11. **hh_022** · electricity bill ₹2,315 का है, due date 24 मार्च है।
12. **hh_024** · सर, outstanding ₹5,670 है, आज pay करेंगे तो late fee ₹350 नहीं लगेगी।

## Then

```bash
cp data/human/refs.csv.template data/human/refs.csv      # file names already match <id>_direct / <id>_call
python -m shorgul.cli prepare --langs "" --human --no-noise
python -m shorgul.cli run --langs hinglish_human --dry-run   # shows the exact call count before anything is billed
```

Consent: these are your own recordings of scripted lines (no customer data). They stay out of git (`data/human/*` audio is ignored)
unless you choose to publish them.
