# Platform limits

Authoritative source: `ad_copywriter/data/platform_spec.json` in the `ad-copywriter` tool (print it with `python scripts/validate.py --print-spec <platform>`).
Numbers mirror the oosamarketing.com Google and Meta copywriting tools.

| Platform | Field | Max chars | Options | Min | Style checks |
|---|---|---|---|---|---|
| meta | primary_text | 2200 (fold 125) | 5 | 1 | `...` blocks, emoji lead, hook within fold, CTA block |
| meta | headline | 40 | 5 | 1 | ≤ 12 words |
| meta | description | 30 | 5 | 1 | ≤ 8 words |
| google_pmax | headline | 30 | 15 (batches 5/10/15) | 5 | no `!` |
| google_pmax | long_headline | 90 | 5 | 1 | |
| google_pmax | description | 90 | 4 | 2 | |
| google_pmax | path | 15 | 1 | 0 | no spaces |
| google_pmax | sitelink | 25 | 4 | 0 | optional |
| google_pmax | callout | 25 | 4 | 0 | optional |
| google_rsa | headline | 30 | 15 | 3 | no `!` |
| google_rsa | description | 90 | 4 | 2 | |
| google_rsa | path | 15 | 2 | 0 | no spaces |

Per-set rows (not counted): landing page URL, display URL, media folder link; Meta audience / custom audience;
Google interests / in-market / first-party data.

Counting: NFC code points. The website tools count UTF-16 units, so an emoji like 🏄‍♂️ counts 4 here and 5 there, and a single-code-point emoji like 🧊 counts 1 here and 2 there.
