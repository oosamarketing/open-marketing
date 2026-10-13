# Mockup specs

Per theme, `--combos N` variations (default 3). Variation *i* rotates through the options starting at index *i*, so
three variations show every option at least once in a different pairing. Rows never split across pages.

Creative: set `sets[].media_path` in the copy document (a local image path or URL, e.g. the product shot from the
brand's Shopify `/products/<handle>.json`) and it is used as the ad image in the Meta cards. Without it a grey
"Image / video" placeholder is shown. `brand.logo_path` fills the avatar / favicon; otherwise the brand initial.

## Google search result (`google_pmax`, `google_rsa`) — one per row, 600px

```
Sponsored                                          14px bold #202124
(N) Northpeak                                      favicon circle (logo or initial), site name 14px
    example.com › steel-bottle-32oz                12px #4d5156 (domain from landing URL + path segments)
Headline 1 | Headline 2 | Headline 3               20px #1a0dab, " | " separators
Description 1 Description 2                        14px #4d5156 (two descriptions, rotated)
Sitelink        Sitelink                           2×2 grid, 16px #1a0dab
Sitelink        Sitelink
Callout · Callout · Callout · Callout              14px #4d5156
```

## Meta — Facebook feed post (340px) and Instagram feed post (290px) side by side per variation

```
Facebook                                           Instagram
(N) Northpeak              ···                     (n) northpeak             ···
    Sponsored · 🌐                                     Sponsored
Primary text … See more   (folded at 125)          [ square creative ]
[ creative, 340px tall ]                           Shop now                     ›   (blue #0095f6 bar)
EXAMPLE.COM                   [Shop now]           ♡  ◯  ➤                     ⊓
Headline (600) / Description (grey)                1,204 likes
👍 ❤️ 1.2K        34 comments · 9 shares            northpeak Primary text … more
👍 Like   💬 Comment   ↗ Share
```

Reaction counts and like counts are decorative placeholders. Instagram uses the caption only (no headline /
description), which is how a feed ad renders there. Styles: `ad_copywriter/preview/templates/mockup.css` in the `ad-copywriter` tool.
