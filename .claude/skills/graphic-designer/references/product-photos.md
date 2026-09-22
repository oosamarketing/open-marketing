# Product photos: real, generated, and cutouts

Real photography beats everything. Look in `brand-guidelines/brands/<slug>/assets/`, the
brand's export folder `assets/`, and whatever the user attached. Generated products are
placeholders for comps; say so in chat and swap in real photography before anything ships.

## No product photo?

Ask the user for one, or use what the brand's site and store already publish (product pages,
Shopify `/products.json`). Generating a stand-in with an image model is an optional add-on
(`tools/gemini_manager`, when present); if it isn't in this toolkit, say so and work with real
photography. Generated products are placeholders for comps, never for a live listing.

## Cut the background out

Two tools, pick by subject:

- `cutout.py in.jpg out.png` uses the rembg model (isnet). Good for colored products on
  white. Needs rembg: run `scripts/setup.sh --cutouts` once from the toolkit root. Check shiny
  highlights for white specks; try `--alpha-matting` or `--model u2net` if so.
- `cutout_white.py in.jpg out.png --seed-edges top,left` removes only near-white pixels
  connected to the chosen image borders, so white parts of the subject (a white jersey, a
  clear visor) survive. Use it when the subject is white on white, and seed only the edges
  that touch true background when the subject runs off the frame.

Both write a transparent PNG cropped to the subject. Then either reference it as
`product.image` in an HTML template, or composite it (Pillow, `alpha_composite`) onto a solid
brand color canvas sized for the layout you need, saving a JPEG for `ai_edit.py`.

## Composite tips

Give the canvas extra room on the side where the copy goes, place the subject flush to the
opposite edge, and for tall formats fade the subject's bottom 25–30% to transparent before
compositing so text below it sits on clean color.

## Pale rim on a colored background

A cutout or 3D render made against white keeps white in its semi-transparent pixels (glass
edges, reflections, soft shadows). On the brand's purple or blue that reads as a gray halo,
most visible along the bottom of bottles. Check with a quick composite on the brand color
before laying out; fix with `defringe.py in.png out.png` (fades those pixels; `--keep 0`
removes them). Padded renders also need `Image.getbbox()` on a thresholded alpha before use,
or every size and anchor you set measures transparent space.

## Photo narrower than the format

When a portrait photo must fill a 1.91:1 or 970x300 slot, don't crop into the subject. Use a
two-column layout (photo on one side, solid brand color with the copy on the other), a blurred
and darkened copy of the same photo as the backdrop, or ask the user for a wider shot. Generative
expansion is an optional add-on (`tools/gemini_manager` + `restore_original.py`) and only applies
when that tool is installed.
