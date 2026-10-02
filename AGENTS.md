# AGENTS.md — start here (Claude, Codex, Grok, Cursor, any coding agent)

This repo is a toolkit for marketing creative. When a user asks for marketing work here, **route
to the right tool and follow that tool's own instructions**; do not rebuild it.

## First run

Get the machine ready yourself; don't send the user to install things one by one.

1. **Python 3.11+.** `python3 --version`. If it's missing or older, install it (macOS:
   `brew install python@3.12` if Homebrew exists, otherwise point the user to python.org; Windows:
   python.org installer with "Add to PATH"; Linux: the distro package). Then continue.
2. **`scripts/setup.sh`** when `.venv/` does not exist. It creates the environment, installs
   Playwright and downloads Chromium (~150 MB, one time), and test-renders the example brand. Say
   what it is downloading. Add `--cutouts` only when the user will need background removal.
3. **Fonts.** Graphics render with the brand's fonts. Google Fonts load from the web at render
   time, but editable `.ai` exports and non-Google fonts need the font installed locally
   (`~/Library/Fonts` on macOS, `%LOCALAPPDATA%\Microsoft\Windows\Fonts` on Windows). When a
   brand's `tokens.json` names a `headline_font` or `font` that `fc-list` doesn't show: if it is a
   Google font, download the TTF from the google/fonts GitHub repo and install it; if it is licensed
   (the brand kit says so), ask the user for the file and, until it arrives, say the render is using
   the fallback. Never claim a render is in the exact font when it isn't.
4. Use `.venv/bin/python` for every script. Tool docs written from inside a tool folder refer to it
   as `../../.venv/bin/python`.

## When the user hands you a client folder

Someone may give you a folder (often a zip) prepared with this toolkit: `branding/` with a brand
kit and `brand-assets/`, and work folders like `email/<campaign>/` or `ads/`. Look for a
`HANDOFF.md` or `README.md` at the top of it and read it first; it says what is finished, what the
user is expected to do with it, and what is still open with the client. Specs in such folders are
self-contained (`brand_tokens` points at `branding/brand-assets/tokens.json`), so rebuild from
them in place and compare against the previews that came with the folder before changing anything.
Don't move or rename what was handed over; add alongside it. When *you* prepare a folder for
someone else, give them `docs/teammate-prompt.md` with it.

## Staying up to date

This folder is a git clone, so it can update itself. Check at most once a week: if
`.last_update_check` is missing or older than 7 days, run `scripts/update.sh --check` at the start
of the session (it only looks). If it reports an update, tell the user in one line what's new and
ask whether to apply it. **Apply only after they say yes**: an update changes these instructions
and the tools, so it is their decision. If GitHub can't be reached, carry on without comment.

### Customizing without painting the user into a corner

- Prefer `custom/`. When the user wants a shipped template or script changed, copy it to
  `custom/templates/` or `custom/scripts/` and change the copy, unless they specifically want the
  shipped file changed. Upstream never touches `custom/`, so this can never conflict.
- When you do change a shipped file, add a line to `custom/CUSTOMIZATIONS.md`: the file, what
  changed, and why the user wanted it. Future merges depend on knowing the intent.

### Updating a copy the user has changed

`scripts/update.sh --check` tells you whether the user has changes of their own and lists files
changed by **both** them and the update. Then:

1. **Explain before acting.** In plain words: what's new, which of their customizations overlap,
   and what you propose for each (take the improvement, keep theirs, or combine). Read
   `custom/CUSTOMIZATIONS.md` and the diffs (`git diff <merge-base> HEAD -- <file>` for theirs,
   `git diff <merge-base> origin/main -- <file>` for the update) so the proposal is specific.
2. **Get a yes, then run `scripts/update.sh --merge`.** It saves unsaved edits as a commit, makes a
   `backup/before-update-…` branch, merges, and test-renders.
