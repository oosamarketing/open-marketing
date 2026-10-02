---
name: email-designer
description: Design and build marketing emails as paste-ready HTML — single sections, a full email, or a Gmail-safe version under 102 KB. Every section is one `<div>` snippet with inline CSS (never `<html>`, `<head>`, `<body>` or `<style>`), mixing rendered graphics where design needs them with live responsive text where there is real copy. Use this whenever the user asks for an email, newsletter, campaign, flow email, email section/block/banner/header/footer, "recreate this email", "make this email better", Klaviyo/Mailchimp/Shopify Email content, or hands over an existing email and assets.
---

# Email designer

Emails here are built as **stackable snippets**. Each section is a single `<div>…</div>` with
inline CSS that pastes into an ESP's HTML/code block; stacked in order they are the email. The
ESP supplies the document shell, so a snippet that carries its own `<html>`, `<body>` or `<style>`
breaks the template it lands in. That rule has no exceptions, including "full email" requests:
the full email is the sections concatenated.

Python: `../../.venv/bin/python` in the Open Marketing toolkit, or any Python with Playwright +
Pillow. Run from the graphic-designer folder.

## The one decision per section: graphic or live text?

| Make it a **graphic** (rendered image) when… | Keep it **live HTML** when… |
|---|---|
| the headline must be in the brand's display font (custom fonts don't load without `<style>`) | there is real copy to read: paragraphs, bullets, product details, FAQs |
| a product cutout sits over color, a photo needs overlay text, or there are gradients/effects | it has to reflow on a phone (multi-column product rows, long text) |
| it is the hero and the design is the message | it is legal or functional: footer, address, unsubscribe, preheader-ish text, buttons |
| | the words matter for deliverability and accessibility (image-only emails read as spam and say nothing with images off) |

A good email is usually one or two graphics carrying the brand, and everything else live. Every
graphic gets alt text that says what the image says, and a link. Buttons stay live so they work
with images blocked.

## Build

Write a spec (JSON) and run the builder; it renders graphics, copies and downsizes images, builds
and lints every snippet, measures size, and screenshots desktop and mobile:

```bash
$PY emails/build_email.py <spec.json>                       # sections/, email.html, previews/, report.md
$PY emails/build_email.py <spec.json> --base-url <https://…/folder/>   # after the images are hosted
$PY emails/build_email.py <spec.json> --lite                # force the ≤102 KB version
```

Section types: `offer` (copy + code chip + one button), `compare` (us-vs-them rows that stay paired when they stack), `tiles` (2-up image grid that never stacks), `social` (text links), `header`, `image`, `graphic` (renders an HTML template from `templates/` to a 2x
JPG, e.g. `templates/email-hero.html`), `hero_text`, `text` (heading, paragraphs, bullets,
button), `button`, `columns` (2–3 cards that stack on phones), `quote`, `divider`, `spacer`,
`footer`, `raw` (your own snippet; still linted). The spec format and every field are in the
docstring of `emails/build_email.py`; `emails/examples/northpeak-launch.json` is a working example.
Text fields accept `**bold**`, `[link](url)` and newlines. ESP merge tags (`{% unsubscribe %}`,
`{{ first_name }}`) pass through untouched.

Output goes in the client workspace, not the repo: `<entry>/email/<campaign>/` (set `"out"` in the
spec). What the user takes: `sections/*.html` to paste block by block, or `email.html` to paste
whole, plus `images/` to upload.

## Reviews and other third-party proof

Testimonials only work if they look like they came from somewhere. Rules:
- Use real reviews. Reviews.io exposes them publicly: `https://api.reviews.io/merchant/reviews?store=<domain>`
  and `/product/reviews/all?store=<domain>`. Check every quote the client hands you against the
  feed; drop or replace any you can't find, and say so. Never edit a quote (trim with an ellipsis).
- Borrow the platform's identity, not the brand's: its real logo (download it from their site), the
  font its site actually uses (read it with computed styles; Reviews.io is `system-ui`), a
  "Verified buyer" tag, and a link on every card to the client's public page on that platform.
  A review card in the brand font looks designed; one in the platform's look reads as verified.
- State the real aggregate (average and count) from the platform next to the cards.
- Record what was used and the review IDs in the workspace (`assets/reviews-used.json`).
- `templates/email-review-card.html` renders a card; render one per review and place them with a
  `columns` section so they stack on phones. Keep cards light (white) so the platform logo reads.

## Size: the 102 KB rule

