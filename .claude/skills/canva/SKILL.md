---
name: canva
description: Get creative into Canva as native, editable designs through the Canva connector, repair a design the user already has in Canva, or hand editable work to a team that works in Canva. Use whenever the user mentions Canva, shares a canva.com link, asks to get work "into Canva", or is about to upload a .ai, PDF or PNG to Canva expecting it to stay editable.
---

# Canva

Needs the Canva connector (its tools start with `mcp__…canva…` or are named `read-design`,
`edit-design`, `import-design-from-url`, `export-design`). If they aren't in the session, say so
and stop; there is no other way in. Canva's own uploader is a native file picker that browser
automation cannot drive, so "just upload it for me" is not available either. Some clients prefer
Canva and some prefer the toolkit's own rendering: both are supported, but they are different
paths, so ask which the user wants before building.

## Three ways in, in order of preference

1. **The user already has a design in Canva.** Ask for the share or edit link, `read-design` it,
   and repair or extend it in place with `edit-design`. Don't ask them to export anything.
2. **Import from a public URL.** `import-design-from-url` accepts PDF, PPTX, DOCX, HTML, PSD, AI and
   more, but **only from a URL that is already public**. A brand's own site and CDN qualify
   (Shopify product images, a hosted PDF). Files on the user's computer do not. **Never publish the
   user's local files to a pastebin, file host or temporary URL to make them importable, and never
   suggest it**: that puts their work on the open internet permanently. If the file is local, either
   rebuild natively (3) or tell the user to import it themselves from Canva's Upload menu.
3. **Build natively with `edit-design`.** Rebuild the design from shapes, images and text. Fully
   editable, and the only path for local work when the user doesn't want to upload by hand.

## What does not work: uploading this toolkit's `.ai` exports

Measured on one 1080×1080 ad made by `render.py` and imported through Canva's Illustrator
importer: 151 elements, of which 83 were single letters as tiny raster images and 53 were letters
as black outlined shapes, plus one merged live text block on top. Doubled, offset, half-black text.
The artwork itself was fine; Canva's `.ai` importer is what shreds text. So: `.ai` is for
Illustrator, `--svg` is for Figma, and neither is a way into Canva. A flat PNG can sit in a design
but nothing in it is editable. (A plain vector PDF from `render.py --out x.pdf` keeps real text and
may import better; untested, so say so if you suggest it.)

## Getting assets in

`upload-asset-from-url` takes public URLs only, same rule as above. Cutouts and renders that exist
only locally: use a public source instead, design around them, or ask the user to drag them into
Canva Uploads.

## Making a canvas at an exact ad size

Prefer `create-design` when the connector offers it; `generate-design` is the legacy path. Preset
types have fixed sizes that don't match ad specs (`instagram_post` is 1080×1350, not 1:1). To get
1080×1080 or 1200×628: make a near-empty design, then `resize-design` with a custom width and
height. **Custom resize is a paid feature with a small free trial** (2 uses on a free account; the
response reports `uses_remaining`). Decide every size you need before spending one, or ask the
user first, and tell them when the trial is used up.

## Building a page

`read-design` with `open_transaction: true` returns a `transaction_id` and each element's
`locator_id`. Send `edit-design` operations, then a separate call with `finalize: "commit"` and no
operations. **This "commit" saves the Canva design; it has nothing to do with git.**

Operations: `add_page` (width, height, background_color), `insert_shape`, `insert_fill` (images),
`add_text`, `format_text`, `position_element`, `resize_element`, `update_opacity`, `delete_element`.

What the API can't do, so don't promise a pixel match:

| Limit | Effect | Do this |
|---|---|---|
| No font family | all text lands in Canva's default sans | tell the user to select the text and pick the brand font, two clicks per page |
| No gradients on shapes | solid fills only | one flat colour, or fake depth with low-opacity circles |
| No blur | hard blob edges | opacity around 0.25 instead |
| `insert_shape` paths | only `M/L/H/V/C/S/A/Z` | convert `Q`/`T` curves to `C` or `A` |
| Glyphs outside the font | render as boxes | draw checkmarks and icons as SVG paths, never as `✓` |

Also: images stretch to their box, so match the box to the image's aspect ratio or cover the
overflow with a panel added afterwards; layering follows insertion order, so insert back to front;
text boxes are top-anchored with height about `fontSize × lineHeight`; and headlines rewrap wider
in Canva's default font, so check the returned thumbnail, reflow, and warn the user it will reflow
again when they set the brand font.

## Verify with an export, not the thumbnail

Stored thumbnails go stale and can show a committed page as garbled. Confirm with
`get-export-formats` then `export-design` to PNG, and look at the file.

## Finishing

Put the designs in a folder (`create-folder`, `move-item-to-folder`) and give the user the folder
link and each design link. Rename anything still carrying an upload filename. If a design
duplicates an existing one, say so and let the user choose; don't delete either.