3. **If it stops on conflicts, resolve them file by file.** The user's feature must keep working
   and the improvement should come in where it doesn't undo their intent. Never resolve a whole
   file with "theirs" or "ours" to make the conflict go away, never delete their code to make a
   merge pass, and never use `git reset`, force-pull or `checkout --` on their files. Commit when done.
4. **Prove nothing broke.** Beyond the built-in test render, re-run something of the user's:
   render one of their recent jobs or their custom template and show them the result next to the
   previous output. Only then call the update finished.
5. **If anything is off, `scripts/update.sh --rollback`** returns to the backup. Say that you did it
   and why.

They may want only part of an update. A new tool or template can be taken by itself with
`git checkout origin/main -- <path>` (then commit), leaving everything else as is. After a bumpy
merge, offer to move their customizations into `custom/` so the next update is clean.

## Routing

| The user wants… | Go to | Read first |
|---|---|---|
| Brand colors/logo/fonts/voice, a brand kit PDF, a round avatar from a logo | `tools/brand-kit` | `.claude/skills/brand-kit/SKILL.md` |
| An ad, Amazon infographic, A+ content, banner, product cutout, variations of an existing `.ai` | `tools/graphic-designer` | `tools/graphic-designer/CLAUDE.md` (house rules + approval gates), then `.claude/skills/graphic-designer/SKILL.md` |
| A marketing email, newsletter, flow email, or one email section (paste-ready `<div>` snippets with inline CSS; full email; ≤102 KB version) | `tools/graphic-designer` | `.claude/skills/email-designer/SKILL.md` |
| Where files should go, a new client or campaign folder | `.claude/skills/client-workspace/SKILL.md` | the skill itself |
| Anything in Canva: build, repair, hand off, or a `canva.com` link (needs the Canva connector) | `.claude/skills/canva/SKILL.md` | the skill itself |

Not included yet (say so rather than improvising): ad copy generation and client preview PDFs,
image generation and generative photo expand, Amazon research. If a tool doc mentions
`../gemini_manager` or an ad-copy tool, that step is unavailable in this release; offer the
closest alternative (a tighter crop, the user's own copy).

## Before saving anything for a client

Follow `.claude/skills/client-workspace/SKILL.md`: inspect the folder the user pointed at
(`.venv/bin/python .claude/skills/client-workspace/scripts/workspace.py inspect "<path>"`), work
inside what already exists, use an entry-point subfolder when the client folder predates this
workflow, and record preferences in `workspace.md`.

## Rules that apply everywhere

- **Work in the user's folders, not in this repo.** Brands, photos, and deliverables belong to the
  user: keep them out of `tools/` except for brand tokens the design tool needs
  (`tools/graphic-designer/brand-guidelines/brands/<slug>/`, which is git-ignored for new brands).
- **Gates for new brands:** assets + brand kit → approval → content plan → approval → build.
- **Show previews before finishing** and look at them yourself first. Editable files (.ai, .svg)
  only when the user asks.
- **Claims and copy** come from the brand's own site, files, or the user. Never invent them.
- **Ask for source files** (transparent PNGs, vector logos) after one failed cutout instead of iterating.
- **Credentials:** never type passwords or API keys.
- **Never commit to the user's clone on your own initiative.** No `git commit`, `git push`,
  `git checkout --`, `git reset` or `git restore` unless the user asks for that specific action in
  the moment. This is their working copy; when you add or change files, say which and leave them in
  the working tree. The one exception is `scripts/update.sh`, which the user runs deliberately and
  which manages its own commits and backup branch (the commit steps in "Staying up to date" above
  are part of that user-approved flow).
- **Design files are not an import path.** A `.ai`, PDF or flat PNG does not become an editable
  design by uploading it to Canva or anywhere else. If the user wants work edited in a design tool,
  ask for the link to the design and rebuild or repair it natively there. See the Canva skill.
- **Never publish the user's local files to a public URL** to get them into a tool that only
  accepts public links. Ask the user to add the file themselves, or use a source that is already
  public.
