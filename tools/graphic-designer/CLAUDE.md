# CLAUDE.md — graphic-designer

Read `.claude/skills/graphic-designer/SKILL.md` for the workflow. These are standing rules
from the user that override defaults.

## Approve PNGs first; editable files only on request

Render PNG/JPG for approval and iterate there. Do **not** generate `.ai` (or SVG) files until
the user says the set is final or asks for a specific one. They take ~30 s each and are pure
derivatives of the approved PNG + data file, so making them early only clutters the client
folder with files that get replaced. When the user approves, ask whether they want `.ai` for
all or for specific ads, then run the same render command with `--out …ai`.

## Editable exports go to Illustrator and Figma, never to Canva

`.ai` is for Illustrator, `--svg` is for Figma. Neither imports into Canva as editable artwork:
Canva's Illustrator importer turns text into one raster image per letter plus outlined shapes, so
it comes out doubled, offset and partly black. A client who works in Canva gets the design built
natively through the Canva connector (hub skill `.claude/skills/canva/SKILL.md`); if they already
have a design there, ask for the link and work in it.

## SVG is opt-in, for Figma only

SVG export (`--svg`) exists so a design can be opened in Figma with editable text (Figma can't
open `.ai` or PDF). Each SVG embeds the product cutout and any photo as base64, so files run
5–20 MB. Only produce SVGs when the user says they are working in Figma.

## Fonts for editable handoff

Illustrator and Figma need the brand fonts installed on this Mac. Google Fonts TTFs go in
`~/Library/Fonts`; restart Illustrator afterwards or it won't list them. Tell the user when you
install a font.

## New-brand creative projects run in gates (A+ content, infographics, ad sets)

When the user asks for A+ Content, listing infographics, or an ad set for a brand that has no
`brand-guidelines/brands/<slug>/` yet, do not start designing. Run the gates in order and stop
for approval at each one:

1. **Assets + brand kit.** Find the products on the client's site (Shopify stores expose
   `/products.json` and `/collections/<handle>/products.json`; the CDN path in any client CSV,
   e.g. `/s/files/1/<store-id>/`, confirms you have the right store). Download product images and
   descriptions into `<cowork>/assets/products/<handle>/`. Run the brand-kit skill
   (`../brand-kit`) on the site plus whatever the client sent, build the DRAFT kit into
   `<cowork>/branding/`, register the brand here (`tokens.json`, `brand.md`, avatar), and point
   the export location at the cowork folder. Present the kit findings and the asset inventory.
   **Wait for approval.**
2. **Content plan.** List every image you intend to make: type (gallery infographic, A+ module,
   ad), size, headline, which product photo, what claim it carries and where the claim comes
   from. Keep it to a table. **Wait for approval.**
3. **Build.** Render PNGs, review them yourself, send a contact sheet, iterate. Editable
   files only when asked (see above).

The cowork folder for the client is the working directory for deliverables; the repos only
hold templates, tokens, and tools.

## Ask for source files after one failed cutout

If a product cutout isn't clean after one attempt with the right tool (`cutout.py`,
`cutout_white.py`, `cutout_clear.py`), stop iterating and ask the user for a transparent PNG
or the original layered file. Clients usually have them, and a second or third algorithmic
pass costs more of the user's review time than asking. Same for logos: ask for the vector or
single-color version rather than recoloring a raster.

Check every cutout at full size before calling it clean, specifically any white or clear part
(goggle and mask frames, lenses, white fabric, glass). A thumbnail on a colored background hides
holes punched through white areas. Group photos are the worst case: prefer composing a scene
from individually clean cutouts over cutting out one shot that contains several products.

## Photo narrower than the format

When a specific format is requested (1.91:1, 1:1, 9:16, a 970x300 A+ row) and the chosen photo
doesn't cover it without cropping into the subject: first try a two-column layout (photo one side,
brand-color panel with the copy on the other) or a blurred, darkened copy of the photo as the
backdrop, or ask for a wider shot. **Only if `../gemini_manager` (or `tools/gemini_manager`) exists**
in this installation, you may expand the scene generatively instead:

```bash
cd ../gemini_manager && venv/bin/python gemini_image.py --image "<photo>" --out <name>-wide \
  "Expand this photo into a wide 16:9 landscape image. Keep the <subject> and everything in the
   original photo exactly unchanged, centered, at full height. Extend the scene naturally to the
   left and right: <what continues: field, stands, sky>, matching the same lighting, lens blur and
   color grade. Photorealistic. Do not add any text, logos, watermarks or additional people."
```

**Always restore the original afterwards.** The model re-renders the whole frame, so details
inside the original area drift: jersey lettering, logos, faces. Put the real pixels back and keep
only the new margins AI-generated:

```bash
$PY restore_original.py "<original photo>" ../gemini_manager/output/<name>-wide.jpg \
    "<cowork>/assets/photos/expanded/<name>-wide.jpg" --erase-mark
```

It finds where the original sits in the expansion (scale + offset), color-matches it, and pastes it
back with feathered edges. `--erase-mark` removes a thin photographer watermark from the top-center
of both images. A reported error above ~12 means the expansion changed the framing: look before using.

Output is ~2752x1536. One wide expansion usually serves both 1.91:1 (slight vertical crop) and
1:1 (center crop). File the result under `<cowork>/assets/photos/expanded/`. Check the result
for photographer watermarks carried over from the source and for changed logos or numbers on the
subject; patch or re-run if so. Tell the user which photos were expanded, since the new edges are
AI-generated.
