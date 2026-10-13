# OOSA ad copy style guide

Distilled from OOSA's ad copy practice and the oosamarketing.com copywriting tools. The validator
(`scripts/validate.py`) enforces the hard limits; the rest is judgement.

## Meta (Facebook / Instagram feed)

### Primary text — the three-block structure

```
<emoji> Hook line one
Hook line two (optional)
...
Body: the concrete product / offer / place detail, one to three lines
...
Call to action, one line
```

| Rule | Why |
|---|---|
| Blocks separated by a line that is only `...` | It is literally how OOSA ads read in feed; the validator warns when missing |
| Hook complete within 125 characters | Meta folds primary text at ~125 chars behind "See more" |
| One emoji opening the hook | Stops the scroll without looking spammy; a second in the CTA is fine |
| Body carries the facts | Where it's made, what it's for, what's different, for whom |
| CTA is a single imperative line | shop / get / grab / order / discover / see / visit / claim / book |
| Hard max 2200 characters | Platform limit; in practice 180–320 characters |

### Headline (≤ 40 chars, ≤ 12 words)
Action or identity, not a product name. "Get the 32 oz Steel Bottle" / "Built to be dropped."

### Description (≤ 30 chars, ≤ 8 words)
A nudge: scarcity, origin, benefit. "Lifetime warranty" / "Leak-proof. Fits cup holders."

### Options
Three per field by default, each with a **different angle**:

1. Seasonal / moment ("Before the first hot weekend")
2. Identity / belonging ("One bottle for the commute, the gym and the trail")
3. Product detail / origin ("Triple-wall 18/8 stainless steel")
4. Social proof (a real review or count from the brief, never an invented one)
5. Urgency ("Get yours before Monday")

Options must not duplicate each other (case-insensitive) and should not all open the same way.

## Google Ads (Performance Max and Search RSA)

| Asset | Limit | Count (PMax) | Count (RSA) | Notes |
|---|---|---|---|---|
| Headline | 30 | 5 / 10 / 15 | 3–15 | no `!`; ≥ 2 brand/keyword headlines; distinct angles; any three must read well together |
| Long headline | 90 | 1–5 | — | complete sentences; a headline plus a reason |
| Description | 90 | 2–4 | 2–4 | each contains a CTA |
| Path / display URL | 15 per segment | 1 | 2 | no spaces |
| Sitelink | 25 | ≤ 4 | ≤ 4 | optional; needs a landing URL |
| Callout | 25 | ≤ 4 | ≤ 4 | optional; short proof points |

Google combines headlines at serve time, so avoid headlines that only make sense in a fixed order. Google
disallows exclamation marks in headlines and repeated punctuation anywhere. Use Title Case consistently within a set
when the brand does; sentence case otherwise.

## Universal don'ts

- No ALL CAPS words except brand names that are styled that way (NORTHPEAK on its own packaging).
- No hashtags in ad copy.
- No claims that the identity or brief does not support (awards, "#1", medical or safety claims).
- No prices or offers unless the brief states them.
- Don't invent locations, founders, materials or dates.

## Voice adaptation

The brand identity usually names a dominant trait (`#1`) and a supporting trait (`#2`). Let `#1` drive hooks and
headlines and `#2` drive the body and CTA. Reuse the brand's own nouns (trail, commute, cup holder, grip) and keep the
sentence length the existing copy uses.
