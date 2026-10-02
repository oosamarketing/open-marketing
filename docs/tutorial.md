# Tutorial: from download to your first ads

You don't need to know how to code. You'll copy three commands once, then talk to Claude in
plain English. Plan on 15 minutes.

## 1. What you need

- A Mac or Linux computer (Windows works through WSL).
- **Claude Code.** Easiest: the Claude desktop app, *Code* tab. Or the terminal version:
  https://claude.com/claude-code
- **git** and **Python 3.11+.** On a Mac, open the Terminal app and run `xcode-select --install`
  if you've never installed developer tools; that gives you both.

## 2. Download and set up (one time)

Open Terminal and paste these one at a time:

```bash
git clone https://github.com/oosamarketing/open-marketing.git
```
```bash
cd open-marketing
```
```bash
scripts/setup.sh
```

The last one takes about three minutes. It builds a private Python environment inside the folder
and downloads a headless browser (about 150 MB) that turns designs into images. It finishes by
rendering a test ad for the example brand. When you see `Ready.` you're done.

## 3. Open the folder in Claude

- **Desktop app:** Code tab → choose the `open-marketing` folder.
- **Terminal:** from inside the folder, run `claude`.

Claude reads the instructions in the repo on its own. You'll be asked to approve commands the
first time it runs them; that's normal.

## 4. Make your brand kit

Tell Claude where your brand lives and where you want files saved. For example:

> Build a brand kit for https://mybrand.com. My brand folder is ~/Documents/MyBrand. I've put our
> logo files in ~/Documents/MyBrand/logo.

What happens:

1. Claude opens your site in the background and measures the colors, fonts, logo and taglines you
   actually use.
2. It shows you what it found next to anything you gave it, and **asks you to confirm or correct**.
   Your word beats the website.
3. After you say yes, it builds a short brand kit PDF and a `brand-assets/` folder (logos, a round
   avatar for social profiles, palette, and the settings the design tool reads) inside your folder.

## 5. Make ads or listing images

Give Claude photos and say what you want:

> Make two Meta ads for our steel bottle, 1:1 and 1.91:1. Photos are in
> ~/Documents/MyBrand/photos. Headline ideas: "Ice cold for 24 hours."

or

> Make Amazon gallery infographics and four A+ rows for our water bottles. Product images are on our
> Shopify store.

For a new brand Claude works in steps and **waits for your OK** at each: brand kit → a short plan
listing every image, its size, headline and which claim it carries → the images. You get preview
sheets to react to. Reply the way you'd talk to a designer: "move the bottle left", "the headline
covers her face", "use the beach photo instead". If a product cutout looks rough, send a
transparent PNG if you have one; it's faster than letting Claude retry.

Sizes are exact for each platform (Meta 1080×1080 and 1200×628, Amazon 2000×2000 gallery, 970×300
A+ rows). Claude only uses claims it can find on your site or that you give it.

## 6. Try the example first (optional)

No brand handy? Ask:

> Render the Northpeak example ads and show me.

or run it yourself:

```bash
cd tools/graphic-designer
../../.venv/bin/python render.py templates/meta-simple-hero.html --brand northpeak --data data/northpeak-meta-1.91x1.json --out out/example-wide.png
```

## 7. Good to know

- **Your files stay yours.** Deliverables and photos are saved in your folders, never uploaded by
  these tools. Tell Claude once where a brand's files live and it records that in a `workspace.md`.
- **Already have folders?** Claude works inside them and won't move or rename your files. If a
  folder is busy, it keeps its work in one subfolder.
- **Editable files.** PNGs come first. On a Mac with Adobe Illustrator installed, ask for "the .ai
  version" once you approve a design and you get a layered file with live text.
- **Better cutouts.** Run `scripts/setup.sh --cutouts` once to add background removal.

## 8. Updating

The toolkit improves over time. About once a week Claude checks quietly and tells you if there's
a new version and what changed; say yes and it updates. You can also do it yourself:

```bash
scripts/update.sh --check    # just look
scripts/update.sh            # update
```

**If you've customized the toolkit** (say Claude changed a template for you), just ask Claude to
update. It explains what's new and what overlaps with your changes, makes a backup, merges the
two, re-renders one of your own designs to prove nothing broke, and can roll back in one step.
Your own templates live safest in the `custom/` folder, which updates never touch.

Updating never touches your brands, photos or finished work. That is why the tutorial uses
`git clone` rather than the *Download ZIP* button: a ZIP copy can't update itself.

## Troubleshooting

| Problem | Fix |
|---|---|
| `python3: command not found` | Install Python from https://www.python.org/downloads/ and rerun `scripts/setup.sh` |
| Setup ends with "test render failed" | Run `.venv/bin/playwright install chromium` and try again |
| Fonts look wrong in an ad | Google fonts load from the web at render time; check your connection. A licensed brand font (the brand kit says which) must be installed on your computer: give Claude the font file and it installs it |
| Claude says a tool "isn't included yet" | Ad-copy generation and AI photo expand are being prepared for release; give Claude your own copy or a wider photo |
| `.ai` export fails | It needs Adobe Illustrator on macOS and the brand fonts installed |
