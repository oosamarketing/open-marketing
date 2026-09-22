#!/usr/bin/env bash
# Update this toolkit from GitHub without losing your own work.
#   scripts/update.sh --check      look only: what's new, and whether you have changes of your own
#   scripts/update.sh              update a copy you haven't modified (fast-forward)
#   scripts/update.sh --merge      update a copy you HAVE modified: saves your edits, makes a backup,
#                                  merges the new version in, tests it
#   scripts/update.sh --rollback   undo the last --merge (or abort one that stopped on conflicts)
# Your brands, photos and deliverables are never touched: they live in your own folders, the brand
# files you add inside tools/ are git-ignored, and nothing upstream ever writes into custom/.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$HERE"
[ -d .git ] || { echo "This copy was downloaded as a ZIP, so it can't update itself. Re-download it, or switch to: git clone https://github.com/oosamarketing/open-marketing.git"; exit 2; }
MODE="${1:-}"
REMOTE=origin; git remote | grep -qx upstream && REMOTE=upstream       # forks: add the original as 'upstream'
G() { git -c user.name="$(git config user.name || echo 'Open Marketing user')" -c user.email="$(git config user.email || echo 'user@localhost')" "$@"; }
merging() { [ -f .git/MERGE_HEAD ]; }

if [ "$MODE" = "--rollback" ]; then
  if merging; then git merge --abort && echo "Stopped the update. Everything is as it was before."; exit 0; fi
  B=$(git for-each-ref --sort=-creatordate --format='%(refname:short)' 'refs/heads/backup/before-update-*' | head -1)
  [ -n "$B" ] || { echo "No backup found; nothing to roll back."; exit 1; }
  git diff --quiet && git diff --cached --quiet || { echo "You have unsaved edits made after the update. Commit or stash them first so they aren't lost, then run this again."; exit 4; }
  git reset -q --hard "$B" && echo "Rolled back to $B ($(cat VERSION 2>/dev/null))."; exit 0
fi

date +%s > .last_update_check
git remote get-url "$REMOTE" >/dev/null 2>&1 || { echo "This copy has no '$REMOTE' remote, so there is nowhere to update from. If you copied the folder instead of cloning: git remote add origin https://github.com/oosamarketing/open-marketing.git"; exit 3; }
git fetch --quiet "$REMOTE" main || { echo "Couldn't reach GitHub; try again later."; exit 3; }
BEHIND=$(git rev-list --count "HEAD..$REMOTE/main"); AHEAD=$(git rev-list --count "$REMOTE/main..HEAD")
DIRTY=$(git status --porcelain --untracked-files=no | wc -l | tr -d ' ')
MINE=""; [ "$AHEAD" != "0" ] && MINE="$AHEAD saved change(s) of your own"; [ "$DIRTY" != "0" ] && MINE="${MINE:+$MINE and }$DIRTY edited file(s) not saved yet"
if merging; then echo "An update is half-finished (conflicts). Resolve them and commit, or run: scripts/update.sh --rollback"; exit 5; fi
if [ "$BEHIND" = "0" ]; then echo "Up to date ($(cat VERSION 2>/dev/null || echo unversioned))${MINE:+, with $MINE}."; exit 0; fi

echo "Update available: $(cat VERSION 2>/dev/null) → $(git show "$REMOTE/main:VERSION" 2>/dev/null)  ($BEHIND new change(s))"
echo "--- what's new ---"; { git diff "HEAD...$REMOTE/main" -- CHANGELOG.md | grep '^+[^+]' | sed 's/^+//' | head -25; } || echo "(no changelog entry)"
if [ -n "$MINE" ]; then
  BASE=$(git merge-base HEAD "$REMOTE/main")
  OVERLAP=$(comm -12 <( { git diff --name-only "$BASE" HEAD; git diff --name-only; } | sort -u) <(git diff --name-only "$BASE" "$REMOTE/main" | sort -u))
  echo "--- your copy ---"; echo "You have $MINE."
  if [ -n "$OVERLAP" ]; then echo "Files changed by BOTH you and the update (need care):"; echo "$OVERLAP" | sed 's/^/   /'; else echo "None of your changes touch files the update changes: this should merge cleanly."; fi
fi
[ "$MODE" = "--check" ] && { echo; echo "To apply: scripts/update.sh${MINE:+ --merge}"; exit 10; }

if [ -z "$MINE" ]; then
  git merge -q --ff-only "$REMOTE/main" || exit 1
elif [ "$MODE" != "--merge" ]; then
  echo; echo "Because you've made changes, a plain update won't do. Run: scripts/update.sh --merge  (or ask your agent to update for you)."; exit 4
else
  [ "$DIRTY" != "0" ] && { git add -u && G commit -q -m "My changes (saved before updating to $(git show "$REMOTE/main:VERSION" 2>/dev/null))" && echo "Saved your unsaved edits as a commit."; }
  BK="backup/before-update-from-$(cat VERSION 2>/dev/null || echo x)-$(date +%Y%m%d-%H%M%S)"; n=1
  while git show-ref --verify --quiet "refs/heads/$BK"; do n=$((n+1)); BK="${BK%-r*}-r$n"; done   # never overwrite an older backup
  git branch "$BK" >/dev/null && echo "Backup: $BK"
  if ! G merge --no-edit "$REMOTE/main" >/dev/null 2>&1; then
    echo; echo "The update and your changes disagree in:"; git diff --name-only --diff-filter=U | sed 's/^/   /'
    echo "Nothing is lost. Ask your agent to resolve these (keeping your features, adding the improvements), or undo with: scripts/update.sh --rollback"; exit 5
  fi
  echo "Merged."
fi
[ -d .venv ] && { .venv/bin/pip -q install --upgrade playwright pillow numpy requests openpyxl; .venv/bin/playwright install chromium >/dev/null 2>&1; }
if [ -d .venv ]; then
  ( cd tools/graphic-designer && ../../.venv/bin/python render.py templates/meta-simple-hero.html --brand northpeak --data data/northpeak-meta-1x1.json --out out/update-test.png >/dev/null 2>&1 ) \
    && echo "Test render OK." || echo "WARNING: the test render failed after updating. Undo with: scripts/update.sh --rollback"
fi
echo "Now at $(cat VERSION)."