Gmail clips a message at about 102 KB of HTML and hides the rest behind "View entire message",
which also hides the unsubscribe link and breaks open tracking. Images don't count (they're
URLs), only markup does. The builder targets 98 KB to leave room for what the ESP adds. When
`email.html` is over, it writes `email-lite.html`: minified first, and if that isn't enough the
heaviest text sections are rendered to images until it fits (footer, header and buttons always
stay live). The report says which sections were rasterized. Prefer fixing the cause when you can:
cut repeated sections, or move long content to a landing page and link to it.

## Weight: tell the user, and let them choose

The 102 KB rule is about HTML. Images are the other half: every build reports the **total
download** (HTML + images actually used) in `report.md` and compares it to benchmarks: plain
text ~10 KB, a typical marketing email 500 KB–1.2 MB, over ~2 MB loads visibly slowly on mobile
and some clients stop fetching images. Always state the total and the comparison when you
deliver. Images are recompressed automatically with `compress.py`, which walks JPEG quality down
until the pixel error would become visible, so the first fix is free.

Then ask, when the email is image-heavy (a designer who builds every section as a graphic will
get there fast): **rich** (default, full-quality images, ~1 MB budget) or **light** (`--profile
light`: smaller, slightly softer images, ~400 KB). Suggest converting image-only text sections to
live HTML before suggesting lower quality, since that cuts weight and fixes mobile legibility at
once.

## Images need hosting

Snippets reference `images/<file>` until the images have a public URL. Tell the user to upload the
`images/` folder to their ESP or store files (Klaviyo image library, Shopify Files), then rebuild
with `--base-url`. Never embed images as `data:` URIs: they count toward the 102 KB and many
clients strip them.

## Handing it to a human in the ESP editor

Most editors (Klaviyo, Shopify Email, Redo, Mailchimp) let a person drop images into native
blocks easily, but a pasted HTML snippet that references images needs those images hosted first.
So deliver in two forms, following `build/handoff.md`, which the builder writes:

- **Image-only sections** (hero graphic, logo bar, review cards, category tiles): tell the human
  which native block to use ("3-image row", "2x2 grid", "image block"), which file from `images/`
  goes in each slot, and the link and alt text for each. They never touch HTML for these.
- **Live sections** (offer, comparison rows, text, buttons, footer): post the snippet **in the
  chat as a code block** so they can copy it straight into a custom HTML block. One `<div>`,
  inline CSS, nothing else. If a live section contains a small image (an icon), say where to
  host it or swap the `src` for the editor's URL after upload.

**Ask which sections the editor already has** before building, or at the latest before handing
off: most editors ship presets for the footer (address, unsubscribe), social icons, a plain
button, dividers and spacers. Those are not worth a custom HTML block; mark them
`"editor": "preset"` in the spec so the handoff tells the human to use the built-in block (with
the links and colors to match) and keeps the snippet only as a fallback. Custom HTML is for what
the editor can't do well: an offer block with a code chip, comparison rows, styled text with
bullets, anything with layout. One short question covers it: "Which of these does your editor
already have as a block: footer, social icons, buttons?"

**Show the picture of each section with its instructions.** The person assembling the email
may not read HTML. Go through the whole email in order, and for every section show its image
(`build/previews/sections/<name>.png`, which the builder makes) followed by what to do: the native
block to use with file/link/alt, or the custom-HTML snippet in a code block. Never post a wall of
snippets without the pictures. `build/handoff.html` is the same guide as a page they can open in a
browser; point them to it as well.

Lead the handoff with the section order so the two kinds interleave correctly. When the user is
assembling by hand, a `--base-url` rebuild is optional: they can also paste the editor's own
hosted URLs into the snippet.

## Checks before sending anything to the user

- Look at `previews/desktop.png` and `previews/mobile.png` yourself. Columns must stack, nothing
  may overflow at 390 px, and tap targets must be finger-sized.
- `report.md` lint must be clean: single `<div>`, no html/head/body/style/script, every image has
  alt and width, links are absolute.
- Read the email with images off in your head: is the offer, the button, and the unsubscribe still there?
- Dark backgrounds need `bgcolor` and explicit text colors (the builders set both).

## Recreating or improving an existing email

1. **Inventory the original**: screenshot or read its HTML, list sections in order with their copy,
   links, and images. Note what is image-only text, what breaks on mobile, missing alt text, the
   total size, and where the call to action sits.
2. **Propose before building**: a short table of sections (graphic or live, headline, source image,
   link) and the specific improvements. Keep the client's copy and offer unless asked to rewrite;
   claims come from their material only. Wait for a yes.
3. **Build, preview, iterate** with the builder. Deliver sections + full email + lite if needed.

Brand colors, fonts and voice come from `brand-guidelines/brands/<slug>/` as with every other
graphic; run the brand-kit skill first if the brand has none.
