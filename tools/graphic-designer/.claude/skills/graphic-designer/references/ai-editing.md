# Variations from a client's existing .ai template

The template is the client's design system. The job is to change photos and copy while
leaving layout, gradients, logos, and effects exactly as the designer built them, and to
never overwrite their file.

## Flow

1. **Inspect.** `$PY ai_inspect.py "<template.ai>" --out report.json` lists artboards with
   sizes, layers, every text frame (contents, font, size, position, artboard), placed and
   embedded images. Summarize it per artboard before deciding anything; it tells you which
   artboards are which format (1440x1800 Mobile, 1440x2560 Story, 1800x1800 Square are Meta's),
   which text is the headline versus subhead versus CTA (font and size), and which copy sets
   already exist. Look at the client's previous exports too (often an `Artboard Export/`
   folder next to the file) so you match their taste.
2. **Choose sources.** For each new photo pick the artboards whose existing copy suits it
   (a product close-up wants the product claim; an action shot wants the attitude headline).
   Prefer keeping the copy sets the designer already built over inventing combinations.
3. **Write a spec** (JSON, keep it next to the exports so the run is reproducible):

```json
{
  "source": "<template.ai>",
  "save_as": "<template> - <Month YYYY> Variations.ai",
  "export_dir": "<client folder>/Artboard Export/<SET NAME>",
  "variants": [
    {"artboard": 1, "export": "fire_mobile_1440x1800", "image": "<abs photo>", "anchor": [0.55, 0.25]},
    {"artboard": 13, "export": "fire_square", "image": "<abs photo>", "anchor": [0.55, 0.2], "hide_texts": ["Lorem ipsum"]},
    {"artboard": 11, "export": "helmet_story", "image": "<abs dark composite>", "anchor": [1.0, 0.0],
     "texts": {"OLD HEADLINE.": "NEW HEADLINE."}}
  ]
}
```

   `anchor` is which part of the cover-fitted photo to keep (x, y in 0..1): 0.2 on y keeps
   the top, 1.0 on x keeps the right edge. `texts` matches current contents, case and
   whitespace insensitive; use `\n` for line breaks. `recolor_white_to` flips white text,
   logos, and brackets to a dark color for light photos; use it rarely (see below).
4. **Run.** `$PY ai_edit.py spec.json`. It saves the copy, unlocks the template's locked
   layers, and for each variant hides the visible photo inside the artboard's clipping group,
   places the new photo cover-fitted into the same group, embeds it, edits text, and exports the
   artboard as PNG. The log says what happened per artboard.
5. **Review** a contact sheet (Pillow: resize each export to a common height, paste side by
   side), fix, re-run. Re-running always starts again from the source, so keep every variant in
   the spec, not just the ones you are changing.

## Light photos on a white-text template

Templates built for dark action shots (white text, black multiply gradients) fail on a white
background: the gradient turns the white muddy and dark text lands on the dark subject. Do not
fight it with recoloring. Cut the subject out and composite it onto the brand's dark color at
the size and position the layout needs, then use that composite as the photo with white text
as designed. For Story formats, put the subject at the top of a tall canvas and fade the bottom
of the subject into the background so the headline block below sits on solid color. See
`product-photos.md` for the cutout tools.

## Things the scripts cannot do

Outlined text is paths, not text: replace the object, don't expect to edit it. Smart objects
and embedded PSDs are opaque. Artboards with odd sizes (a client's 1738x1806 "square") export
at their own size; if the platform needs exact dimensions add a resize step with Pillow or ask
whether to resize the artboard.
