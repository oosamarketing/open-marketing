# The copy document

One JSON file per brand + platform. Schema: `ad_copywriter/data/copy_document.schema.json` (in the `ad-copywriter` tool).

```json
{
  "schema_version": 1,
  "platform": "meta",                       // meta | google_pmax | google_rsa
  "brand": {
    "name": "Northpeak",                    // required
    "website": "https://example.com",
    "page_name": "Northpeak",               // Meta mockup header (defaults to name)
    "avatar_path": "brand-assets/logo/avatar.png",   // round page avatar for Meta/IG mockups (see preview/avatar.py)
    "logo_path": null,                      // file path or URL for previews; null = OOSA logo in the deck, initial in the mockup
    "primary_color": "#0F6E6E", "secondary_color": "#F5A623", "font_family": null,
    "identity": "Confident, plain-spoken, short sentences. …"
  },
  "sets": [                                 // one per theme = one legacy sheet = one deck section
    {
      "theme": "Steel Bottle 32 oz",
      "landing_page_url": "https://example.com/products/steel-bottle-32oz",
      "display_url": "example.com",
      "media_folder_link": null,
      "media_path": "previews/assets/steel-bottle.jpg",   // single product image for the mockups (file or URL)
      "media_paths": [                                 // OR one creative per variation (rotates); overrides media_path
        {"square": "ads/bottle-trail-1x1.png", "wide": "ads/bottle-trail-1.91x1.png"},
        {"square": "ads/bottle-desk-1x1.png", "wide": "ads/bottle-desk-1.91x1.png"}
      ],
      "cta": "Shop now",                    // Meta button label
      "audiences": {"audience": "…", "custom_audience": "…"},        // meta
                                            // google: {"interests", "in_market", "first_party_data"}
      "fields": {
        "primary_text": ["🧊 Hook\n...\nBody\n...\nCTA", "…", "…"],
        "headline": ["…", "…", "…"],
        "description": ["…", "…", "…"]
        // google_pmax: headline, long_headline, description, path (1), sitelink (≤4), callout (≤4)
        // google_rsa:  headline, description, path (≤2)
      },
      "notes": "optional rationale for the reviewer"
    }
  ],
  "validation": null,                       // filled by validate.py --write
  "meta": {"generated_by": "agent", "model": null, "created_at": "2026-09-14T12:00:00+00:00"}
}
```

Rules:
- `fields` keys must be valid for the platform; unknown keys are validation errors.
- Every value is a list of strings. Only `primary_text` may contain line breaks.
- In `primary_text`, a line that is exactly `...` (or `…`) separates blocks.
- Keep theme names as the user gave them: they become sheet names (truncated to 31 chars) and deck headings.

`validation` after `validate.py --write`:

```json
{"ok": false, "checked_at": "…", "spec_version": 1,
 "errors":   [{"set": "Steel Bottle 32 oz", "field": "headline", "index": 1, "code": "over_max", "chars": 44, "limit": 40, "message": "Headline 2 is 44 chars (max 40)"}],
 "warnings": [{"set": "Steel Bottle 32 oz", "field": "primary_text", "index": 0, "code": "hook_beyond_fold", "chars": 131, "limit": 125, "message": "…"}],
 "summary":  {"Steel Bottle 32 oz": {"primary_text": {"count": 3, "min_count": 1, "max_count": 5, "max_chars": 2200, "fold_chars": 125, "chars": [282, 214, 214]}}}}
```

Error codes: `unknown_field`, `empty_value`, `over_max`, `too_many_options`, `too_few_options`, `duplicate_option`,
`google_exclamation_in_headline`, `newline_in_field`, `spaces_in_path`.
Warning codes: `hook_beyond_fold`, `missing_block_structure`, `missing_emoji_lead`, `no_cta_block`, `over_max_words`,
`all_caps`, `double_space`, `trailing_space`, `count_below_batch`, `sitelink_without_landing_url`, `duplicate_theme`.
